"""Focused validation for v0.6.4.1.6 current-league semantics hotfix."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Core.json_utils import read_optional_json
from Providers.Fantrax.identity import resolve_league_name
from Athena.sync import _validate_raw_fantrax, _validate_knowledge_readiness
from Athena.capabilities import assess_capabilities


def main() -> int:
    checks = []
    checks.append((ATHENA_VERSION == "0.6.4.1.6", "version", ATHENA_VERSION))
    checks.append((RELEASE_NAME == "Current League Semantics Hotfix", "release_name", RELEASE_NAME))
    raw = read_optional_json(ROOT / "Raw" / "league_info.json")
    resolved = resolve_league_name(raw)
    checks.append(("@" not in resolved and resolved != "unknown", "league_name_resolution", resolved))
    raw_ok, raw_msg, raw_details = _validate_raw_fantrax()
    checks.append((raw_ok and raw_details.get("transactions_available") is True, "zero_transaction_feed_available", raw_msg))
    caps = assess_capabilities("Fantrax").get("by_key", {})
    tx = caps.get("transactions", {})
    checks.append((tx.get("status") == "available", "transaction_capability", str(tx)))
    ready_ok, ready_msg, ready_details = _validate_knowledge_readiness()
    checks.append((ready_ok and ready_details.get("readiness_score") is not None, "knowledge_readiness_score", ready_msg))
    contracts = read_optional_json(ROOT / "Output" / "player_contracts.json")
    pool = read_optional_json(ROOT / "Output" / "player_pool_master.json")
    c = int(contracts.get("record_count") or 0) if isinstance(contracts, dict) else 0
    p = int(pool.get("record_count") or 0) if isinstance(pool, dict) else 0
    checks.append((c == p, "contract_population_matches_active_pool", f"contracts={c}; pool={p}"))
    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    checks.append(("def copy_console" in studio and "clipboard_append" in studio, "studio_copy_console", "entire console clipboard action present"))

    failed = [x for x in checks if not x[0]]
    print("Current League Semantics Hotfix Validation")
    print("=" * 64)
    for ok, name, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall: {'PASS' if not failed else 'FAIL'} | passed={len(checks)-len(failed)} failed={len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
