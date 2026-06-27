"""Validate Athena partial sync degradation for optional Fantrax capabilities.

This protects the alpha contract that missing transaction auth must not block
core league/team/player synchronization.
"""

from __future__ import annotations

import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sync_module = importlib.import_module("Athena.sync")  # noqa: E402


class ValidationReport:
    def __init__(self) -> None:
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.warnings: List[str] = []

    def pass_(self, name: str, detail: str = "") -> None:
        self.passed.append(f"[PASS] {name}: {detail}" if detail else f"[PASS] {name}")

    def fail(self, name: str, detail: str = "") -> None:
        self.failed.append(f"[FAIL] {name}: {detail}" if detail else f"[FAIL] {name}")

    def emit(self) -> None:
        status = "PASS" if not self.failed else "FAIL"
        print("Partial Sync Degradation Validation Report")
        print("==========================================")
        print(f"Overall status: {status}")
        print(f"Passed: {len(self.passed)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Failed: {len(self.failed)}")
        print()
        for line in self.passed + self.warnings + self.failed:
            print(line)
        raise SystemExit(0 if not self.failed else 1)


def check(report: ValidationReport, condition: bool, name: str, detail: str = "") -> None:
    if condition:
        report.pass_(name, detail)
    else:
        report.fail(name, detail)


def main() -> None:
    report = ValidationReport()
    raw_dir = ROOT / "Raw"
    output_dir = ROOT / "Output"
    backup_dir = ROOT / "Reports" / "_partial_sync_validation_backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        raw_dir / "league_info.json",
        raw_dir / "fantrax_player_pool.json",
        raw_dir / "transactions.json",
        output_dir / "player_pool_master.json",
        output_dir / "player_master.json",
        output_dir / "transaction_master.json",
        output_dir / "transaction_history.json",
        output_dir / "manager_behavior.json",
        output_dir / "league_market.json",
    ]
    backed_up: Dict[Path, Path] = {}
    for path in files_to_backup:
        if path.exists():
            dest = backup_dir / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            backed_up[path] = dest

    original_pipeline = list(sync_module.FANTRAX_FANTASY_PIPELINE)
    try:
        sync_module.FANTRAX_FANTASY_PIPELINE = [
            {
                "id": "fake_fetch",
                "label": "Fetch Fantrax data",
                "layer": "Fetch",
                "script": "Tests/fixtures/fake_fetch_partial_fantrax.py",
                "requires_fetch": True,
                "validator": "validate_raw_fantrax",
            },
            {
                "id": "fake_player_pool",
                "label": "Build player pool master",
                "layer": "Build",
                "script": "Tests/fixtures/fake_build_player_pool.py",
                "validator": "validate_player_pool_master",
            },
            {
                "id": "fake_player_master",
                "label": "Build player master",
                "layer": "Build",
                "script": "Tests/fixtures/fake_build_player_master.py",
                "validator": "validate_player_master",
            },
            {
                "id": "fake_transaction_master",
                "label": "Build transaction master",
                "layer": "Build",
                "script": "Tests/fixtures/fake_build_player_master.py",
                "validator": "validate_transaction_master",
                "required": False,
                "requires_capability": "transactions",
            },
            {
                "id": "fake_manager_behavior",
                "label": "Build manager behavior",
                "layer": "Intelligence",
                "script": "Tests/fixtures/fake_build_player_master.py",
                "validator": "validate_manager_behavior",
                "required": False,
                "requires_capability": "transactions",
            },
        ]
        result = sync_module.sync(mode="fantasy_league", provider="Fantrax", fetch=True)
        operation = result.get("operation_result") if isinstance(result.get("operation_result"), dict) else {}
        skipped = result.get("skipped_steps") if isinstance(result.get("skipped_steps"), list) else []
        warnings = result.get("warnings") if isinstance(result.get("warnings"), list) else []
        capability = result.get("capability_status") if isinstance(result.get("capability_status"), dict) else {}
        transactions = capability.get("transactions") if isinstance(capability.get("transactions"), dict) else {}

        check(report, result.get("ok") is True, "sync_succeeds_with_missing_transactions", f"ok={result.get('ok')}")
        check(report, result.get("partial") is True, "partial_flag_set", f"partial={result.get('partial')}")
        check(report, operation.get("success") is True, "operation_result_successful", f"stage={operation.get('stage')}")
        check(report, operation.get("stage") == "completed_with_warnings", "stage_completed_with_warnings", f"stage={operation.get('stage')}")
        check(report, bool(warnings), "warnings_returned", f"warnings={warnings}")
        check(report, transactions.get("available") is False, "transaction_capability_unavailable", json.dumps(transactions, sort_keys=True))
        check(report, len(skipped) >= 2, "transaction_modules_skipped", f"skipped={len(skipped)}")
        check(report, any(item.get("requires_capability") == "transactions" for item in skipped), "skipped_steps_explain_capability", str(skipped))
        check(report, any("transaction" in str(item).lower() for item in operation.get("warnings", [])), "operation_warnings_include_transactions", str(operation.get("warnings", [])))
    finally:
        sync_module.FANTRAX_FANTASY_PIPELINE = original_pipeline
        for path in files_to_backup:
            if path.exists():
                path.unlink()
        for original, backup in backed_up.items():
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, original)
        shutil.rmtree(backup_dir, ignore_errors=True)

    report.emit()


if __name__ == "__main__":
    main()
