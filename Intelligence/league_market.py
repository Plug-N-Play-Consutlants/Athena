"""
League Market Intelligence

Layer: Intelligence

Responsibility:
    Aggregate deterministic manager behavior and transaction history into
    league-level market signals. This module does not parse provider payloads
    and does not treat transaction-derived fees as official finance data.

Inputs:
    Output/transaction_history.json
    Output/manager_behavior.json

Output:
    Output/league_market.json
    Output/league_market.csv
"""

from __future__ import annotations

import csv
from collections import Counter
from typing import Any, Dict, List

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR


TRANSACTION_HISTORY_JSON = OUTPUT_DIR / "transaction_history.json"
MANAGER_BEHAVIOR_JSON = OUTPUT_DIR / "manager_behavior.json"
OUTPUT_JSON = OUTPUT_DIR / "league_market.json"
OUTPUT_CSV = OUTPUT_DIR / "league_market.csv"

SCHEMA_VERSION = "0.3.1"


def _manager_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [row for row in payload["records"] if isinstance(row, dict)]
    return []


def _classification_from_score(score: int) -> str:
    if score >= 85:
        return "very_liquid"
    if score >= 65:
        return "liquid"
    if score >= 40:
        return "moderate"
    if score > 0:
        return "thin"
    return "inactive"


def _liquidity_profile(
    transaction_count: int,
    manager_count: int,
    type_distribution: Dict[str, int],
    week_distribution: Dict[str, int],
    activity_counts: Counter,
    trade_profile_counts: Counter,
) -> Dict[str, Any]:
    if manager_count <= 0:
        return {
            "classification": "unknown",
            "score": 0,
            "confidence": 0.0,
            "drivers": [],
            "limitations": ["No manager records available."],
        }

    per_manager = transaction_count / manager_count
    active_manager_count = int(activity_counts.get("very_active") or 0) + int(activity_counts.get("active") or 0)
    active_manager_ratio = active_manager_count / manager_count
    active_week_count = len([week for week, count in week_distribution.items() if week != "unknown" and int(count or 0) > 0])
    free_agent_count = int(type_distribution.get("free_agent_add") or 0) + int(type_distribution.get("free_agent_add_drop") or 0)
    waiver_count = int(type_distribution.get("waiver_claim") or 0) + int(type_distribution.get("waiver_claim_drop") or 0)
    trade_count = int(type_distribution.get("trade") or 0)

    score = 0
    score += min(35, int(per_manager * 4))
    score += min(25, int(active_manager_ratio * 25))
    score += min(20, int(active_week_count * 1.2))
    if free_agent_count > 0:
        score += min(10, int(free_agent_count / max(transaction_count, 1) * 10))
    if waiver_count > 0:
        score += 5
    if trade_count > 0:
        score += 5
    score = max(0, min(100, score))

    drivers: List[str] = []
    if per_manager >= 6:
        drivers.append(f"{transaction_count} transactions across {manager_count} managers ({per_manager:.1f} per manager).")
    else:
        drivers.append(f"{transaction_count} transactions across {manager_count} managers ({per_manager:.1f} per manager).")
    if active_manager_count:
        drivers.append(f"{active_manager_count} managers are active or very active.")
    if active_week_count:
        drivers.append(f"Transactions appear in {active_week_count} season weeks.")
    if free_agent_count:
        drivers.append(f"{free_agent_count} free-agent-related transactions observed.")
    if waiver_count:
        drivers.append(f"{waiver_count} waiver-related transactions observed.")

    limitations: List[str] = []
    if trade_count == 0:
        limitations.append("No trades were observed in the available transaction history, so trade liquidity is unknown rather than inactive.")
    if int(trade_profile_counts.get("insufficient_trade_evidence") or 0) == manager_count:
        limitations.append("Every manager has insufficient observed trade evidence in this dataset.")
    limitations.append("Official money balances must come from the Fantrax finance page, not transaction-derived fee fields.")

    confidence = 0.5
    if transaction_count >= 50:
        confidence += 0.2
    if manager_count >= 10:
        confidence += 0.1
    if active_week_count >= 10:
        confidence += 0.1
    if trade_count == 0:
        confidence -= 0.1
    confidence = round(max(0.0, min(0.95, confidence)), 2)

    return {
        "classification": _classification_from_score(score),
        "score": score,
        "confidence": confidence,
        "drivers": drivers,
        "limitations": limitations,
    }


