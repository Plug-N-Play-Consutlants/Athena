"""
Manager Behavior Intelligence

Layer: Intelligence

Responsibility:
    Consume transaction history knowledge and derive deterministic manager/team
    behaviour signals. This module does not parse provider payloads and does
    not treat transaction-derived fees as the official financial ledger.

Input:
    Output/transaction_history.json

Output:
    Output/manager_behavior.json
    Output/manager_behavior.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_json, read_optional_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR


INPUT_JSON = OUTPUT_DIR / "transaction_history.json"
TEAM_PROFILES_JSON = OUTPUT_DIR / "team_profiles.json"
OUTPUT_JSON = OUTPUT_DIR / "manager_behavior.json"
OUTPUT_CSV = OUTPUT_DIR / "manager_behavior.csv"

SCHEMA_VERSION = "0.3.2"


def _activity_band(count: int) -> str:
    if count >= 15:
        return "very_active"
    if count >= 8:
        return "active"
    if count >= 3:
        return "moderate"
    if count >= 1:
        return "low"
    return "inactive"


def _dominant(counter: Dict[str, int]) -> str:
    if not counter:
        return "unknown"
    return max(counter.items(), key=lambda item: item[1])[0]


def _trade_profile(types: Dict[str, int], total: int) -> Dict[str, Any]:
    trade_count = int(types.get("trade") or 0)
    if total <= 0:
        return {
            "classification": "insufficient_evidence",
            "confidence": 0.0,
            "evidence": ["No transaction history observed for this manager."],
        }
    if trade_count == 0:
        return {
            "classification": "insufficient_trade_evidence",
            "confidence": 0.3,
            "evidence": ["No trades were observed in the available transaction history."],
            "limitation": "This does not prove the manager will not trade; it only means no trade behavior is present in this data window.",
        }
    ratio = trade_count / total
    if trade_count >= 5 or ratio >= 0.4:
        return {
            "classification": "trade_active",
            "confidence": min(0.95, 0.55 + ratio),
            "evidence": [f"Observed {trade_count} trades across {total} transactions."],
        }
    return {
        "classification": "trade_selective",
        "confidence": min(0.85, 0.45 + ratio),
        "evidence": [f"Observed {trade_count} trades across {total} transactions."],
    }


def _transaction_style(types: Dict[str, int]) -> str:
    free_agent = int(types.get("free_agent_add") or 0) + int(types.get("free_agent_add_drop") or 0)
    waiver = int(types.get("waiver_claim") or 0) + int(types.get("waiver_claim_drop") or 0)
    drops = int(types.get("drop") or 0)
    trades = int(types.get("trade") or 0)
    if trades > max(free_agent, waiver, drops):
        return "trade_oriented"
    if waiver > max(free_agent, drops):
        return "waiver_oriented"
    if free_agent > 0:
        return "free_agent_oriented"
    if drops > 0:
        return "roster_churn"
    return "unknown"


def _confidence_from_volume(total: int) -> float:
    if total >= 15:
        return 0.9
    if total >= 8:
        return 0.75
    if total >= 3:
        return 0.55
    if total >= 1:
        return 0.35
    return 0.0


def _tendencies(total: int, types: Dict[str, int], added: int, dropped: int, observed_fee_total: float) -> List[Dict[str, Any]]:
    tendencies: List[Dict[str, Any]] = []
    free_agent_count = int(types.get("free_agent_add") or 0) + int(types.get("free_agent_add_drop") or 0)
    waiver_count = int(types.get("waiver_claim") or 0) + int(types.get("waiver_claim_drop") or 0)
    drop_count = int(types.get("drop") or 0)
    volume_confidence = _confidence_from_volume(total)

    if total >= 15:
        tendencies.append({
            "label": "aggressive_roster_manager",
            "confidence": volume_confidence,
            "evidence": [f"{total} transactions observed, placing this manager in the very_active band."],
        })
    elif total <= 2 and total > 0:
        tendencies.append({
            "label": "low_activity_manager",
            "confidence": volume_confidence,
            "evidence": [f"Only {total} transactions observed."],
        })

    if free_agent_count >= 7 or (total > 0 and free_agent_count / total >= 0.6 and free_agent_count >= 3):
        tendencies.append({
            "label": "free_agent_streamer",
            "confidence": min(0.9, 0.45 + (free_agent_count / max(total, 1))),
            "evidence": [f"{free_agent_count} free-agent-related transactions observed."],
        })

    if waiver_count >= 2 or (total > 0 and waiver_count / total >= 0.3 and waiver_count >= 1):
        tendencies.append({
            "label": "waiver_opportunist",
            "confidence": min(0.85, 0.45 + (waiver_count / max(total, 1))),
            "evidence": [f"{waiver_count} waiver-related transactions observed."],
        })

    if added + dropped >= 20:
        tendencies.append({
            "label": "high_roster_churn",
            "confidence": volume_confidence,
            "evidence": [f"{added + dropped} player movements observed ({added} added, {dropped} dropped)."],
        })

    if drop_count >= 5 and free_agent_count < drop_count:
        tendencies.append({
            "label": "roster_pruner",
            "confidence": volume_confidence,
            "evidence": [f"{drop_count} drop transactions observed."],
        })

    if observed_fee_total >= 100:
        tendencies.append({
            "label": "high_observed_fee_activity",
            "confidence": 0.6,
            "evidence": [f"${observed_fee_total:.2f} observed in transaction-history fee fields."],
            "limitation": "This is not the official league finance balance.",
        })

    return tendencies


def build_manager_behavior() -> Dict[str, Any]:
    history = read_json(INPUT_JSON)
    manager_history = history.get("manager_transaction_history", []) if isinstance(history, dict) else []

    records: List[Dict[str, Any]] = []
    for manager in manager_history:
        if not isinstance(manager, dict):
            continue

        total = int(manager.get("transaction_count") or 0)
        transaction_types = manager.get("transaction_types") or {}
        asset_types = manager.get("asset_types") or {}
        asset_movements = manager.get("asset_movements") or {}
        observed_fee_total = float(manager.get("observed_transaction_fee_total") or manager.get("fee_total") or 0)
        added_count = int(asset_movements.get("added") or 0)
        dropped_count = int(asset_movements.get("dropped") or 0)
        player_count = int(asset_types.get("player") or 0)
        waiver_count = int(transaction_types.get("waiver_claim") or 0) + int(transaction_types.get("waiver_claim_drop") or 0)
        free_agent_count = int(transaction_types.get("free_agent_add") or 0) + int(transaction_types.get("free_agent_add_drop") or 0)
        trade_count = int(transaction_types.get("trade") or 0)
        trade_profile = _trade_profile(transaction_types, total)

        observed_facts = {
            "transaction_count": total,
            "transaction_types": transaction_types,
            "asset_types": asset_types,
            "asset_movements": asset_movements,
            "player_movement_volume": player_count,
            "added_player_count": added_count,
            "dropped_player_count": dropped_count,
            "trade_count": trade_count,
            "waiver_claim_count": waiver_count,
            "free_agent_activity_count": free_agent_count,
            "observed_transaction_fee_total": round(observed_fee_total, 2),
            "financial_provenance": "observed_from_transaction_history_not_official_ledger",
        }

        records.append(
            {
                "manager_id": manager.get("team_id", ""),
                "manager_name": manager.get("team_name", ""),
                "team_id": manager.get("team_id", ""),
                "team_name": manager.get("team_name", ""),
                "observed_facts": observed_facts,
                "inferred_profile": {
                    "activity_band": _activity_band(total),
                    "dominant_transaction_type": _dominant(transaction_types),
                    "transaction_style": _transaction_style(transaction_types),
                    "trade_profile": trade_profile,
                    "tendencies": _tendencies(total, transaction_types, added_count, dropped_count, observed_fee_total),
                    "confidence": _confidence_from_volume(total),
                },
                "limitations": [
                    "Manager behavior is inferred only from available transaction history.",
                    "Official financial balances must come from the Fantrax finance page, not transaction history.",
                ],
                # Flattened summary fields retained for CSV/readability and downstream aggregation.
                "transaction_count": total,
                "activity_band": _activity_band(total),
                "dominant_transaction_type": _dominant(transaction_types),
                "transaction_style": _transaction_style(transaction_types),
                "trade_profile_classification": trade_profile.get("classification"),
                "observed_transaction_fee_total": round(observed_fee_total, 2),
                "signals": observed_facts,
            }
        )

    # Include teams with no observed transaction activity so league coverage is
    # complete. These are "inactive in this observed data window", not missing
    # managers and not proof of owner inactivity.
    team_profiles = read_optional_json(TEAM_PROFILES_JSON) or []
    seen_team_ids = {str(row.get("team_id") or row.get("manager_id") or "") for row in records}
    if isinstance(team_profiles, list):
        for team in team_profiles:
            if not isinstance(team, dict):
                continue
            team_id = str(team.get("team_id") or "")
            if not team_id or team_id in seen_team_ids:
                continue
            observed_facts = {
                "transaction_count": 0,
                "transaction_types": {},
                "asset_types": {},
                "asset_movements": {},
                "player_movement_volume": 0,
                "added_player_count": 0,
                "dropped_player_count": 0,
                "trade_count": 0,
                "waiver_claim_count": 0,
                "free_agent_activity_count": 0,
                "observed_transaction_fee_total": 0.0,
                "financial_provenance": "no_observed_transaction_history_for_team",
            }
            records.append({
                "manager_id": team_id,
                "manager_name": team.get("team_name", ""),
                "team_id": team_id,
                "team_name": team.get("team_name", ""),
                "observed_facts": observed_facts,
                "inferred_profile": {
                    "activity_band": "inactive_observed_window",
                    "dominant_transaction_type": "none_observed",
                    "transaction_style": "none_observed",
                    "trade_profile": _trade_profile({}, 0),
                    "tendencies": [],
                    "confidence": 0.2,
                },
                "limitations": [
                    "No transactions were observed for this team in the synced transaction-history window.",
                    "This does not prove the manager is inactive; it only means no activity was present in the available data window.",
                ],
                "transaction_count": 0,
                "activity_band": "inactive_observed_window",
                "dominant_transaction_type": "none_observed",
                "transaction_style": "none_observed",
                "trade_profile_classification": "insufficient_evidence",
                "observed_transaction_fee_total": 0.0,
                "signals": observed_facts,
            })
            seen_team_ids.add(team_id)

    payload = {
        "domain": "manager_behavior",
        "schema_version": "0.3.2",
        "source": "transaction_history_plus_team_profiles",
        "manager_count": len(records),
        "financial_provenance": {
            "official_finance_source": "Fantrax finance page under team menu",
            "transaction_history_fee_fields": "observed only",
        },
        "records": sorted(records, key=lambda row: row["transaction_count"], reverse=True),
    }
    write_json(OUTPUT_JSON, payload)
    _write_csv(payload["records"])
    return payload


def _write_csv(rows: List[Dict[str, Any]]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "manager_id",
        "manager_name",
        "transaction_count",
        "activity_band",
        "dominant_transaction_type",
        "transaction_style",
        "trade_profile_classification",
        "observed_transaction_fee_total",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> None:
    log_header("BUILD MANAGER BEHAVIOR INTELLIGENCE")
    payload = build_manager_behavior()
    log_section("Summary")
    log(f"Managers analyzed: {payload['manager_count']}")
    log(f"Output JSON: {OUTPUT_JSON}")
    log(f"Output CSV: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
