"""
Build a canonical draft pick master from raw Fantrax draft pick data.

Build layer responsibility:
- Read raw provider payloads.
- Normalize provider data into deterministic canonical output.
- No league analysis.
- No asset valuation.
- No intelligence logic.
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR, RAW_DIR


INPUT_DRAFT_PICKS = RAW_DIR / "draft_picks.json"
INPUT_LEAGUE_INFO = RAW_DIR / "league_info.json"

OUTPUT_JSON = OUTPUT_DIR / "draft_picks.json"
OUTPUT_CSV = OUTPUT_DIR / "draft_picks.csv"

PROVIDER = "fantrax"


CSV_FIELDS = [
    "asset_id",
    "league_id",
    "season",
    "original_owner_id",
    "original_owner_name",
    "current_owner_id",
    "current_owner_name",
    "round",
    "overall_pick",
    "pick_label",
    "is_traded",
    "provider",
    "provider_pick_id",
]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _raise_if_provider_error(payload: Any, source_name: str) -> None:
    if not isinstance(payload, dict):
        return

    error = payload.get("error")
    if not error:
        return

    if isinstance(error, dict):
        code = error.get("code", "ERROR")
        message = error.get("message", "Unknown provider error")
    else:
        code = "ERROR"
        message = str(error)

    raise ValueError(f"{source_name} contains a provider error: {code} - {message}")


def _extract_league_id(league_info: dict[str, Any]) -> str:
    return _safe_str(
        league_info.get("leagueId")
        or league_info.get("league_id")
        or league_info.get("id")
        or league_info.get("league", {}).get("id")
    )


def _extract_season(league_info: dict[str, Any]) -> int | None:
    return _safe_int(
        league_info.get("season")
        or league_info.get("seasonYear")
        or league_info.get("year")
        or league_info.get("league", {}).get("season")
        or league_info.get("league", {}).get("seasonYear")
    )


def _extract_pick_rows(raw_draft_picks: Any) -> list[dict[str, Any]]:
    if isinstance(raw_draft_picks, list):
        return [row for row in raw_draft_picks if isinstance(row, dict)]

    if not isinstance(raw_draft_picks, dict):
        return []

    for key in (
        "draftPicks",
        "draft_picks",
        "futureDraftPicks",
        "future_draft_picks",
        "picks",
        "items",
        "records",
        "rows",
    ):
        value = raw_draft_picks.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]

    for wrapper_key in ("data", "result", "body", "payload", "response"):
        wrapped = raw_draft_picks.get(wrapper_key)

        if isinstance(wrapped, dict):
            rows = _extract_pick_rows(wrapped)
            if rows:
                return rows

        if isinstance(wrapped, list):
            return [row for row in wrapped if isinstance(row, dict)]

    return []


def _extract_owner_id(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)

        if isinstance(value, dict):
            owner_id = (
                value.get("id")
                or value.get("teamId")
                or value.get("team_id")
                or value.get("rosterId")
                or value.get("roster_id")
            )
            if owner_id:
                return _safe_str(owner_id)

        elif value:
            return _safe_str(value)

    return ""


def _extract_owner_name(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)

        if isinstance(value, dict):
            owner_name = (
                value.get("name")
                or value.get("teamName")
                or value.get("team_name")
                or value.get("rosterName")
                or value.get("roster_name")
            )
            if owner_name:
                return _safe_str(owner_name)

        elif value:
            return _safe_str(value)

    return ""


def normalize_pick(
    row: dict[str, Any],
    league_id: str,
    default_season: int | None,
) -> dict[str, Any]:
    season = _safe_int(
        row.get("season")
        or row.get("seasonYear")
        or row.get("year")
        or row.get("draftYear")
        or default_season
    )

    round_number = _safe_int(
        row.get("round")
        or row.get("roundNumber")
        or row.get("rnd")
        or row.get("draftRound")
    )

    overall_pick = _safe_int(
        row.get("overallPick")
        or row.get("overall")
        or row.get("pickNumber")
        or row.get("pick")
        or row.get("selection")
    )

    original_owner_id = _extract_owner_id(
        row,
        (
            "originalOwnerId",
            "original_owner_id",
            "originalTeamId",
            "original_team_id",
            "originalRosterId",
            "original_roster_id",
            "originalOwner",
            "originalTeam",
            "originalRoster",
        ),
    )

    original_owner_name = _extract_owner_name(
        row,
        (
            "originalOwnerName",
            "original_owner_name",
            "originalTeamName",
            "original_team_name",
            "originalRosterName",
            "original_roster_name",
            "originalOwner",
            "originalTeam",
            "originalRoster",
        ),
    )

    current_owner_id = _extract_owner_id(
        row,
        (
            "currentOwnerId",
            "current_owner_id",
            "ownerId",
            "teamId",
            "rosterId",
            "currentTeamId",
            "currentRosterId",
            "currentOwner",
            "owner",
            "team",
            "roster",
            "currentTeam",
            "currentRoster",
        ),
    )

    current_owner_name = _extract_owner_name(
        row,
        (
            "currentOwnerName",
            "current_owner_name",
            "ownerName",
            "teamName",
            "rosterName",
            "currentTeamName",
            "currentRosterName",
            "currentOwner",
            "owner",
            "team",
            "roster",
            "currentTeam",
            "currentRoster",
        ),
    )

    provider_pick_id = _safe_str(
        row.get("id")
        or row.get("pickId")
        or row.get("draftPickId")
        or row.get("draft_pick_id")
        or row.get("provider_pick_id")
    )

    asset_id = f"PICK_{season}_{round_number}_{original_owner_id}"

    return {
        "asset_id": asset_id,
        "league_id": league_id,
        "season": season,
        "original_owner_id": original_owner_id,
        "original_owner_name": original_owner_name,
        "current_owner_id": current_owner_id,
        "current_owner_name": current_owner_name,
        "round": round_number,
        "overall_pick": overall_pick,
        "pick_label": f"{season} R{round_number}",
        "is_traded": bool(
            original_owner_id
            and current_owner_id
            and original_owner_id != current_owner_id
        ),
        "provider": PROVIDER,
        "provider_pick_id": provider_pick_id,
    }


def build_draft_pick_master() -> list[dict[str, Any]]:
    log_header("Draft Pick Master Builder")

    raw_draft_picks = read_json(INPUT_DRAFT_PICKS)
    league_info = read_json(INPUT_LEAGUE_INFO)

    _raise_if_provider_error(raw_draft_picks, str(INPUT_DRAFT_PICKS))
    _raise_if_provider_error(league_info, str(INPUT_LEAGUE_INFO))

    league_id = _extract_league_id(league_info)
    default_season = _extract_season(league_info)

    rows = _extract_pick_rows(raw_draft_picks)
    log(f"Loaded {len(rows)} draft pick rows")

    draft_picks = [
        normalize_pick(row=row, league_id=league_id, default_season=default_season)
        for row in rows
    ]

    draft_picks.sort(
        key=lambda pick: (
            pick.get("season") or 0,
            pick.get("round") or 0,
            pick.get("original_owner_name") or "",
            pick.get("asset_id") or "",
        )
    )

    write_json(OUTPUT_JSON, draft_picks)
    write_draft_pick_csv(OUTPUT_CSV, draft_picks)

    log()
    log_section("Summary")
    log(f"Normalized {len(draft_picks)} draft pick assets")
    log(f"Wrote: {OUTPUT_JSON}")
    log(f"Wrote: {OUTPUT_CSV}")
    log("Completed successfully.")

    return draft_picks


def write_draft_pick_csv(path: Path, draft_picks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(draft_picks)


if __name__ == "__main__":
    build_draft_pick_master()
