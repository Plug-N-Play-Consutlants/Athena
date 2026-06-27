"""
Player Bio Knowledge Builder.

Normalizes NHL player landing payloads into canonical player biography facts.
This is a Knowledge-layer enrichment module: it joins canonical identity records
with raw NHL provider payloads and produces provider-independent bio facts.

Inputs:
    Output/player_identity_map.json
    Raw/nhl_player_landing.json

Outputs:
    Output/player_bio.json
    Output/player_bio.csv
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from Core.config import get_workspace_value
from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR, RAW_DIR

IDENTITY_MAP_PATH = OUTPUT_DIR / "player_identity_map.json"
NHL_PLAYER_LANDING_PATH = RAW_DIR / "nhl_player_landing.json"

OUTPUT_JSON = OUTPUT_DIR / "player_bio.json"
OUTPUT_CSV = OUTPUT_DIR / "player_bio.csv"


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _round(value: Any, digits: int = 3) -> Any:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return value


def _parse_date(value: Any) -> date | None:
    text = _safe_str(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _season_age_as_of() -> date:
    """Use Oct. 1 of workspace season as the dynasty/fantasy age anchor."""
    workspace_season = _safe_str(get_workspace_value("workspace.season", ""))
    if len(workspace_season) >= 4 and workspace_season[:4].isdigit():
        return date(int(workspace_season[:4]), 10, 1)
    return date.today()


def _age_on(birth_date: date | None, as_of: date) -> float | None:
    if birth_date is None:
        return None
    days = (as_of - birth_date).days
    if days < 0:
        return None
    return _round(days / 365.2425, 2)


def _landing_records_by_id(raw_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    players = raw_payload.get("players", []) if isinstance(raw_payload, dict) else []
    by_id: dict[str, dict[str, Any]] = {}

    if not isinstance(players, list):
        return by_id

    for row in players:
        if not isinstance(row, dict):
            continue
        player_id = _safe_str(row.get("nhl_player_id"))
        payload = row.get("payload", {})
        if player_id and isinstance(payload, dict):
            by_id[player_id] = payload

    return by_id


def _name_field(value: Any) -> str:
    if isinstance(value, dict):
        return _safe_str(value.get("default") or value.get("en") or value.get("fr"))
    return _safe_str(value)


def _extract_payload_bio(payload: dict[str, Any]) -> dict[str, Any]:
    birth_date_value = payload.get("birthDate") or payload.get("birthdate")
    birth_date = _parse_date(birth_date_value)

    return {
        "birth_date": birth_date.isoformat() if birth_date else "",
        "birth_city": _safe_str(payload.get("birthCity")),
        "birth_state_province": _safe_str(payload.get("birthStateProvince")),
        "birth_country": _safe_str(payload.get("birthCountry")),
        "height_inches": _safe_int(payload.get("heightInInches")),
        "height_centimeters": _safe_int(payload.get("heightInCentimeters")),
        "weight_pounds": _safe_int(payload.get("weightInPounds")),
        "weight_kilograms": _safe_int(payload.get("weightInKilograms")),
        "shoots_catches": _safe_str(payload.get("shootsCatches")),
        "nhl_current_team_abbrev": _safe_str(
            payload.get("currentTeamAbbrev")
            or _name_field(payload.get("currentTeamAbbrev"))
        ),
        "nhl_current_team_name": _name_field(payload.get("fullTeamName")),
        "nhl_position": _safe_str(payload.get("position") or payload.get("positionCode")),
        "sweater_number": _safe_int(payload.get("sweaterNumber")),
        "is_active": payload.get("isActive"),
    }


def _evidence_completeness(record: dict[str, Any]) -> float:
    fields = [
        "birth_date",
        "age_as_of_season_start",
        "height_inches",
        "weight_pounds",
        "shoots_catches",
        "birth_country",
        "nhl_current_team_abbrev",
    ]
    available = sum(1 for field in fields if record.get(field) not in (None, ""))
    return round(available / len(fields), 3)


def build_player_bio() -> list[dict[str, Any]]:
    log_header("Player Bio Knowledge Builder")

    identity_rows = read_json(IDENTITY_MAP_PATH)
    landing_raw = read_json(NHL_PLAYER_LANDING_PATH)

    if not isinstance(identity_rows, list):
        raise ValueError("player_identity_map.json must contain a list of records.")
    if not isinstance(landing_raw, dict):
        raise ValueError("nhl_player_landing.json must contain an object with a players list.")

    landing_by_id = _landing_records_by_id(landing_raw)
    age_as_of = _season_age_as_of()

    records: list[dict[str, Any]] = []

    for row in identity_rows:
        if not isinstance(row, dict):
            continue

        nhl_player_id = _safe_str(row.get("nhl_player_id"))
        payload = landing_by_id.get(nhl_player_id, {})
        payload_bio = _extract_payload_bio(payload) if payload else {}
        birth_date = _parse_date(payload_bio.get("birth_date"))
        age = _age_on(birth_date, age_as_of)

        record = {
            "fantrax_player_id": row.get("fantrax_player_id"),
            "nhl_player_id": nhl_player_id,
            "player_name": row.get("canonical_player_name") or row.get("nhl_player_name") or row.get("fantrax_player_name"),
            "fantrax_player_name": row.get("fantrax_player_name"),
            "nhl_player_name": row.get("nhl_player_name"),
            "fantrax_position": row.get("fantrax_position"),
            "nhl_position": payload_bio.get("nhl_position") or row.get("nhl_position"),
            "fantasy_team": row.get("fantasy_team") or row.get("owner_team") or row.get("team_name"),
            "nhl_team": payload_bio.get("nhl_current_team_abbrev") or row.get("nhl_team"),
            "birth_date": payload_bio.get("birth_date", ""),
            "age_as_of_date": age_as_of.isoformat(),
            "age_as_of_season_start": age,
            "birth_city": payload_bio.get("birth_city", ""),
            "birth_state_province": payload_bio.get("birth_state_province", ""),
            "birth_country": payload_bio.get("birth_country", ""),
            "height_inches": payload_bio.get("height_inches"),
            "height_centimeters": payload_bio.get("height_centimeters"),
            "weight_pounds": payload_bio.get("weight_pounds"),
            "weight_kilograms": payload_bio.get("weight_kilograms"),
            "shoots_catches": payload_bio.get("shoots_catches", ""),
            "sweater_number": payload_bio.get("sweater_number"),
            "is_active": payload_bio.get("is_active"),
            "bio_source": "nhl_player_landing" if payload else "missing",
            "identity_resolution_status": row.get("resolution_status"),
            "identity_match_confidence": row.get("match_confidence"),
        }
        record["evidence_completeness"] = _evidence_completeness(record)
        records.append(record)

    records.sort(key=lambda item: (_safe_str(item.get("player_name")).lower()))

    write_json(OUTPUT_JSON, records)
    write_player_bio_csv(OUTPUT_CSV, records)

    matched = [row for row in records if row.get("bio_source") == "nhl_player_landing"]
    ages = [_safe_float(row.get("age_as_of_season_start")) for row in matched]
    ages = [age for age in ages if age is not None]
    avg_age = round(sum(ages) / len(ages), 2) if ages else 0.0
    avg_completeness = round(
        sum(_safe_float(row.get("evidence_completeness"), 0.0) or 0.0 for row in records) / len(records),
        3,
    ) if records else 0.0

    log(f"Identity Rows: {len(identity_rows)}")
    log(f"Landing Payloads: {len(landing_by_id)}")
    log(f"Bio Records: {len(records)}")
    log(f"Matched Bio Records: {len(matched)}")
    log(f"Average Age: {avg_age}")
    log(f"Average Evidence Completeness: {avg_completeness}")

    log_section("Youngest Resolved Players")
    for row in sorted(matched, key=lambda item: _safe_float(item.get("age_as_of_season_start"), 999.0) or 999.0)[:10]:
        log(
            f"  {row.get('player_name')}: age {row.get('age_as_of_season_start')} | "
            f"{row.get('nhl_position')} | {row.get('nhl_team')}"
        )

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")

    return records


def write_player_bio_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "fantrax_player_id",
        "nhl_player_id",
        "player_name",
        "fantrax_position",
        "nhl_position",
        "fantasy_team",
        "nhl_team",
        "birth_date",
        "age_as_of_date",
        "age_as_of_season_start",
        "birth_city",
        "birth_state_province",
        "birth_country",
        "height_inches",
        "height_centimeters",
        "weight_pounds",
        "weight_kilograms",
        "shoots_catches",
        "sweater_number",
        "is_active",
        "bio_source",
        "identity_resolution_status",
        "identity_match_confidence",
        "evidence_completeness",
    ]

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field) for field in fieldnames})


if __name__ == "__main__":
    build_player_bio()