def build_league_market() -> Dict[str, Any]:
    history = read_json(TRANSACTION_HISTORY_JSON)
    behavior = read_json(MANAGER_BEHAVIOR_JSON)

    transaction_count = int(history.get("record_count") or 0) if isinstance(history, dict) else 0
    asset_movement_count = int(history.get("asset_movement_count") or 0) if isinstance(history, dict) else 0
    manager_records = _manager_records(behavior)
    manager_count = len(manager_records)

    trade_profile_counts = Counter(row.get("trade_profile_classification") or "unknown" for row in manager_records)
    activity_counts = Counter(row.get("activity_band") or "unknown" for row in manager_records)
    style_counts = Counter(row.get("transaction_style") or "unknown" for row in manager_records)
    type_distribution = history.get("transaction_type_distribution", {}) if isinstance(history, dict) else {}
    movement_distribution = history.get("asset_movement_distribution", {}) if isinstance(history, dict) else {}
    week_distribution = history.get("transaction_week_distribution", {}) if isinstance(history, dict) else {}

    observed_fee_total = round(sum(float(row.get("observed_transaction_fee_total") or 0) for row in manager_records), 2)
    most_active = manager_records[:5]
    liquidity = _liquidity_profile(
        transaction_count,
        manager_count,
        type_distribution,
        week_distribution,
        activity_counts,
        trade_profile_counts,
    )

    payload = {
        "domain": "league_market",
        "schema_version": SCHEMA_VERSION,
        "source": ["transaction_history", "manager_behavior"],
        "transaction_count": transaction_count,
        "asset_movement_count": asset_movement_count,
        "manager_count": manager_count,
        "market_liquidity": liquidity,
        "transaction_type_distribution": type_distribution,
        "asset_movement_distribution": movement_distribution,
        "transaction_week_distribution": week_distribution,
        "manager_activity_distribution": dict(activity_counts),
        "manager_style_distribution": dict(style_counts),
        "trade_profile_distribution": dict(trade_profile_counts),
        "observed_transaction_fee_total": observed_fee_total,
        "financial_provenance": {
            "official_finance_source": "Fantrax finance page under team menu",
            "transaction_history_fee_fields": "observed only",
            "note": "Do not use observed_transaction_fee_total as the league financial balance.",
        },
        "most_active_managers": [
            {
                "manager_id": row.get("manager_id", ""),
                "manager_name": row.get("manager_name", ""),
                "transaction_count": row.get("transaction_count", 0),
                "activity_band": row.get("activity_band", ""),
                "transaction_style": row.get("transaction_style", ""),
                "trade_profile_classification": row.get("trade_profile_classification", ""),
                "observed_transaction_fee_total": row.get("observed_transaction_fee_total", 0),
            }
            for row in most_active
        ],
        "signals": {
            "trade_active_manager_count": int(trade_profile_counts.get("trade_active") or 0),
            "trade_selective_manager_count": int(trade_profile_counts.get("trade_selective") or 0),
            "insufficient_trade_evidence_manager_count": int(trade_profile_counts.get("insufficient_trade_evidence") or 0),
            "draft_pick_activity_observed": any(
                isinstance(row, dict) and bool((row.get("observed_facts") or {}).get("uses_draft_picks"))
                for row in manager_records
            ),
            "waiver_activity_observed": any(
                isinstance(row, dict) and int((row.get("observed_facts") or {}).get("waiver_claim_count") or 0) > 0
                for row in manager_records
            ),
            "free_agent_activity_observed": any(
                isinstance(row, dict) and int((row.get("observed_facts") or {}).get("free_agent_activity_count") or 0) > 0
                for row in manager_records
            ),
        },
    }
    write_json(OUTPUT_JSON, payload)
    _write_csv(payload)
    return payload


def _write_csv(payload: Dict[str, Any]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["metric", "value"]
    liquidity = payload.get("market_liquidity") or {}
    rows = [
        {"metric": "transaction_count", "value": payload.get("transaction_count", 0)},
        {"metric": "asset_movement_count", "value": payload.get("asset_movement_count", 0)},
        {"metric": "manager_count", "value": payload.get("manager_count", 0)},
        {"metric": "market_liquidity_classification", "value": liquidity.get("classification", "")},
        {"metric": "market_liquidity_score", "value": liquidity.get("score", 0)},
        {"metric": "market_liquidity_confidence", "value": liquidity.get("confidence", 0)},
        {"metric": "observed_transaction_fee_total", "value": payload.get("observed_transaction_fee_total", 0)},
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    log_header("BUILD LEAGUE MARKET INTELLIGENCE")
    payload = build_league_market()
    liquidity = payload["market_liquidity"]
    log_section("Summary")
    log(f"Transactions: {payload['transaction_count']}")
    log(f"Asset movements: {payload['asset_movement_count']}")
    log(f"Managers: {payload['manager_count']}")
    log(f"Market liquidity: {liquidity['classification']} ({liquidity['score']})")
    log(f"Output JSON: {OUTPUT_JSON}")
    log(f"Output CSV: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
