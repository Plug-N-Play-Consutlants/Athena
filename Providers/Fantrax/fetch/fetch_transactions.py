"""
Fetch Fantrax transaction history.

Fetch layer responsibility:
- Call provider client.
- Save raw provider payload.
- No normalization.
- No analysis.
"""

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


def fetch_transactions() -> Any:
    """Fetch transaction history and save Raw/transactions.json."""
    client = FantraxClient()
    payload = client.get_transactions(max_results_per_page=1000)
    client.save_raw_json(OUTPUT_FILENAME, payload)

    if isinstance(payload, dict):
        if "pageError" in payload:
            log("Fantrax returned a pageError. Raw response was saved for inspection.")
            return payload

        table = payload.get("table")
        if isinstance(table, dict):
            rows = table.get("rows")
            if isinstance(rows, list):
                log(f"Transaction rows returned: {len(rows)}")

    return payload


def main() -> None:
    log_header("FETCH FANTRAX TRANSACTIONS")

    fetch_transactions()

    log("")
    log("Fetch complete.")


if __name__ == "__main__":
    main()
