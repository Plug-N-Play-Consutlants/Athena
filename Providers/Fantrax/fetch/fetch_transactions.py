"""Fetch Fantrax transaction evidence across canonical transaction views."""
from __future__ import annotations
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Providers.Fantrax.fantrax_client import FantraxClient
from Core.logger import log_header, log

OUTPUT_FILENAME = "transactions.json"


def _row_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    table = payload.get("table")
    rows = table.get("rows") if isinstance(table, dict) else None
    return len(rows) if isinstance(rows, list) else 0


def fetch_transactions() -> Any:
    """Fetch Claim/Drop and Trade evidence and save the raw provider bundle."""
    client = FantraxClient()
    payload = client.get_transaction_evidence(max_results_per_page=1000)
    client.save_raw_json(OUTPUT_FILENAME, payload)

    views = payload.get("views") if isinstance(payload, dict) else {}
    if isinstance(views, dict):
        for view, view_payload in views.items():
            client.save_raw_json(f"transactions_{str(view).lower()}.json", view_payload)
            log(f"Transaction rows returned [{view}]: {_row_count(view_payload)}")
    return payload


def main() -> None:
    log_header("FETCH FANTRAX TRANSACTION EVIDENCE")
    fetch_transactions()
    log("")
    log("Fetch complete.")


if __name__ == "__main__":
    main()
