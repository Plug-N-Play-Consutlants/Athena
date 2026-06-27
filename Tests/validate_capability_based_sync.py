"""Validate Sprint 3F.5 capability-based synchronization.

This protects Athena's alpha contract: unavailable optional provider capabilities
must be represented as capability states, not treated as whole-system failure.
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
cap_module = importlib.import_module("Athena.capabilities")  # noqa: E402
router = importlib.import_module("Scout.conversation.router")  # noqa: E402
ScoutContext = importlib.import_module("Scout.conversation.context").ScoutContext  # noqa: E402


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
        print("Capability-Based Sync Validation Report")
        print("=======================================")
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
    backup_dir = ROOT / "Reports" / "_capability_sync_validation_backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        raw_dir / "league_info.json",
        raw_dir / "fantrax_player_pool.json",
        raw_dir / "transactions.json",
        output_dir / "player_pool_master.json",
        output_dir / "player_master.json",
        output_dir / "team_profiles.json",
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
        dashboard = result.get("capability_dashboard") if isinstance(result.get("capability_dashboard"), dict) else {}
        capabilities = result.get("capability_status") if isinstance(result.get("capability_status"), dict) else {}
        operation = result.get("operation_result") if isinstance(result.get("operation_result"), dict) else {}
        metadata = operation.get("metadata") if isinstance(operation.get("metadata"), dict) else {}
        tx = capabilities.get("transactions") if isinstance(capabilities.get("transactions"), dict) else {}
        manager = capabilities.get("manager_activity") if isinstance(capabilities.get("manager_activity"), dict) else {}

        check(report, result.get("ok") is True, "partial_sync_is_successful", f"ok={result.get('ok')}; partial={result.get('partial')}")
        check(report, result.get("partial") is True, "partial_sync_flagged", f"partial={result.get('partial')}")
        check(report, tx.get("status") == "session_required", "transaction_capability_session_required", json.dumps(tx, sort_keys=True))
        check(report, manager.get("status") == "session_required", "manager_activity_limited_by_capability", json.dumps(manager, sort_keys=True))
        check(report, dashboard.get("status") == "partial", "capability_dashboard_partial", json.dumps({"status": dashboard.get("status"), "available": dashboard.get("available_count"), "limited": dashboard.get("limited_count")}, sort_keys=True))
        check(report, isinstance(dashboard.get("lines"), list) and any("Transactions" in line for line in dashboard.get("lines", [])), "dashboard_renders_transaction_line", str(dashboard.get("lines", [])[:4]))
        check(report, isinstance(metadata.get("capability_dashboard"), dict), "operation_metadata_contains_dashboard", str(metadata.keys()))

        ctx = ScoutContext(
            raw_status={},
            team_profiles=[],
            manager_behavior={"records": []},
            league_market={"transaction_count": 0, "asset_movement_count": 0, "market_liquidity": "unknown"},
            knowledge_readiness={},
            player_contracts={},
            player_master=[],
        )
        active_answer = router.most_active_managers(ctx)
        market_answer = router.league_market(ctx)
        check(report, active_answer.get("confidence", 0) >= 0.3, "manager_question_degrades_without_failure", active_answer.get("engine_conclusion", ""))
        check(report, any("transaction" in str(item).lower() for item in active_answer.get("known_limitations", [])), "manager_question_explains_missing_transactions", str(active_answer.get("known_limitations", [])))
        check(report, "limited" in str(market_answer.get("engine_conclusion", "")).lower(), "market_question_degrades_without_invention", market_answer.get("engine_conclusion", ""))
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
