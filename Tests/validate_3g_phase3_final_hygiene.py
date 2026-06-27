from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ENGINE_LABEL  # noqa: E402
from Athena.workspace import load_workspace, secrets_status  # noqa: E402
from Tools.doctor import build_report  # noqa: E402

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


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.warnings = 0
        self.failed = 0
        self.lines: list[str] = []

    def ok(self, name: str, detail: str) -> None:
        self.passed += 1
        self.lines.append(f"[PASS] {name}: {detail}")

    def warn(self, name: str, detail: str) -> None:
        self.warnings += 1
        self.lines.append(f"[WARN] {name}: {detail}")

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.lines.append(f"[FAIL] {name}: {detail}")


def _exists(rel: str) -> bool:
    return (PROJECT_ROOT / rel).exists()


def _root_history_files() -> list[str]:
    found: list[str] = []
    for pattern in ROOT_HISTORY_PATTERNS:
        found.extend(path.name for path in PROJECT_ROOT.glob(pattern) if path.is_file())
    return sorted(found)


def main() -> int:
    r = Report()

    if ATHENA_VERSION == "0.5.0-drop3g3" and SCOUT_VERSION == "v0.5.0-drop3g3":
        r.ok("single_version_source", f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}")
    else:
        r.fail("single_version_source", f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}")

    duplicate_roots = [rel for rel in DUPLICATE_ROOTS if _exists(rel)]
    if duplicate_roots:
        r.fail("duplicate_roots_removed", ", ".join(duplicate_roots))
    else:
        r.ok("duplicate_roots_removed", "no duplicate runtime roots detected")

    root_history = _root_history_files()
    if root_history:
        r.fail("root_history_archived", ", ".join(root_history[:10]))
    else:
        r.ok("root_history_archived", "root release/change history moved out of repo root")

    workspace_payload = load_workspace()
    workspace = workspace_payload.get("workspace", {}) if isinstance(workspace_payload, dict) else {}
    workspace_text = json.dumps(workspace_payload)
    hits = [token for token in PLACEHOLDER_IDS if token in workspace_text]
    if hits:
        r.fail("workspace_placeholder_free", str(hits))
    else:
        r.ok("workspace_placeholder_free", f"league_id={workspace.get('league_id')}")

    if workspace.get("engine_version") == ENGINE_LABEL:
        r.ok("workspace_engine_version_current", str(workspace.get("engine_version")))
    else:
        r.fail("workspace_engine_version_current", str(workspace.get("engine_version")))

    config_path = PROJECT_ROOT / "Configuration" / "config.json"
    if config_path.exists():
        config_text = config_path.read_text(encoding="utf-8", errors="ignore")
        config_hits = [token for token in PLACEHOLDER_IDS if token in config_text]
        if config_hits:
            r.fail("config_placeholder_free", str(config_hits))
        else:
            r.ok("config_placeholder_free", "no placeholder IDs in Configuration/config.json")
    else:
        r.ok("config_placeholder_free", "Configuration/config.json not present")

    gitignore = PROJECT_ROOT / ".gitignore"
    gitignore_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    required = ["Configuration/secrets.local.json", "Raw/", "Output/", "Reports/", "Logs/", "Runtime/", "__pycache__/", "*.py[cod]"]
    missing = [line for line in required if line not in gitignore_text]
    if missing:
        r.fail("gitignore_runtime_hardened", f"missing={missing}")
    else:
        r.ok("gitignore_runtime_hardened", "runtime artifacts and local secrets ignored")

    pycache = list(PROJECT_ROOT.rglob("__pycache__")) + list(PROJECT_ROOT.rglob("*.pyc"))
    if pycache:
        r.warn("python_cache_removed", f"cache artifacts remain: {len(pycache)}")
    else:
        r.ok("python_cache_removed", "no cache artifacts detected")

    status = secrets_status()
    if "fantrax_cookie_present" in status and "fantrax_league_secret_present" in status:
        r.ok("credential_status_split_available", f"cookie={status.get('fantrax_cookie_present')}; league_secret={status.get('fantrax_league_secret_present')}")
    else:
        r.fail("credential_status_split_available", str(status))

    doctor = build_report()
    if doctor.get("status") in {"pass", "warn"} and not doctor.get("issues"):
        r.ok("doctor_health_report_clean", f"status={doctor.get('status')}; warnings={len(doctor.get('warnings') or [])}")
    else:
        r.fail("doctor_health_report_clean", f"status={doctor.get('status')}; issues={doctor.get('issues')}")

    print("3G Phase 3 Final Hygiene Validation Report")
    print("==========================================")
    overall = "PASS" if r.failed == 0 else "FAIL"
    print(f"Overall status: {overall}")
    print(f"Passed: {r.passed}")
    print(f"Warnings: {r.warnings}")
    print(f"Failed: {r.failed}\n")
    for line in r.lines:
        print(line)
    return 0 if r.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
