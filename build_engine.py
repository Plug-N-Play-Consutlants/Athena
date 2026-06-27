"""
Sports Intelligence Engine build runner.

Runs the current canonical deterministic pipeline from provider Build outputs
through Knowledge and Intelligence. Fetch is intentionally separate; refresh raw
provider data first when needed.
"""

from __future__ import annotations

from pathlib import Path
import runpy
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.logger import log, log_header, log_section


PIPELINE = [
    "Providers/Fantrax/build/league_settings.py",
    "Providers/Fantrax/build/player_pool_master.py",
    "Providers/Fantrax/build/player_master.py",
    "Providers/Fantrax/build/transaction_master.py",
    "Knowledge/league_profile.py",
    "Knowledge/player_identity_resolver.py",
    "Knowledge/player_bio.py",
    "Knowledge/player_production.py",
    "Knowledge/player_status.py",
    "Knowledge/player_contracts.py",
    "Knowledge/team_profile.py",
    "Knowledge/transaction_history.py",
    "Intelligence/manager_behavior.py",
    "Intelligence/league_market.py",
    "Knowledge/knowledge_readiness.py",
    "Intelligence/league_archetype.py",
    "Intelligence/analysis_profile.py",
    "Intelligence/valuation_engine.py",
    "Intelligence/team_direction.py",
]


def main() -> None:
    log_header("SPORTS INTELLIGENCE ENGINE BUILD")
    for relative_path in PIPELINE:
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            log_section("Missing")
            log(f"Skipped missing module: {relative_path}")
            continue
        log_section(relative_path)
        runpy.run_path(str(path), run_name="__main__")
    log_header("BUILD COMPLETE")


if __name__ == "__main__":
    main()
