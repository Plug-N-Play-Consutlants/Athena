"""Optional sync stage for documented historical Fantrax lineup snapshots.

Works after the canonical league-info fetch. It never fabricates past lineups
from a current roster and never causes the otherwise healthy sync to fail.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Athena.Investigation.fantrax_period_calendar import resolve_unified_period
from Athena.Investigation.historical_roster_attribution import backfill_period_rosters
from Athena.workspace import get_workspace_value
from Core.project_paths import RAW_DIR, OUTPUT_DIR


def run(*, league_info: dict | None = None, league_id: str | None = None,
        season: int | str | None = None, client_factory=None,
        output_dir: Path | None = None, clock: datetime | None = None) -> dict:
    now = clock or datetime.now(timezone.utc)
    target = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    manifest_path = target / "PeriodRosters" / "sync_manifest.json"
    league_id = league_id or get_workspace_value("league_id")
    season = season or get_workspace_value("season")
    expected_teams = get_workspace_value("team_count")
    try:
        if league_info is None:
            league_info = json.loads((RAW_DIR / "league_info.json").read_text(encoding="utf-8"))
        if not isinstance(league_info, dict) or not league_id or not str(season).isdigit():
            raise ValueError("Canonical Fantrax league info/workspace unavailable")
        calendar = resolve_unified_period(league_info, at=now)
        if calendar.get("status") != "calendar_closed" or type(calendar.get("period")) is not int:
            raise ValueError("No verified elapsed lineup period in Fantrax league calendar")
        result = backfill_period_rosters(league_id=league_id, season=season,
                                         through_period=calendar["period"],
                                         expected_teams=int(expected_teams) if expected_teams else None,
                                         output_dir=target, client_factory=client_factory, clock=now)
        manifest = {"schema": "athena.historical_roster_sync.v1", "league_id": league_id,
                    "season": str(season), "selected_period": calendar["period"],
                    "status": result["status"], "verified_count": result["verified_count"],
                    "attempted_count": len(result["periods"]),
                    "periods": {str(k): {"status": v.get("status"), "verified": v.get("verified", False),
                                        "team_count": v.get("team_count", 0), "reason": v.get("reason", "")}
                                for k,v in result["periods"].items()},
                    "acquired_at": now.isoformat()}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        manifest = {"schema": "athena.historical_roster_sync.v1", "league_id": str(league_id or ""),
                    "season": str(season or ""), "status": "unverified",
                    "reason": str(exc)[:180], "verified_count": 0, "attempted_count": 0,
                    "acquired_at": now.isoformat()}
    except Exception as exc:
        manifest = {"schema": "athena.historical_roster_sync.v1", "league_id": str(league_id or ""),
                    "season": str(season or ""), "status": "unavailable",
                    "reason": type(exc).__name__ + " fetching period rosters", "verified_count": 0,
                    "attempted_count": 0, "acquired_at": now.isoformat()}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp = manifest_path.with_suffix(".tmp")
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(manifest_path)
    return manifest


if __name__ == "__main__":
    status = run()
    print(f"Historical roster snapshots: {status['status']} "
          f"({status.get('verified_count', 0)}/{status.get('attempted_count', 0)} verified)")
