"""
Fantrax Transaction Master Builder

Layer: Providers/Fantrax/build

Responsibility:
    Normalize raw Fantrax transaction payloads into canonical transaction
    records. Provider-specific table rows belong here, not in Knowledge.

Input:
    Raw/transactions.json

Output:
    Output/transaction_master.json
    Output/transaction_master.csv

Notes:
    Fantrax returns transaction table rows, not already-normalized events.
    Related rows share txSetId. A claim/drop pair, for example, should become
    one canonical transaction with multiple asset movements.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import RAW_DIR, OUTPUT_DIR


INPUT_JSON = RAW_DIR / "transactions.json"
OUTPUT_JSON = OUTPUT_DIR / "transaction_master.json"
OUTPUT_CSV = OUTPUT_DIR / "transaction_master.csv"
PROVIDER = "fantrax"
SCHEMA_VERSION = "0.3.0"

CSV_FIELDS = [
    "transaction_id",
    "timestamp",
    "transaction_type",
    "status",
    "team_name",
    "team_id",
    "asset_count",
    "fee_total",
    "provider",
    "provider_transaction_set_id",
]


POSITION_MAP = {
    "202": "D",
    "203": "LW",
    "204": "RW",
    "206": "C",
}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _records(payload: Any) -> List[Dict[str, Any]]:
    """Return raw Fantrax transaction rows from known payload shapes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    table = payload.get("table")
    if isinstance(table, dict):
        rows = table.get("rows")
        if isinstance(rows, list):
            return [item for item in rows if isinstance(item, dict)]

    for key in ("transactions", "transactionHistory", "transaction_history", "records", "items", "rows", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _records(value)
            if nested:
                return nested

    return []


def _cell(row: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    cells = row.get("cells")
    if not isinstance(cells, list):
        return None
    for item in cells:
        if isinstance(item, dict) and item.get("key") == key:
            return item
    return None


def _cell_content(row: Dict[str, Any], key: str) -> str:
    cell = _cell(row, key)
    return _safe_str(cell.get("content")) if isinstance(cell, dict) else ""


def _team_from_row(row: Dict[str, Any]) -> Dict[str, str]:
    """Extract fantasy team/manager identity from the Fantrax row cells."""
    cell = _cell(row, "team")
    if isinstance(cell, dict):
        return {
            "team_id": _safe_str(cell.get("teamId")),
            "team_name": _safe_str(cell.get("content")),
        }

    for key in ("team", "fantasy_team", "owner", "claimingTeam", "claiming_team"):
        value = row.get(key)
        if isinstance(value, dict):
            return {
                "team_id": _safe_str(value.get("teamId") or value.get("id") or value.get("team_id")),
                "team_name": _safe_str(value.get("teamName") or value.get("name") or value.get("team_name")),
            }

    return {"team_id": "", "team_name": ""}


def _date_from_row(row: Dict[str, Any]) -> str:
    for key in ("timestamp", "date", "createdDate", "created_date", "transactionDate"):
        value = _safe_str(row.get(key))
        if value:
            return value
    return _cell_content(row, "date")


def _week_from_row(row: Dict[str, Any]) -> str:
    for key in ("week", "period"):
        value = _safe_str(row.get(key))
        if value:
            return value
    return _cell_content(row, "week")


def _normalize_timestamp(value: Any) -> str:
    """Preserve Fantrax display dates while normalizing epoch values if present."""
    text = _safe_str(value)
    if not text:
        return ""

    if text.isdigit():
        number = int(text)
        if number > 10_000_000_000:
            number = number / 1000
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return text

    return text


def _status_from_rows(rows: Iterable[Dict[str, Any]]) -> str:
    statuses = Counter()
    for row in rows:
        value = _safe_str(row.get("resultCode") or row.get("status") or row.get("state")).lower()
        if value:
            statuses[value] += 1
    if not statuses:
        return "unknown"
    if len(statuses) == 1:
        return next(iter(statuses))
    if "executed" in statuses:
        return "executed"
    return statuses.most_common(1)[0][0]


def _movement_from_code(row: Dict[str, Any]) -> str:
    code = _safe_str(row.get("transactionCode")).upper()
    if code == "CLAIM":
        return "added"
    if code == "DROP":
        return "dropped"
    if code == "TRADE":
        return "moved"
    return "involved"


def _asset_from_scorer(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    scorer = row.get("scorer")
    if not isinstance(scorer, dict):
        return None

    scorer_id = _safe_str(scorer.get("scorerId") or scorer.get("playerId") or scorer.get("id"))
    name = _safe_str(scorer.get("name") or scorer.get("shortName"))
    if not (scorer_id or name):
        return None

    position_ids = scorer.get("posIds") if isinstance(scorer.get("posIds"), list) else []
    position_ids_no_flex = scorer.get("posIdsNoFlex") if isinstance(scorer.get("posIdsNoFlex"), list) else []
    positions = [POSITION_MAP.get(str(item), str(item)) for item in position_ids]
    positions_no_flex = [POSITION_MAP.get(str(item), str(item)) for item in position_ids_no_flex]

    return {
        "asset_type": "player",
        "asset_id": scorer_id,
        "asset_name": name,
        "movement": _movement_from_code(row),
        "provider_reference": {
            "provider": PROVIDER,
            "scorer_id": scorer_id,
            "url_name": _safe_str(scorer.get("urlName")),
        },
        "player": {
            "name": name,
            "short_name": _safe_str(scorer.get("shortName")),
            "fantrax_scorer_id": scorer_id,
            "position": _safe_str(scorer.get("posShortNames")),
            "positions": positions,
            "positions_no_flex": positions_no_flex,
            "default_position_id": _safe_str(scorer.get("defaultPosId")),
            "nhl_team_id": _safe_str(scorer.get("teamId")),
            "nhl_team_name": _safe_str(scorer.get("teamName")),
            "nhl_team_abbreviation": _safe_str(scorer.get("teamShortName")),
            "rookie": bool(scorer.get("rookie")),
            "minors_eligible": bool(scorer.get("minorsEligible")),
            "icons": scorer.get("icons") if isinstance(scorer.get("icons"), list) else [],
        },
        "provider_metadata": scorer,
    }


def _fees_from_row(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    fees: List[Dict[str, Any]] = []
    for key in ("fees", "fee"):
        cell = _cell(row, key)
        if not isinstance(cell, dict):
            continue

        props = cell.get("props")
        if isinstance(props, dict) and isinstance(props.get("feeData"), list):
            for item in props["feeData"]:
                if not isinstance(item, dict):
                    continue
                amount = _safe_float(item.get("fee"))
                fees.append(
                    {
                        "team_id": _safe_str(item.get("teamId")),
                        "team_name": _safe_str(item.get("shortName")),
                        "amount": amount,
                        "currency": "league_fee",
                    }
                )
        elif cell.get("content") not in (None, ""):
            fees.append(
                {
                    "team_id": "",
                    "team_name": "",
                    "amount": _safe_float(cell.get("content")),
                    "currency": "league_fee",
                }
            )
    return fees


def _group_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group related Fantrax table rows by txSetId and inherit row-spanned cells."""
    groups: List[Dict[str, Any]] = []
    current_by_id: Dict[str, Dict[str, Any]] = {}
    active_context = {"team_id": "", "team_name": "", "date": "", "week": "", "fees": []}

    for index, row in enumerate(rows):
        team = _team_from_row(row)
        if team.get("team_id") or team.get("team_name"):
            active_context["team_id"] = team.get("team_id", "")
            active_context["team_name"] = team.get("team_name", "")

        date_text = _date_from_row(row)
        if date_text:
            active_context["date"] = date_text

        week = _week_from_row(row)
        if week:
            active_context["week"] = week

        row_fees = _fees_from_row(row)
        if row_fees:
            active_context["fees"] = row_fees

        tx_set_id = _safe_str(row.get("txSetId")) or f"ungrouped_{index + 1}"
        if tx_set_id not in current_by_id:
            group = {
                "tx_set_id": tx_set_id,
                "rows": [],
                "context": dict(active_context),
            }
            current_by_id[tx_set_id] = group
            groups.append(group)

        current_by_id[tx_set_id]["rows"].append(row)

    return groups


def _transaction_type(codes: Counter, claim_types: Counter) -> str:
    has_claim = codes.get("CLAIM", 0) > 0
    has_drop = codes.get("DROP", 0) > 0
    has_trade = codes.get("TRADE", 0) > 0

    if has_trade:
        return "trade"
    if has_claim and has_drop:
        if claim_types.get("WW", 0) > 0:
            return "waiver_claim_drop"
        if claim_types.get("FA", 0) > 0:
            return "free_agent_add_drop"
        return "claim_drop"
    if has_claim:
        if claim_types.get("WW", 0) > 0:
            return "waiver_claim"
        if claim_types.get("FA", 0) > 0:
            return "free_agent_add"
        return "claim"
    if has_drop:
        return "drop"
    return "unknown"


def _summary(transaction_type: str, assets: List[Dict[str, Any]], team_name: str) -> str:
    added = [a.get("asset_name") for a in assets if a.get("movement") == "added"]
    dropped = [a.get("asset_name") for a in assets if a.get("movement") == "dropped"]
    prefix = team_name or "Unknown team"

    if added and dropped:
        return f"{prefix} added {', '.join(added)} and dropped {', '.join(dropped)}"
    if added:
        return f"{prefix} added {', '.join(added)}"
    if dropped:
        return f"{prefix} dropped {', '.join(dropped)}"
    return f"{prefix} completed {transaction_type}"


def _normalize_group(group: Dict[str, Any], index: int) -> Dict[str, Any]:
    rows = [row for row in group.get("rows", []) if isinstance(row, dict)]
    context = group.get("context") if isinstance(group.get("context"), dict) else {}

    tx_set_id = _safe_str(group.get("tx_set_id")) or f"fantrax_transaction_{index + 1}"
    team_id = _safe_str(context.get("team_id"))
    team_name = _safe_str(context.get("team_name"))
    timestamp = _normalize_timestamp(context.get("date"))
    week = _safe_str(context.get("week"))

    assets: List[Dict[str, Any]] = []
    for row in rows:
        asset = _asset_from_scorer(row)
        if asset:
            asset["movement_context"] = {
                "team_id": team_id,
                "team_name": team_name,
                "transaction_code": _safe_str(row.get("transactionCode")),
                "claim_type": _safe_str(row.get("claimType")),
            }
            assets.append(asset)

    codes = Counter(_safe_str(row.get("transactionCode")).upper() for row in rows if _safe_str(row.get("transactionCode")))
    claim_types = Counter(_safe_str(row.get("claimType")).upper() for row in rows if _safe_str(row.get("claimType")))
    transaction_type = _transaction_type(codes, claim_types)
    fees = context.get("fees") if isinstance(context.get("fees"), list) else []
    fee_total = round(sum(_safe_float(fee.get("amount")) for fee in fees if isinstance(fee, dict)), 2)

    participant = {
        "participant_type": "fantasy_team",
        "participant_id": team_id,
        "participant_name": team_name,
        "role": "actor",
        "provider_reference": {"provider": PROVIDER, "team_id": team_id},
    }

    return {
        "transaction_id": f"fantrax:{tx_set_id}",
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp,
        "season_week": week,
        "transaction_type": transaction_type,
        "status": _status_from_rows(rows),
        "summary": _summary(transaction_type, assets, team_name),
        "participants": [participant] if team_id or team_name else [],
        "assets": assets,
        "asset_movements": [
            {
                "asset_type": asset.get("asset_type"),
                "asset_id": asset.get("asset_id"),
                "asset_name": asset.get("asset_name"),
                "movement": asset.get("movement"),
                "to_participant_id": team_id if asset.get("movement") == "added" else "",
                "from_participant_id": team_id if asset.get("movement") == "dropped" else "",
            }
            for asset in assets
        ],
        "fees": fees,
        "fee_total": fee_total,
        "provider": PROVIDER,
        "provider_reference": {
            "provider": PROVIDER,
            "transaction_set_id": tx_set_id,
            "row_count": len(rows),
            "transaction_codes": dict(codes),
            "claim_types": dict(claim_types),
        },
        "provider_metadata": {
            "rows": rows,
        },
    }


def build_transaction_master() -> Dict[str, Any]:
    raw_payload = read_json(INPUT_JSON)
    rows = _records(raw_payload)
    groups = _group_rows(rows)
    records = [_normalize_group(group, index) for index, group in enumerate(groups)]

    type_distribution = Counter(row.get("transaction_type") or "unknown" for row in records)
    asset_distribution = Counter()
    for row in records:
        for asset in row.get("assets") or []:
            if isinstance(asset, dict):
                asset_distribution[asset.get("asset_type") or "unknown"] += 1

    payload = {
        "domain": "transactions",
        "schema_version": SCHEMA_VERSION,
        "source": "fantrax_transaction_history",
        "provider": PROVIDER,
        "raw_row_count": len(rows),
        "record_count": len(records),
        "transaction_type_distribution": dict(type_distribution),
        "asset_type_distribution": dict(asset_distribution),
        "records": records,
    }

    write_json(OUTPUT_JSON, payload)
    _write_csv(records)
    return payload


def _write_csv(records: List[Dict[str, Any]]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in records:
            participant = (row.get("participants") or [{}])[0]
            writer.writerow(
                {
                    "transaction_id": row.get("transaction_id", ""),
                    "timestamp": row.get("timestamp", ""),
                    "transaction_type": row.get("transaction_type", ""),
                    "status": row.get("status", ""),
                    "team_name": participant.get("participant_name", "") if isinstance(participant, dict) else "",
                    "team_id": participant.get("participant_id", "") if isinstance(participant, dict) else "",
                    "asset_count": len(row.get("assets") or []),
                    "fee_total": row.get("fee_total", 0),
                    "provider": row.get("provider", ""),
                    "provider_transaction_set_id": (row.get("provider_reference") or {}).get("transaction_set_id", ""),
                }
            )


def main() -> None:
    log_header("BUILD TRANSACTION MASTER")
    payload = build_transaction_master()
    log_section("Summary")
    log(f"Raw transaction rows: {payload['raw_row_count']}")
    log(f"Canonical transactions: {payload['record_count']}")
    log(f"Types: {payload['transaction_type_distribution']}")
    log(f"Output JSON: {OUTPUT_JSON}")
    log(f"Output CSV: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
