"""
Player Status Knowledge Builder

Layer: Knowledge

Responsibility:
    Consume canonical player_pool_master output and produce player availability /
    roster status knowledge.

Input:
    Output/player_pool_master.json

Output:
    Output/player_status.json
    Output/player_status.csv

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

OUTPUT_JSON = OUTPUT_DIR / "player_status.json"
OUTPUT_CSV = OUTPUT_DIR / "player_status.csv"


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


def build_player_status() -> Dict[str, Any]:
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

    records: List[Dict[str, Any]] = []
    matched = 0

    for profile in profiles:
        pid = profile_id(profile)
        source = pool_by_id.get(pid)

        if source:
            matched += 1

        status = source.get("availability_status") if source else "unknown"
        roster_slot = source.get("roster_slot") if source else "unknown"

        evidence = 1.0 if source else 0.0
        confidence = 1.0 if source and source_live else (0.85 if source else 0.0)

        records.append(
            {
                "fantrax_player_id": pid,
                "player_name": profile_name(profile),
                "fantasy_team": source.get("fantasy_team") if source else "",
                "position": source.get("position") if source else "",
                "availability_status": status,
                "roster_slot": roster_slot,
                "source_status": source.get("source_status") if source else "",
                "source_type": source_type,
                "source_live": source_live,
                "fetched_at": fetched_at,
                "evidence_completeness": evidence,
                "confidence": confidence,
            }
        )

    status_distribution = Counter(row.get("availability_status") or "unknown" for row in records)
    slot_distribution = Counter(row.get("roster_slot") or "unknown" for row in records)

    average_evidence = (
        round(sum(float(row.get("evidence_completeness") or 0.0) for row in records) / len(records), 3)
        if records
        else 0.0
    )

    payload = {
        "domain": "player_status",
        "source_type": source_type,
        "source_live": source_live,
        "fetched_at": fetched_at,
        "record_count": len(records),
        "source_rows": len(pool_records),
        "matched_status_rows": matched,
        "average_evidence_completeness": average_evidence,
        "status_distribution": dict(status_distribution),
        "roster_slot_distribution": dict(slot_distribution),
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
        "availability_status",
        "roster_slot",
        "source_status",
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
    payload = build_player_status()

    log_header("Player Status Knowledge Builder")
    log(f"Player Profiles: {payload.get('record_count')}")
    log(f"Source Type: {payload.get('source_type')}")
    log(f"Source Live: {payload.get('source_live')}")
    log(f"Source Rows: {payload.get('source_rows')}")
    log(f"Matched Status Rows: {payload.get('matched_status_rows')}")
    log(f"Average Evidence Completeness: {payload.get('average_evidence_completeness')}")

    log_section("Status Distribution")
    for key, value in sorted((payload.get("status_distribution") or {}).items()):
        log(f"  {key}: {value}")

    log_section("Roster Slot Distribution")
    for key, value in sorted((payload.get("roster_slot_distribution") or {}).items()):
        log(f"  {key}: {value}")

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")


if __name__ == "__main__":
    main()
