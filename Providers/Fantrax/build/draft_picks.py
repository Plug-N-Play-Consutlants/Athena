"""Normalize Fantrax draft-pick payload into provider-neutral Draft Knowledge."""
from __future__ import annotations
import csv
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import RAW_DIR, OUTPUT_DIR
from Core.logger import log, log_header, log_section

RAW_DRAFT = RAW_DIR / "draft_picks.json"
LEAGUE_SETTINGS = OUTPUT_DIR / "league_settings.json"
OUTPUT_JSON = OUTPUT_DIR / "draft_picks.json"
OUTPUT_CSV = OUTPUT_DIR / "draft_picks.csv"
GENERATOR_VERSION = "0.6.4.3.2"


def _team_map(settings: Any) -> dict[str, str]:
    rows = settings.get("teams") if isinstance(settings, dict) else []
    return {str(r.get("team_id")): str(r.get("team_name") or r.get("team_id")) for r in (rows or []) if isinstance(r, dict) and r.get("team_id")}


def _team(team_id: Any, teams: dict[str, str]) -> dict[str, str]:
    key = str(team_id or "")
    return {"team_id": key, "team_name": teams.get(key, key)}


def build_draft_picks() -> dict[str, Any]:
    raw = read_optional_json(RAW_DRAFT) or {}
    settings = read_optional_json(LEAGUE_SETTINGS) or {}
    teams = _team_map(settings)
    season = int(settings.get("season") or 0) if isinstance(settings, dict) else 0

    current: list[dict[str, Any]] = []
    for row in raw.get("currentDraftPicks", []) if isinstance(raw, dict) else []:
        if not isinstance(row, dict):
            continue
        rnd = int(row.get("round") or 0)
        pick = int(row.get("pick") or 0)
        owner = _team(row.get("teamId"), teams)
        current.append({
            "asset_type": "draft_pick",
            "year": season,
            "round": rnd,
            "pick_in_round": pick,
            "overall_pick": ((rnd - 1) * len(teams) + pick) if rnd > 0 and pick > 0 and teams else None,
            "original_owner": None,
            "current_owner": owner,
            "ownership_status": "current_owner_confirmed",
            "ownership_provenance": "fantrax_current_draft_board",
        })

    future: list[dict[str, Any]] = []
    for row in raw.get("futureDraftPicks", []) if isinstance(raw, dict) else []:
        if not isinstance(row, dict):
            continue
        original = _team(row.get("originalOwnerTeamId"), teams)
        current_owner = _team(row.get("currentOwnerTeamId"), teams)
        future.append({
            "asset_type": "future_draft_pick",
            "year": int(row.get("year") or 0),
            "round": int(row.get("round") or 0),
            "pick_in_round": None,
            "overall_pick": None,
            "original_owner": original,
            "current_owner": current_owner,
            "ownership_status": "retained" if original["team_id"] == current_owner["team_id"] else "traded",
            "ownership_provenance": "fantrax_future_pick_ownership",
        })

    current.sort(key=lambda x: (x["round"], x["pick_in_round"]))
    future.sort(key=lambda x: (x["year"], x["round"], x["original_owner"]["team_id"]))
    payload = {
        "domain": "draft_assets",
        "schema_version": "draft_knowledge_v1",
        "generator_version": GENERATOR_VERSION,
        "provider": "fantrax",
        "league_id": settings.get("league_id") if isinstance(settings, dict) else None,
        "season": season,
        "team_count": len(teams),
        "current_draft": {
            "pick_count": len(current),
            "round_count": max((x["round"] for x in current), default=0),
            "board_semantics": "configured_draft_slots",
            "selection_count_status": "not_yet_determined",
            "note": "Fantrax draft-board slots describe configured/current ownership state; they do not imply every slot will be exercised.",
            "picks": current,
        },
        "future_draft_assets": {"pick_count": len(future), "years": sorted({x["year"] for x in future if x["year"]}), "picks": future},
        "provenance": {
            "raw_source": "Raw/draft_picks.json",
            "current_owner": "observed",
            "future_original_owner": "observed",
            "future_current_owner": "observed",
            "current_original_owner": "unknown_unless_separately_observed",
            "note": "Current draft-board ownership is stored as observed state. Current-board original ownership remains unknown unless separately reconciled. Future draft assets preserve Fantrax-observed original and current owners. Athena does not invent transactions to explain ownership state.",
        },
    }
    write_json(OUTPUT_JSON, payload)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        fields = ["year", "round", "pick_in_round", "overall_pick", "original_owner_team_id", "original_owner_team_name", "current_owner_team_id", "current_owner_team_name", "ownership_status", "ownership_provenance"]
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader()
        for item in current + future:
            oo = item.get("original_owner") or {}; co = item.get("current_owner") or {}
            writer.writerow({"year":item.get("year"),"round":item.get("round"),"pick_in_round":item.get("pick_in_round"),"overall_pick":item.get("overall_pick"),"original_owner_team_id":oo.get("team_id"),"original_owner_team_name":oo.get("team_name"),"current_owner_team_id":co.get("team_id"),"current_owner_team_name":co.get("team_name"),"ownership_status":item.get("ownership_status"),"ownership_provenance":item.get("ownership_provenance")})
    log_header("DRAFT KNOWLEDGE BUILDER")
    log(f"Current draft picks: {len(current)}")
    log(f"Current rounds: {payload['current_draft']['round_count']}")
    log(f"Future draft assets: {len(future)}")
    log_section("Output Files"); log(str(OUTPUT_JSON)); log(str(OUTPUT_CSV))
    return payload


if __name__ == "__main__":
    build_draft_picks()
