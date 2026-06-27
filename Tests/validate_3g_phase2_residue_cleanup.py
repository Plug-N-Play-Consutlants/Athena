from __future__ import annotations

import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ENGINE_LABEL  # noqa: E402
from Athena.workspace import load_workspace, secrets_status  # noqa: E402


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


def _path_exists(relative: str) -> bool:
    return (PROJECT_ROOT / relative).exists()


def main() -> int:
    r = Report()

    if ATHENA_VERSION == "0.5.0-drop3g2" and SCOUT_VERSION == "v0.5.0-drop3g2":
        r.ok("single_version_source", f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}")
    else:
        r.fail("single_version_source", f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}")

    duplicate_roots = [
        p for p in [
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
        ] if _path_exists(p)
    ]
    if not duplicate_roots:
        r.ok("nested_legacy_roots_removed", "no nested or top-level duplicate roots detected")
    else:
        r.fail("nested_legacy_roots_removed", ", ".join(duplicate_roots))

    pycache = list(PROJECT_ROOT.rglob("__pycache__")) + list(PROJECT_ROOT.rglob("*.pyc"))
    if not pycache:
        r.ok("python_cache_removed", "no __pycache__ or .pyc files detected")
    else:
        r.warn("python_cache_removed", f"cache artifacts remain: {len(pycache)}")

    workspace_payload = load_workspace()
    workspace = workspace_payload.get("workspace", {})
    text = json.dumps(workspace_payload)
    if "validation_league_id" not in text and "test_league_id_provider_registry" not in text:
        r.ok("workspace_not_test_contaminated", f"league_id={workspace.get('league_id')}")
    else:
        r.fail("workspace_not_test_contaminated", text[:300])

    if workspace.get("engine_version") == ENGINE_LABEL:
        r.ok("workspace_engine_version_current", workspace.get("engine_version"))
    else:
        r.fail("workspace_engine_version_current", str(workspace.get("engine_version")))

    gitignore = PROJECT_ROOT / ".gitignore"
    gitignore_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    required_ignores = ["Configuration/secrets.local.json", "Raw/", "Output/", "Reports/", "Logs/", "__pycache__/", "*.py[cod]"]
    missing = [item for item in required_ignores if item not in gitignore_text]
    if not missing:
        r.ok("gitignore_runtime_hardened", "runtime artifacts and local secrets ignored")
    else:
        r.fail("gitignore_runtime_hardened", f"missing: {missing}")

    status = secrets_status()
    if "fantrax_cookie_present" in status and "fantrax_league_secret_present" in status:
        r.ok("credential_status_split_available", f"cookie={status.get('fantrax_cookie_present')}; league_secret={status.get('fantrax_league_secret_present')}")
    else:
        r.fail("credential_status_split_available", str(status))

    print("3G Phase 2 Residue Cleanup Validation Report")
    print("============================================")
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
