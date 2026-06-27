"""Cleanup Sprint 4A.7b one-click Fantrax workspace guard.

Removes validator/demo league IDs (for example abc123) from the live workspace
so Scout will prompt for a real league ID instead of opening an invalid Fantrax
URL.
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Providers.Fantrax.auth.connection_wizard import sanitize_live_workspace_league_id


def main() -> None:
    result = sanitize_live_workspace_league_id()
    print("Fantrax One-Click Workspace Guard Cleanup")
    print("=========================================")
    print(f"Status: {'cleaned' if result.get('changed') else 'clean'}")
    print(f"Message: {result.get('message')}")
    if result.get('removed_league_id'):
        print(f"Removed league ID: {result.get('removed_league_id')}")
    print(f"Current league ID: {result.get('league_id') or '(not set)'}")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
