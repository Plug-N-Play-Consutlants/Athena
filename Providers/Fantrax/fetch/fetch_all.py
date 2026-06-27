"""
Fetch all active Fantrax raw provider data for the active workspace.

Fetch layer responsibility:
- Refresh canonical raw provider snapshots.
- No normalization.
- No analysis.

Active canonical Fantrax snapshots:
- Raw/league_info.json
- Raw/fantrax_player_pool.json
- Raw/transactions.json

Retired legacy endpoint fetches are archived under Archive/ and are not part
of the canonical Fetch path.
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from Core.logger import log_header, log_section, log
from Providers.Fantrax.fetch import fetch_league
from Providers.Fantrax.fetch import fetch_player_pool
from Providers.Fantrax.fetch import fetch_transactions


def main() -> None:
    log_header("FETCH ALL FANTRAX DATA")

    log_section("League")
    fetch_league.main()

    log_section("Player Pool")
    fetch_player_pool.main()

    log_section("Transactions")
    fetch_transactions.main()

    log("")
    log_header("FETCH ALL COMPLETE")


if __name__ == "__main__":
    main()
