"""
Transaction History Knowledge Builder

Layer: Knowledge

Responsibility:
    Consume canonical transaction_master output and produce deterministic
    transaction history knowledge. This module does not parse raw provider
    payloads and does not infer official league finances.

Input:
    Output/transaction_master.json

Output:
    Output/transaction_history.json
    Output/transaction_history.csv
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from typing import Any, Dict, List

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR


INPUT_JSON = OUTPUT_DIR / "transaction_master.json"
OUTPUT_JSON = OUTPUT_DIR / "transaction_history.json"
OUTPUT_CSV = OUTPUT_DIR / "transaction_history.csv"


SCHEMA_VERSION = "0.3.1"


def _records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [row for row in payload["records"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _participant_key(participant: Dict[str, Any]) -> str:
    return str(
        participant.get("participant_id")
        or participant.get("participant_name")
        or participant.get("manager_id")
        or participant.get("manager_name")
        or "unknown"
    ).strip() or "unknown"


def _participant_name(participant: Dict[str, Any]) -> str:
    return str(participant.get("participant_name") or participant.get("manager_name") or "").strip()


def _participant_id(participant: Dict[str, Any]) -> str:
    return str(participant.get("participant_id") or participant.get("manager_id") or "").strip()


def _asset_key(asset: Dict[str, Any]) -> str:
    return str(asset.get("asset_id") or asset.get("asset_name") or "unknown").strip() or "unknown"


def build_transaction_history() -> Dict[str, Any]:
    payload = read_json(INPUT_JSON)
    records = _records(payload)

    by_type = Counter(row.get("transaction_type") or "unknown" for row in records)
    by_status = Counter(row.get("status") or "unknown" for row in records)
    by_week = Counter(str(row.get("season_week") or "unknown") for row in records)
    asset_movements_by_type = Counter()

    team_history: Dict[str, Dict[str, Any]] = {}
    player_movements: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    asset_movements: List[Dict[str, Any]] = []
    transaction_timeline: List[Dict[str, Any]] = []

    for row in records:
        transaction_id = row.get("transaction_id")
        timestamp = row.get("timestamp")
        transaction_type = row.get("transaction_type") or "unknown"
        status = row.get("status") or "unknown"
        week = row.get("season_week") or ""
        observed_fee_total = float(row.get("fee_total") or row.get("observed_transaction_fee_total") or 0)
        participants = [p for p in (row.get("participants") or []) if isinstance(p, dict)]
        assets = [a for a in (row.get("assets") or []) if isinstance(a, dict)]

        transaction_timeline.append(
            {
                "transaction_id": transaction_id,
                "timestamp": timestamp,
                "season_week": week,
                "transaction_type": transaction_type,
                "status": status,
                "summary": row.get("summary", ""),
                "participant_count": len(participants),
                "asset_count": len(assets),
                "observed_transaction_fee_total": round(observed_fee_total, 2),
                "financial_provenance": "observed_from_transaction_history_not_official_ledger",
            }
        )

        for participant in participants:
            key = _participant_key(participant)
            entry = team_history.setdefault(
                key,
                {
                    "team_id": _participant_id(participant),
                    "team_name": _participant_name(participant),
                    "transaction_count": 0,
                    "transaction_types": Counter(),
                    "asset_movements": Counter(),
                    "asset_types": Counter(),
                    "observed_transaction_fee_total": 0.0,
                    "financial_provenance": "observed_from_transaction_history_not_official_ledger",
                    "transactions": [],
                },
            )
            entry["transaction_count"] += 1
            entry["transaction_types"][transaction_type] += 1
            entry["observed_transaction_fee_total"] = round(
                float(entry["observed_transaction_fee_total"]) + observed_fee_total,
                2,
            )
            entry["transactions"].append(transaction_id)

            for asset in assets:
                movement = asset.get("movement") or "involved"
                asset_type = asset.get("asset_type") or "unknown"
                entry["asset_movements"][movement] += 1
                entry["asset_types"][asset_type] += 1

        for asset in assets:
            movement = asset.get("movement") or "involved"
            asset_type = asset.get("asset_type") or "unknown"
            asset_movements_by_type[movement] += 1

            movement_record = {
                "transaction_id": transaction_id,
                "timestamp": timestamp,
                "season_week": week,
                "transaction_type": transaction_type,
                "asset_type": asset_type,
                "asset_id": asset.get("asset_id", ""),
                "asset_name": asset.get("asset_name", ""),
                "movement": movement,
                "team_id": ((asset.get("movement_context") or {}).get("team_id") or ""),
                "team_name": ((asset.get("movement_context") or {}).get("team_name") or ""),
            }
            asset_movements.append(movement_record)

            if asset_type == "player":
                player_movements[_asset_key(asset)].append(movement_record)

    team_records = []
    for entry in team_history.values():
        entry["transaction_types"] = dict(entry["transaction_types"])
        entry["asset_movements"] = dict(entry["asset_movements"])
        entry["asset_types"] = dict(entry["asset_types"])
        team_records.append(entry)

    history = {
        "domain": "transaction_history",
        "schema_version": SCHEMA_VERSION,
        "source": "transaction_master",
        "record_count": len(records),
        "asset_movement_count": len(asset_movements),
        "transaction_type_distribution": dict(by_type),
        "transaction_status_distribution": dict(by_status),
        "transaction_week_distribution": dict(by_week),
        "asset_movement_distribution": dict(asset_movements_by_type),
        "financial_provenance": {
            "official_finance_source": "Fantrax finance page under team menu",
            "transaction_history_fee_fields": "observed only",
            "note": "Transaction history is an activity source. It is not the authoritative league financial ledger.",
        },
        "team_transaction_history": sorted(team_records, key=lambda item: item["transaction_count"], reverse=True),
        "manager_transaction_history": sorted(team_records, key=lambda item: item["transaction_count"], reverse=True),
        "player_movement_history": dict(player_movements),
        "asset_movements": asset_movements,
        "transaction_timeline": sorted(transaction_timeline, key=lambda row: str(row.get("timestamp") or "")),
        "records": sorted(records, key=lambda row: str(row.get("timestamp") or "")),
    }

    write_json(OUTPUT_JSON, history)
    _write_csv(asset_movements)
    return history


def _write_csv(rows: List[Dict[str, Any]]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "transaction_id",
        "timestamp",
        "season_week",
        "transaction_type",
        "asset_type",
        "asset_id",
        "asset_name",
        "movement",
        "team_id",
        "team_name",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> None:
    log_header("BUILD TRANSACTION HISTORY KNOWLEDGE")
    payload = build_transaction_history()
    log_section("Summary")
    log(f"Transactions: {payload['record_count']}")
    log(f"Asset movements: {payload['asset_movement_count']}")
    log(f"Teams with transaction history: {len(payload['team_transaction_history'])}")
    log(f"Output JSON: {OUTPUT_JSON}")
    log(f"Output CSV: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
