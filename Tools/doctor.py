"""Athena local alpha doctor report.

Doctor is the single health check for the local Athena alpha. It reports whether
runtime state is clean enough to continue feature work and writes a portable JSON
report to Reports/athena_doctor_report.json.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ENGINE_LABEL  # noqa: E402
from Athena.workspace import load_workspace, secrets_status  # noqa: E402

VERSION = "0.5.0-drop3g3"
PLACEHOLDER_IDS = {
    "validation_league_id",
    "test_league_id_provider_registry",
    "test_league_id_drop2",
    "test_league_id",
}
DUPLICATE_ROOTS = [
    "Sports_Intelligence_Engine_2.0",
    "Athena/Sports_Intelligence_Engine_2.0",
    "Athena/Athena",
    "Athena/Configuration",
    "Athena/Core",
    "Athena/Scout",
    "Athena/Providers",
    "Athena/Raw",
    "Athena/Output",
    "Athena/Reports",
    "Athena/Tests",
]
ROOT_HISTORY_PATTERNS = (
    "CHANGE_MANIFEST_*.md",
    "RELEASE_NOTES_*.md",
    "RELEASE_MANIFEST_*.md",
    "MANIFEST_v*.md",
    "Release_Notes_*.md",
)


def _exists(path: str) -> bool:
    return (PROJECT_ROOT / path).exists()


def _json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        return {"_error": str(exc)}


def _root_history_files() -> List[str]:
    found: List[str] = []
    for pattern in ROOT_HISTORY_PATTERNS:
        found.extend(path.name for path in PROJECT_ROOT.glob(pattern) if path.is_file())
    return sorted(found)


def _generated_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for name in ["Raw", "Output", "Reports", "Logs", "Runtime"]:
        path = PROJECT_ROOT / name
        counts[name] = len(list(path.iterdir())) if path.exists() else 0
    return counts


def _placeholder_config_hits() -> Dict[str, List[str]]:
    hits: Dict[str, List[str]] = {}
    for rel in ["Configuration/workspace.json", "Configuration/config.json"]:
        path = PROJECT_ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        found = [token for token in PLACEHOLDER_IDS if token in text]
        if found:
            hits[rel] = found
    return hits


def _raw_output_health() -> Dict[str, Any]:
    raw_league = _json_file(PROJECT_ROOT / "Raw" / "league_info.json")
    player_master = _json_file(PROJECT_ROOT / "Output" / "player_master.json")
    team_profiles = _json_file(PROJECT_ROOT / "Output" / "team_profiles.json")

    team_count = 0
    if isinstance(raw_league.get("teamInfo"), list):
        team_count = len(raw_league["teamInfo"])
    elif isinstance(raw_league.get("teams"), list):
        team_count = len(raw_league["teams"])
    elif isinstance(raw_league.get("league"), dict) and isinstance(raw_league["league"].get("teams"), list):
        team_count = len(raw_league["league"]["teams"])

    player_count = 0
    missing_names = 0
    if isinstance(player_master, list):
        player_count = len(player_master)
        missing_names = sum(1 for p in player_master if not str(p.get("player_name") or "").strip())
    elif isinstance(player_master.get("records"), list):
        records = player_master["records"]
        player_count = len(records)
        missing_names = sum(1 for p in records if isinstance(p, dict) and not str(p.get("player_name") or "").strip())

    profile_count = len(team_profiles) if isinstance(team_profiles, list) else int(team_profiles.get("record_count") or 0) if isinstance(team_profiles, dict) else 0
    return {
        "league_info_team_count": team_count,
        "player_master_count": player_count,
        "player_master_missing_names": missing_names,
        "team_profile_count": profile_count,
    }


def build_report() -> Dict[str, Any]:
    payload = load_workspace()
    workspace = payload.get("workspace", {}) if isinstance(payload, dict) else {}
    duplicate_roots = [path for path in DUPLICATE_ROOTS if _exists(path)]
    root_history = _root_history_files()
    placeholder_hits = _placeholder_config_hits()
    generated = _generated_counts()
    credentials = secrets_status()
    raw_output = _raw_output_health()

    issues: List[str] = []
    warnings: List[str] = []

    if ATHENA_VERSION != VERSION or SCOUT_VERSION != f"v{VERSION}":
        issues.append(f"Version mismatch: Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}; expected={VERSION}")
    if duplicate_roots:
        issues.append(f"Duplicate legacy roots detected: {duplicate_roots}")
    if root_history:
        warnings.append(f"Root release/change history files remain: {root_history}")
    if placeholder_hits:
        issues.append(f"Placeholder IDs remain in runtime config: {placeholder_hits}")
    if workspace.get("engine_version") not in {ENGINE_LABEL, None, ""}:
        warnings.append(f"Workspace engine_version is not current: {workspace.get('engine_version')}")
    if any(token == str(workspace.get("league_id") or "").strip() for token in PLACEHOLDER_IDS):
        issues.append(f"Workspace league_id is placeholder: {workspace.get('league_id')}")
    if raw_output["player_master_count"] and raw_output["player_master_missing_names"] == raw_output["player_master_count"]:
        warnings.append("Player master exists but every record has a blank player_name.")

    status = "pass"
    if issues:
        status = "fail"
    elif warnings:
        status = "warn"

    return {
        "doctor_version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT_ROOT),
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "versions": {"athena": ATHENA_VERSION, "scout": SCOUT_VERSION, "engine_label": ENGINE_LABEL},
        "workspace": {
            "provider": workspace.get("provider"),
            "league_id": workspace.get("league_id"),
            "league_name": workspace.get("league_name") or workspace.get("name"),
            "sport": workspace.get("sport"),
            "season": workspace.get("season"),
            "team_count": workspace.get("team_count"),
            "engine_version": workspace.get("engine_version"),
            "operation_history_count": len(workspace.get("operation_history") or []),
        },
        "credentials": credentials,
        "duplicate_roots": duplicate_roots,
        "root_history_files": root_history,
        "placeholder_config_hits": placeholder_hits,
        "generated_artifact_counts": generated,
        "raw_output_health": raw_output,
        "recommendations": [
            "Run Tools/cleanup_3g_phase3_final_hygiene.py if status is FAIL or root_history_files is not empty.",
            "Run Tools/cleanup_3g_phase2_residue.py only if duplicate roots reappear.",
            "Attach Reports/athena_doctor_report.json and the latest Scout debug export when reporting issues.",
        ],
    }


def main() -> int:
    report = build_report()
    reports_dir = PROJECT_ROOT / "Reports"
    reports_dir.mkdir(exist_ok=True)
    out = reports_dir / "athena_doctor_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Athena Doctor")
    print("=============")
    print(f"Status: {report['status'].upper()}")
    print(f"Athena: {report['versions']['athena']}")
    print(f"Scout: {report['versions']['scout']}")
    print(f"League: {report['workspace'].get('league_id')}")
    print(f"Duplicate roots: {len(report['duplicate_roots'])}")
    print(f"Root history files: {len(report['root_history_files'])}")
    print(f"Issues: {len(report['issues'])}")
    print(f"Warnings: {len(report['warnings'])}")
    print(f"Report: {out}")
    return 0 if report["status"] in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
