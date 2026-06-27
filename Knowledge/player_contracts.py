"""
Player Contract Knowledge Builder

Layer: Knowledge

Responsibility:
    Consume canonical player_pool_master output and produce player contract
    knowledge.

Input:
    Output/player_pool_master.json

Output:
    Output/player_contracts.json
    Output/player_contracts.csv

Knowledge modules should not parse raw Fantrax payloads.
"""

from __future__ import annotations

import csv
from collections import Counter
from typing import Any, Dict, List

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR


PLAYER_PROFILES_JSON = OUTPUT_DIR / "player_profiles.json"
PLAYER_POOL_MASTER_JSON = OUTPUT_DIR / "player_pool_master.json"

OUTPUT_JSON = OUTPUT_DIR / "player_contracts.json"
OUTPUT_CSV = OUTPUT_DIR / "player_contracts.csv"


def as_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    return []


def profile_id(profile: Dict[str, Any]) -> str:
    for key in ("fantrax_player_id", "player_id", "id"):
        value = profile.get(key)
        if value not in (None, ""):
            return str(value).strip()

    identity = profile.get("identity")
    if isinstance(identity, dict):
        for key in ("fantrax_player_id", "player_id", "id"):
            value = identity.get(key)
            if value not in (None, ""):
                return str(value).strip()

    return ""


def profile_name(profile: Dict[str, Any]) -> str:
    for key in ("player_name", "name", "full_name", "display_name"):
        value = profile.get(key)
        if value not in (None, ""):
            return str(value).strip()

    identity = profile.get("identity")
    if isinstance(identity, dict):
        for key in ("player_name", "name", "full_name", "display_name"):
            value = identity.get(key)
            if value not in (None, ""):
                return str(value).strip()

    return ""


def build_player_contracts() -> Dict[str, Any]:
    profiles_payload = read_json(PLAYER_PROFILES_JSON)
    pool_payload = read_json(PLAYER_POOL_MASTER_JSON)

    profiles = as_records(profiles_payload)
    pool_records = as_records(pool_payload)
    pool_by_id = {
        str(row.get("fantrax_player_id") or "").strip(): row
        for row in pool_records
        if row.get("fantrax_player_id")
    }

    source_type = pool_payload.get("source_type") if isinstance(pool_payload, dict) else None
    source_live = bool(pool_payload.get("source_live")) if isinstance(pool_payload, dict) else False
    fetched_at = pool_payload.get("fetched_at") if isinstance(pool_payload, dict) else None
    active_season = pool_payload.get("active_season") if isinstance(pool_payload, dict) else None

    records: List[Dict[str, Any]] = []
    matched = 0
    verified = 0

    for profile in profiles:
        pid = profile_id(profile)
        source = pool_by_id.get(pid)

        if source:
            matched += 1

        expiry_year = source.get("contract_expiry_year") if source else None
        years_remaining = source.get("contract_years_remaining") if source else None
        contract_band = source.get("contract_band") if source else "unknown"
        contract_is_verified = bool(source.get("contract_is_verified")) if source else False

        if contract_is_verified:
            verified += 1

        evidence = 1.0 if contract_is_verified else 0.0
        confidence = 1.0 if contract_is_verified and source_live else (0.85 if contract_is_verified else 0.0)

        records.append(
            {
                "fantrax_player_id": pid,
                "player_name": profile_name(profile),
                "fantasy_team": source.get("fantasy_team") if source else "",
                "position": source.get("position") if source else "",
                "contract_expiry_year": expiry_year,
                "expiry_year": expiry_year,
                "years_remaining": years_remaining,
                "contract_years_remaining": years_remaining,
                "contract_band": contract_band,
                "contract_status": contract_band,
                "contract_is_verified": contract_is_verified,
                "source_type": source_type,
                "source_live": source_live,
                "fetched_at": fetched_at,
                "evidence_completeness": evidence,
                "confidence": confidence,
                "missing_fields": [] if contract_is_verified else ["contract_expiry_year"],
            }
        )

    contract_distribution = Counter(row.get("contract_band") or "unknown" for row in records)
    runway_distribution = Counter(
        int(row["years_remaining"])
        for row in records
        if isinstance(row.get("years_remaining"), int)
        and row.get("years_remaining") > 0
    )

    average_evidence = (
        round(sum(float(row.get("evidence_completeness") or 0.0) for row in records) / len(records), 3)
        if records
        else 0.0
    )

    payload = {
        "domain": "contracts",
        "active_season": active_season,
        "source_type": source_type,
        "source_live": source_live,
        "fetched_at": fetched_at,
        "record_count": len(records),
        "source_rows": len(pool_records),
        "matched_contract_rows": matched,
        "verified_contract_records": verified,
        "average_evidence_completeness": average_evidence,
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
        "fantasy_team",
        "position",
        "contract_expiry_year",
        "years_remaining",
        "contract_band",
        "contract_is_verified",
        "source_type",
        "source_live",
        "evidence_completeness",
        "confidence",
    ]

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()

        for record in records:
            writer.writerow({key: record.get(key) for key in headers})


def main() -> None:
    payload = build_player_contracts()

    log_header("Player Contract Knowledge Builder")
    log(f"Player Profiles: {payload.get('record_count')}")
    log(f"Active Season: {payload.get('active_season')}")
    log(f"Source Type: {payload.get('source_type')}")
    log(f"Source Live: {payload.get('source_live')}")
    log(f"Source Rows: {payload.get('source_rows')}")
    log(f"Matched Contract Rows: {payload.get('matched_contract_rows')}")
    log(f"Verified Contract Records: {payload.get('verified_contract_records')}")
    log(f"Average Evidence Completeness: {payload.get('average_evidence_completeness')}")

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
