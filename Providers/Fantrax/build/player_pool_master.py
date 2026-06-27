"""
Fantrax Player Pool Master Builder

Layer: Providers/Fantrax/build

Responsibility:
    Normalize Fantrax live player-pool / roster payloads into a canonical
    provider build output.

Input:
    Raw/fantrax_player_pool.json

Output:
    Output/player_pool_master.json
    Output/player_pool_master.csv

Important:
    Fantrax-specific shapes belong here, not in Knowledge.

Known live Fantrax roster shape:
    {
      "id": "02f9l",
      "contract": {
        "smallId": "3",
        "name": "2027"
      },
      "position": "C",
      "status": "ACTIVE",
      "fantasy_team": "Grabner By the Jussi"
    }

Contract rule:
    contract.name is the expiry year.
    years_remaining = expiry_year - active_season + 1
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_json, read_optional_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import RAW_DIR, OUTPUT_DIR


RAW_PLAYER_POOL_JSON = RAW_DIR / "fantrax_player_pool.json"
LEAGUE_PROFILE_JSON = OUTPUT_DIR / "league_profile.json"
LEAGUE_SETTINGS_JSON = OUTPUT_DIR / "league_settings.json"

OUTPUT_JSON = OUTPUT_DIR / "player_pool_master.json"
OUTPUT_CSV = OUTPUT_DIR / "player_pool_master.csv"


def safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, int):
        return value

    text = str(value).strip()
    if not text:
        return None

    match = re.search(r"\d+", text)
    if not match:
        return None

    try:
        return int(match.group(0))
    except ValueError:
        return None




def clean_fantrax_id(value: Any) -> str:
    return str(value or "").strip().strip("*")


def load_supplemental_player_lookup() -> dict[str, dict[str, Any]]:
    """Load local Fantrax CSV only as supplemental identity/production metadata.

    Live roster/contract/status facts still come from Raw/fantrax_player_pool.json.
    The CSV is used to fill names and NHL teams because the live roster route
    returns player IDs and contract state but not display names.
    """
    lookup: dict[str, dict[str, Any]] = {}
    for path in sorted(RAW_DIR.glob("Fantrax-Players*.csv")) + sorted(RAW_DIR.glob("fantrax-players*.csv")):
        try:
            with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    player_id = clean_fantrax_id(row.get("ID") or row.get("id") or row.get("Player ID"))
                    if player_id:
                        lookup[player_id] = row
        except UnicodeDecodeError:
            with path.open("r", newline="", encoding="latin-1") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    player_id = clean_fantrax_id(row.get("ID") or row.get("id") or row.get("Player ID"))
                    if player_id:
                        lookup[player_id] = row
    return lookup

def as_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]

    return []


def load_active_season() -> int:
    for path in (LEAGUE_PROFILE_JSON, LEAGUE_SETTINGS_JSON):
        payload = read_optional_json(path)
        if not isinstance(payload, dict):
            continue

        for key in ("season", "active_season", "league_season"):
            value = safe_int(payload.get(key))
            if value:
                return value

        league = payload.get("league")
        if isinstance(league, dict):
            for key in ("season", "active_season", "league_season"):
                value = safe_int(league.get(key))
                if value:
                    return value

    return 2025


def normalize_status(status: Any, fantasy_team: str) -> str:
    raw = str(status or "").strip().upper()

    if not fantasy_team:
        if raw in {"WAIVERS", "WAIVER", "W"}:
            return "waivers"
        return "free_agent"

    if raw in {"ACTIVE", "RESERVE", "INJURED_RESERVE", "IR"}:
        return "rostered"

    if raw in {"WAIVERS", "WAIVER", "W"}:
        return "waivers"

    if raw in {"FREE_AGENT", "FREE AGENT", "FA"}:
        return "free_agent"

    return "rostered"


def normalize_roster_slot(status: Any) -> str:
    raw = str(status or "").strip().upper()

    if raw == "ACTIVE":
        return "active"

    if raw == "RESERVE":
        return "reserve"

    if raw in {"INJURED_RESERVE", "IR"}:
        return "injured_reserve"

    if raw in {"WAIVERS", "WAIVER", "W"}:
        return "waivers"

    if raw in {"FREE_AGENT", "FREE AGENT", "FA"}:
        return "free_agent"

    return raw.lower() if raw else ""


def extract_contract(row: Dict[str, Any], active_season: int) -> Dict[str, Any]:
    contract = row.get("contract")

    expiry_year = None
    runway_indicator = None
    raw_contract = contract

    if isinstance(contract, dict):
        expiry_year = safe_int(contract.get("name"))
        runway_indicator = safe_int(contract.get("smallId"))
    else:
        expiry_year = safe_int(contract)

    years_remaining = None
    if expiry_year is not None:
        years_remaining = max(0, expiry_year - active_season + 1)
    elif runway_indicator is not None:
        years_remaining = runway_indicator

    verified = expiry_year is not None and years_remaining is not None

    if years_remaining is None or years_remaining <= 0:
        band = "unknown"
    elif years_remaining == 1:
        band = "expiring"
    elif years_remaining == 2:
        band = "stable"
    else:
        band = "full_runway"

    return {
        "contract_expiry_year": expiry_year,
        "contract_years_remaining": years_remaining,
        "contract_runway_indicator": runway_indicator,
        "contract_band": band,
        "contract_is_verified": verified,
        "raw_contract": raw_contract,
    }


def build_player_pool_master() -> Dict[str, Any]:
    source_payload = read_json(RAW_PLAYER_POOL_JSON)
    active_season = load_active_season()

    source_type = "unknown"
    source_reference = str(RAW_PLAYER_POOL_JSON)
    source_live = False
    fetched_at = None

    if isinstance(source_payload, dict):
        source_type = source_payload.get("source_type") or source_type
        source_reference = source_payload.get("source_reference") or source_reference
        source_live = bool(source_payload.get("is_live"))
        fetched_at = source_payload.get("fetched_at")

    source_records = as_records(source_payload)
    supplemental_lookup = load_supplemental_player_lookup()

    records: List[Dict[str, Any]] = []

    for row in source_records:
        fantrax_player_id = clean_fantrax_id(
            row.get("fantrax_player_id")
            or row.get("player_id")
            or row.get("id")
            or ""
        )
        supplemental = supplemental_lookup.get(fantrax_player_id, {})

        fantasy_team = str(
            row.get("fantasy_team")
            or row.get("team_name")
            or row.get("owner")
            or ""
        ).strip()

        source_status = row.get("status")
        contract = extract_contract(row, active_season)

        record = {
            "fantrax_player_id": fantrax_player_id,
            "player_name": str(row.get("player_name") or row.get("name") or supplemental.get("Player") or "").strip(),
            "nhl_team": str(row.get("nhl_team") or row.get("team") or supplemental.get("Team") or "").strip(),
            "fantasy_team": fantasy_team,
            "position": str(row.get("position") or supplemental.get("Position") or "").strip(),
            "source_status": str(source_status or "").strip(),
            "availability_status": normalize_status(source_status, fantasy_team),
            "roster_slot": normalize_roster_slot(source_status),
            "contract_expiry_year": contract["contract_expiry_year"],
            "contract_years_remaining": contract["contract_years_remaining"],
            "contract_runway_indicator": contract["contract_runway_indicator"],
            "contract_band": contract["contract_band"],
            "contract_is_verified": contract["contract_is_verified"],
            "source_type": source_type,
            "source_reference": source_reference,
            "source_live": source_live,
            "fetched_at": fetched_at,
            "supplemental_identity_source": "local_fantrax_csv" if supplemental else "",
            "source_path": row.get("source_path"),
            "evidence_completeness": 1.0,
        }

        records.append(record)

    verified_contracts = sum(1 for row in records if row.get("contract_is_verified"))
    live_records = sum(1 for row in records if row.get("source_live"))

    status_distribution = Counter(row.get("availability_status") or "unknown" for row in records)
    slot_distribution = Counter(row.get("roster_slot") or "unknown" for row in records)
    contract_distribution = Counter(row.get("contract_band") or "unknown" for row in records)
    runway_distribution = Counter(
        int(row["contract_years_remaining"])
        for row in records
        if isinstance(row.get("contract_years_remaining"), int)
        and row.get("contract_years_remaining") > 0
    )

    payload = {
        "domain": "player_pool_master",
        "provider": "fantrax",
        "source_type": source_type,
        "source_reference": source_reference,
        "source_live": source_live,
        "fetched_at": fetched_at,
        "active_season": active_season,
        "record_count": len(records),
        "verified_contract_records": verified_contracts,
        "live_records": live_records,
        "status_distribution": dict(status_distribution),
        "roster_slot_distribution": dict(slot_distribution),
        "contract_distribution": dict(contract_distribution),
        "contract_runway_distribution": {
            str(key): value for key, value in sorted(runway_distribution.items())
        },
        "records": records,
    }

    write_json(OUTPUT_JSON, payload)
    write_csv(records)

    return payload


def write_csv(records: List[Dict[str, Any]]) -> None:
    headers = [
        "fantrax_player_id",
        "player_name",
        "nhl_team",
        "fantasy_team",
        "position",
        "source_status",
        "availability_status",
        "roster_slot",
        "contract_expiry_year",
        "contract_years_remaining",
        "contract_band",
        "contract_is_verified",
        "source_type",
        "source_live",
        "fetched_at",
    ]

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()

        for record in records:
            writer.writerow({key: record.get(key) for key in headers})


def main() -> None:
    payload = build_player_pool_master()

    log_header("Fantrax Player Pool Master Builder")
    log(f"Source Type: {payload.get('source_type')}")
    log(f"Source Live: {payload.get('source_live')}")
    log(f"Active Season: {payload.get('active_season')}")
    log(f"Records: {payload.get('record_count')}")
    log(f"Verified Contract Records: {payload.get('verified_contract_records')}")

    log_section("Status Distribution")
    for key, value in sorted((payload.get("status_distribution") or {}).items()):
        log(f"  {key}: {value}")

    log_section("Roster Slot Distribution")
    for key, value in sorted((payload.get("roster_slot_distribution") or {}).items()):
        log(f"  {key}: {value}")

    log_section("Contract Distribution")
    for key, value in sorted((payload.get("contract_distribution") or {}).items()):
        log(f"  {key}: {value}")

    runway = payload.get("contract_runway_distribution") or {}
    if runway:
        log_section("Contract Runway")
        for years, count in sorted(runway.items(), key=lambda item: int(item[0])):
            log(f"  {years} years remaining: {count}")

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")


if __name__ == "__main__":
    main()
