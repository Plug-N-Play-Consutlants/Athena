"""3G Phase 3 final repository hygiene pass.

This is the final cleanup pass before returning to feature cadence. It removes
source-tree residue that can confuse runtime state without deleting live local
league data, secrets, or the current Raw/Output cache.

Safe by design:
- preserves Configuration/secrets.local.json
- preserves Raw/, Output/, Reports/, Logs/
- archives historical root release/change files instead of deleting them
- removes duplicate nested roots, Python cache files, and validation residue in workspace
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "Reports"
REPORTS_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR = PROJECT_ROOT / "Archive" / "release_history_3g3"

VERSION = "0.5.0-drop3g3"
ENGINE_LABEL = f"Athena v{VERSION}"

PLACEHOLDER_IDS = {
    "validation_league_id",
    "test_league_id_provider_registry",
    "test_league_id_drop2",
    "test_league_id",
}

DUPLICATE_ROOT_PATHS = [
    "Sports_Intelligence_Engine_2.0",
    "Athena/Sports_Intelligence_Engine_2.0",
    "Athena/Athena",
    "Athena/Configuration",
    "Athena/Core",
    "Athena/Diagnostics",
    "Athena/docs",
    "Athena/Intelligence",
    "Athena/Knowledge",
    "Athena/Logs",
    "Athena/Output",
    "Athena/Providers",
    "Athena/Raw",
    "Athena/Reports",
    "Athena/Scout",
    "Athena/Tests",
]

ROOT_HISTORY_PATTERNS = (
    "CHANGE_MANIFEST_*.md",
    "RELEASE_NOTES_*.md",
    "RELEASE_MANIFEST_*.md",
    "MANIFEST_v*.md",
    "Release_Notes_*.md",
)

GITIGNORE_REQUIRED = [
    "Configuration/secrets.local.json",
    "__pycache__/",
    "*.py[cod]",
    "Raw/",
    "Output/",
    "Reports/",
    "Logs/",
    "Runtime/",
    ".pytest_cache/",
]


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _remove_path(path: Path, removed: List[Dict[str, str]]) -> None:
    if not path.exists():
        return
    kind = "dir" if path.is_dir() else "file"
    removed.append({"path": _relative(path), "kind": kind})
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _remove_duplicate_roots(removed: List[Dict[str, str]]) -> None:
    for rel in DUPLICATE_ROOT_PATHS:
        _remove_path(PROJECT_ROOT / rel, removed)


def _remove_python_cache(removed: List[Dict[str, str]]) -> None:
    for path in sorted(PROJECT_ROOT.rglob("__pycache__"), key=lambda p: len(str(p)), reverse=True):
        _remove_path(path, removed)
    for path in sorted(PROJECT_ROOT.rglob("*.pyc")):
        _remove_path(path, removed)
    for path in sorted(PROJECT_ROOT.rglob(".pytest_cache"), key=lambda p: len(str(p)), reverse=True):
        _remove_path(path, removed)


def _archive_root_history_files(moved: List[Dict[str, str]]) -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for pattern in ROOT_HISTORY_PATTERNS:
        for source in sorted(PROJECT_ROOT.glob(pattern)):
            if not source.is_file():
                continue
            target = ARCHIVE_DIR / source.name
            suffix = 1
            while target.exists():
                target = ARCHIVE_DIR / f"{source.stem}_{suffix}{source.suffix}"
                suffix += 1
            shutil.move(str(source), str(target))
            moved.append({"from": _relative(source), "to": _relative(target)})


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _sanitize_workspace() -> Dict[str, Any]:
    path = PROJECT_ROOT / "Configuration" / "workspace.json"
    payload = _load_json(path)
    workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else payload
    if not isinstance(workspace, dict):
        workspace = {}

    original_league_id = str(workspace.get("league_id") or "").strip()
    if original_league_id in PLACEHOLDER_IDS:
        workspace["league_id"] = ""

    workspace["engine_version"] = ENGINE_LABEL

    history = workspace.get("operation_history")
    removed_history = 0
    if isinstance(history, list):
        cleaned = []
        for item in history:
            item_text = json.dumps(item, default=str)
            if any(token in item_text for token in PLACEHOLDER_IDS) or "Tests/fixtures/" in item_text:
                removed_history += 1
                continue
            cleaned.append(item)
        workspace["operation_history"] = cleaned

    for key in ["last_operation_result", "last_answer", "latest_answer", "latest_operation"]:
        val = workspace.get(key)
        if isinstance(val, dict):
            val_text = json.dumps(val, default=str)
            if any(token in val_text for token in PLACEHOLDER_IDS) or "Tests/fixtures/" in val_text:
                workspace.pop(key, None)

    _write_json(path, {"workspace": workspace})
    return {
        "workspace_file_exists": True,
        "league_id": workspace.get("league_id"),
        "engine_version": workspace.get("engine_version"),
        "removed_history_records": removed_history,
        "operation_history_count": len(workspace.get("operation_history") or []),
    }


def _sanitize_config() -> Dict[str, Any]:
    path = PROJECT_ROOT / "Configuration" / "config.json"
    if not path.exists():
        return {"config_file_exists": False}
    payload = _load_json(path)
    changed = False

    def scrub(obj: Any) -> Any:
        nonlocal changed
        if isinstance(obj, dict):
            return {k: scrub(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [scrub(v) for v in obj]
        if isinstance(obj, str) and obj.strip() in PLACEHOLDER_IDS:
            changed = True
            return ""
        return obj

    cleaned = scrub(payload)
    if changed:
        _write_json(path, cleaned)
    return {"config_file_exists": True, "changed": changed}


def _harden_gitignore() -> Dict[str, Any]:
    path = PROJECT_ROOT / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    changed = False
    for line in GITIGNORE_REQUIRED:
        if line not in lines:
            lines.append(line)
            changed = True
    if changed:
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"exists": path.exists(), "changed": changed}


def _collect_remaining() -> Dict[str, Any]:
    duplicate_roots = [rel for rel in DUPLICATE_ROOT_PATHS if (PROJECT_ROOT / rel).exists()]
    root_history = []
    for pattern in ROOT_HISTORY_PATTERNS:
        root_history.extend(str(p.name) for p in PROJECT_ROOT.glob(pattern) if p.is_file())
    pycache_count = len(list(PROJECT_ROOT.rglob("__pycache__"))) + len(list(PROJECT_ROOT.rglob("*.pyc")))
    return {
        "duplicate_roots": duplicate_roots,
        "root_history_files": sorted(root_history),
        "python_cache_count": pycache_count,
    }


def main() -> int:
    removed: List[Dict[str, str]] = []
    moved: List[Dict[str, str]] = []

    _remove_duplicate_roots(removed)
    _remove_python_cache(removed)
    _archive_root_history_files(moved)
    workspace_status = _sanitize_workspace()
    config_status = _sanitize_config()
    gitignore_status = _harden_gitignore()
    remaining = _collect_remaining()

    manifest = {
        "cleanup": "3G Phase 3 Final Hygiene Pass",
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT_ROOT),
        "removed_count": len(removed),
        "removed": removed,
        "archived_root_history_count": len(moved),
        "archived_root_history": moved,
        "workspace_status": workspace_status,
        "config_status": config_status,
        "gitignore_status": gitignore_status,
        "remaining": remaining,
        "notes": [
            "Raw/Output/Reports/Logs were preserved as local runtime data.",
            "Configuration/secrets.local.json was preserved if present.",
            "Root release/change files were archived to Archive/release_history_3g3 instead of deleted.",
        ],
    }
    report_path = REPORTS_DIR / "cleanup_3g_phase3_final_hygiene_report.json"
    report_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("3G Phase 3 final hygiene complete")
    print(f"Removed paths: {len(removed)}")
    print(f"Archived root history files: {len(moved)}")
    print(f"Remaining duplicate roots: {len(remaining['duplicate_roots'])}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
