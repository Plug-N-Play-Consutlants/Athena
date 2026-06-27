"""
Fetch Fantrax team rosters.

Fetch layer responsibility:
- Call provider client.
- Save raw provider payload.
- No normalization.
- No analysis.
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from Providers.Fantrax.fantrax_client import FantraxClient
from Core.logger import log_header, log


OUTPUT_FILENAME = "team_rosters.json"


def main() -> None:
    log_header("FETCH FANTRAX ROSTERS")

    client = FantraxClient()
    payload = client.get_rosters()
    client.save_raw_json(OUTPUT_FILENAME, payload)

    log("")
    log("Fetch complete.")


if __name__ == "__main__":
    main()

