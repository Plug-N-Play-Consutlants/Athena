"""
AthenaEngine build runner.

Runs the canonical deterministic build pipeline from provider Build outputs
through Knowledge and Intelligence. Fetch is intentionally separate; refresh raw
provider data first when needed.

No silent failure: required stages must exist and execute successfully.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import runpy
import sys
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.logger import log, log_header, log_section


@dataclass(frozen=True)
class BuildStage:
    relative_path: str
    required: bool = True


PIPELINE: tuple[BuildStage, ...] = (
    BuildStage("Providers/Fantrax/build/league_settings.py"),
    BuildStage("Providers/Fantrax/build/player_pool_master.py"),
    BuildStage("Providers/Fantrax/build/player_master.py"),
    BuildStage("Providers/Fantrax/build/transaction_master.py"),
    BuildStage("Knowledge/league_profile.py"),
    BuildStage("Knowledge/player_identity_resolver.py"),
    BuildStage("Knowledge/player_bio.py"),
    BuildStage("Knowledge/player_production.py"),
    BuildStage("Knowledge/player_status.py"),
    BuildStage("Knowledge/player_contracts.py"),
    BuildStage("Knowledge/team_profile.py"),
    BuildStage("Knowledge/transaction_history.py"),
    BuildStage("Intelligence/manager_behavior.py"),
    BuildStage("Intelligence/league_market.py"),
    BuildStage("Knowledge/knowledge_readiness.py"),
    BuildStage("Intelligence/league_archetype.py"),
    BuildStage("Intelligence/analysis_profile.py"),
    BuildStage("Intelligence/valuation_engine.py"),
    BuildStage("Intelligence/team_direction.py"),
)


def validate_pipeline(stages: Iterable[BuildStage] = PIPELINE) -> list[str]:
    """Return missing required build stages without executing the pipeline."""
    missing: list[str] = []
    for stage in stages:
        path = PROJECT_ROOT / stage.relative_path
        if stage.required and not path.exists():
            missing.append(stage.relative_path)
    return missing


def main() -> None:
    log_header("ATHENAENGINE BUILD")
    missing = validate_pipeline()
    if missing:
        log_section("Missing required build stages")
        for relative_path in missing:
            log(f"Missing required module: {relative_path}")
        raise SystemExit(f"BUILD FAILED: {len(missing)} required stage(s) missing")

    executed = 0
    for stage in PIPELINE:
        path = PROJECT_ROOT / stage.relative_path
        log_section(stage.relative_path)
        runpy.run_path(str(path), run_name="__main__")
        executed += 1

    if executed == 0:
        raise SystemExit("BUILD FAILED: no stages executed")

    log_header(f"BUILD COMPLETE: {executed} stage(s) executed")


if __name__ == "__main__":
    main()
