"""Validate 3G Phase 1 runtime hygiene.

This validator intentionally checks live runtime state. It does not write a
validation league id, does not overwrite secrets, and does not use test fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Athena.workspace import load_workspace, repair_workspace_file, is_placeholder_league_id, secrets_status
from Core.version import ATHENA_VERSION, SCOUT_VERSION, ENGINE_LABEL
import Athena
from Scout.app import SCOUT_VERSION as APP_SCOUT_VERSION, _effective_league_id


class Report:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    def ok(self, name, detail=""):
        self.passed.append((name, detail))
    def fail(self, name, detail=""):
        self.failed.append((name, detail))
    def warn(self, name, detail=""):
        self.warnings.append((name, detail))
    def emit(self):
        status = "PASS" if not self.failed else "FAIL"
        print("3G Phase 1 Runtime Hygiene Validation Report")
        print("=" * 48)
        print(f"Overall status: {status}")
        print(f"Passed: {len(self.passed)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Failed: {len(self.failed)}")
        print("")
        for n, d in self.passed:
            print(f"[PASS] {n}: {d}")
        for n, d in self.warnings:
            print(f"[WARN] {n}: {d}")
        for n, d in self.failed:
            print(f"[FAIL] {n}: {d}")
        if self.failed:
            raise SystemExit(1)
        raise SystemExit(0)


def main():
    r = Report()
    payload = repair_workspace_file()
    workspace = payload.get("workspace", {})

    league_id = workspace.get("league_id")
    if league_id and not is_placeholder_league_id(league_id):
        r.ok("workspace_league_id_sanitized", f"league_id={league_id}")
    else:
        r.fail("workspace_league_id_sanitized", f"league_id={league_id}")

    history_text = json.dumps(workspace.get("operation_history") or [])
    if "validation_league_id" not in history_text and "Tests/fixtures/" not in history_text:
        r.ok("operation_history_not_test_contaminated", f"records={len(workspace.get('operation_history') or [])}")
    else:
        r.fail("operation_history_not_test_contaminated", "validation fixture content remains in operation history")

    if workspace.get("engine_version") == ENGINE_LABEL:
        r.ok("workspace_engine_version_current", workspace.get("engine_version"))
    else:
        r.fail("workspace_engine_version_current", str(workspace.get("engine_version")))

    if getattr(Athena, "__version__", "") == ATHENA_VERSION and APP_SCOUT_VERSION == SCOUT_VERSION:
        r.ok("single_version_source", f"Athena={ATHENA_VERSION}; Scout={APP_SCOUT_VERSION}")
    else:
        r.fail("single_version_source", f"Athena={getattr(Athena,'__version__','')}; Scout={APP_SCOUT_VERSION}")

    effective = _effective_league_id(workspace)
    if effective and not is_placeholder_league_id(effective):
        r.ok("scout_effective_league_id_clean", effective)
    else:
        r.fail("scout_effective_league_id_clean", f"effective={effective}")

    sec = secrets_status()
    if "fantrax_cookie_present" in sec and "fantrax_league_secret_present" in sec:
        r.ok("credential_status_split", f"cookie={sec.get('fantrax_cookie_present')}; league_secret={sec.get('fantrax_league_secret_present')}")
    else:
        r.fail("credential_status_split", str(sec))

    # Phase 1 reports duplicate roots but does not fail on them. Phase 2 can remove/archive them.
    duplicate_roots = [rel for rel in ("Athena", "Sports_Intelligence_Engine_2.0") if (PROJECT_ROOT / rel).is_dir()]
    if duplicate_roots:
        r.warn("duplicate_legacy_roots_detected", ", ".join(duplicate_roots))
    else:
        r.ok("duplicate_legacy_roots_detected", "none")

    r.emit()


if __name__ == "__main__":
    main()
