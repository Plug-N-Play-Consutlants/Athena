from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Providers.Fantrax.fantrax_client import FantraxClient
from Providers.Fantrax.build.transaction_master import _records, _group_rows, _normalize_group
from Knowledge.transaction_history import build_transaction_history


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return bool(condition)


def trade_fixture() -> dict:
    """Observed Fantrax TRADE shape: txSetId + from/to cells, no transactionCode."""
    return {
        "filterSettings": {"view": "TRADE"},
        "table": {"rows": [
            {
                "txSetId": "trade-set-1", "resultCode": "EXECUTED",
                "scorer": {"scorerId": "p1", "name": "Player One", "posShortNames": "C"},
                "cells": [
                    {"key": "from", "teamId": "team-a", "content": "Team A"},
                    {"key": "to", "teamId": "team-b", "content": "Team B"},
                    {"key": "date", "content": "Mon Mar 4, 2019, 5:11PM", "rowspan": 2},
                    {"key": "week", "content": "23"},
                ],
            },
            {
                "txSetId": "trade-set-1", "resultCode": "EXECUTED",
                "scorer": {"scorerId": "p2", "name": "Player Two", "posShortNames": "LW"},
                "cells": [
                    {"key": "from", "teamId": "team-b", "content": "Team B"},
                    {"key": "to", "teamId": "team-a", "content": "Team A"},
                    {"key": "week", "content": "23"},
                ],
            },
        ]},
    }


def claim_fixture() -> dict:
    return {"filterSettings": {"view": "CLAIM_DROP"}, "table": {"rows": []}}


def main() -> None:
    ok = []
    ok.append(check("version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 6, 5, 0, 0), ATHENA_VERSION))
    ok.append(check("release", bool(RELEASE_NAME), RELEASE_NAME))

    client = FantraxClient.__new__(FantraxClient)
    calls = []
    def fake_get(max_results_per_page=1000, view=None):
        calls.append(view)
        return trade_fixture() if view == "TRADE" else claim_fixture()
    with patch.object(client, "get_transactions", side_effect=fake_get):
        bundle = client.get_transaction_evidence(max_results_per_page=1000)
    ok.append(check("explicit_views", calls == ["CLAIM_DROP", "TRADE"], str(calls)))
    ok.append(check("views_preserved", set((bundle.get("views") or {}).keys()) == {"CLAIM_DROP", "TRADE"}))

    rows = _records(bundle)
    ok.append(check("bundle_rows", len(rows) == 2, str(len(rows))))
    ok.append(check("trade_view_provenance", all(r.get("_fantrax_view") == "TRADE" for r in rows), str([r.get("_fantrax_view") for r in rows])))
    groups = _group_rows(rows)
    tx = _normalize_group(groups[0], 0)
    ok.append(check("trade_without_transaction_code", tx.get("transaction_type") == "trade", str(tx.get("transaction_type"))))
    ok.append(check("trade_counterparties", len(tx.get("participants") or []) == 2, str(tx.get("participants"))))
    moves = tx.get("asset_movements") or []
    ok.append(check("directional_asset_movements", len(moves) == 2 and all(m.get("from_participant_id") and m.get("to_participant_id") for m in moves), str(moves)))
    ok.append(check("trade_assets", {m.get("asset_name") for m in moves} == {"Player One", "Player Two"}, str(moves)))
    with patch("Knowledge.transaction_history.read_json", return_value={"records": [tx]}), \
         patch("Knowledge.transaction_history.write_json"), \
         patch("Knowledge.transaction_history._write_csv"):
        knowledge = build_transaction_history()
    kmoves = knowledge.get("asset_movements") or []
    ok.append(check("knowledge_preserves_trade_direction", len(kmoves) == 2 and all(m.get("from_team_id") and m.get("to_team_id") for m in kmoves), str(kmoves)))
    ok.append(check("knowledge_counts_both_counterparties", len(knowledge.get("team_transaction_history") or []) == 2, str(knowledge.get("team_transaction_history"))))
    raise SystemExit(0 if all(ok) else 1)


if __name__ == "__main__":
    main()
