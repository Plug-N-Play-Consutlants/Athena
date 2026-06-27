"""Athena capability assessment.

Capability assessment is provider-neutral glue for Alpha UX. It turns missing
optional provider data into an explicit operating state instead of an exception.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from Core.json_utils import read_optional_json
from Core.project_paths import OUTPUT_DIR, RAW_DIR

AVAILABLE = "available"
PARTIAL = "partial"
SESSION_REQUIRED = "session_required"
NOT_SUPPORTED = "not_supported"
MISSING = "missing"
FAILED = "failed"


def _page_error_code(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    page_error = payload.get("pageError")
    if isinstance(page_error, dict):
        return str(page_error.get("code") or "")
    responses = payload.get("responses")
    if isinstance(responses, list):
        for response in responses:
            if isinstance(response, dict):
                nested = response.get("pageError")
                if isinstance(nested, dict):
                    return str(nested.get("code") or "")
    return ""


def _has_auth_error(payload: Any) -> bool:
    return _page_error_code(payload) in {"WARNING_NOT_LOGGED_IN", "ERROR_NOT_LOGGED_IN", "NOT_LOGGED_IN"}


def _count_records(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in (
            "record_count",
            "manager_count",
            "transaction_count",
            "asset_movement_count",
            "raw_row_count",
            "team_count",
        ):
            value = payload.get(key)
            if isinstance(value, int):
                return value
        for key in (
            "records",
            "transactions",
            "asset_movements",
            "team_transaction_history",
            "players",
            "playerInfo",
            "teams",
            "teamInfo",
            "rosters",
            "rows",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
            if isinstance(value, dict):
                return len(value)
        table = payload.get("table")
        if isinstance(table, dict) and isinstance(table.get("rows"), list):
            return len(table["rows"])
    if isinstance(payload, list):
        return len(payload)
    return 0


def _capability(
    key: str,
    label: str,
    status: str,
    *,
    layer: str,
    required: bool = False,
    reason: str = "",
    impact: str = "",
    evidence: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "available": status in {AVAILABLE, PARTIAL},
        "layer": layer,
        "required": required,
        "reason": reason,
        "impact": impact,
        "evidence": evidence or {},
    }


def _exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def assess_capabilities(provider: str = "Fantrax") -> Dict[str, Any]:
    """Assess current provider/data capabilities from available Raw/Output files."""
    provider_label = str(provider or "Fantrax")
    league = read_optional_json(RAW_DIR / "league_info.json")
    player_pool = read_optional_json(RAW_DIR / "fantrax_player_pool.json")
    transactions = read_optional_json(RAW_DIR / "transactions.json")
    player_master = read_optional_json(OUTPUT_DIR / "player_master.json")
    team_profiles = read_optional_json(OUTPUT_DIR / "team_profiles.json")
    transaction_master = read_optional_json(OUTPUT_DIR / "transaction_master.json")
    transaction_history = read_optional_json(OUTPUT_DIR / "transaction_history.json")
    manager_behavior = read_optional_json(OUTPUT_DIR / "manager_behavior.json")
    league_market = read_optional_json(OUTPUT_DIR / "league_market.json")

    league_teams = 0
    if isinstance(league, dict):
        if isinstance(league.get("teams"), list):
            league_teams = len(league["teams"])
        elif isinstance(league.get("teamInfo"), dict):
            # Fantrax league_info.json exposes teams under teamInfo keyed by team id.
            # Treat this as authoritative league-team evidence for capability assessment.
            league_teams = len(league["teamInfo"])
        elif isinstance(league.get("league"), dict) and isinstance(league["league"].get("teams"), list):
            league_teams = len(league["league"]["teams"])
        elif isinstance(league.get("league"), dict) and isinstance(league["league"].get("teamInfo"), dict):
            league_teams = len(league["league"]["teamInfo"])
        elif isinstance(league.get("team_count"), int):
            league_teams = int(league["team_count"])

    player_pool_count = _count_records(player_pool)
    player_master_count = _count_records(player_master)
    team_profile_count = _count_records(team_profiles)
    transaction_rows = _count_records(transactions)
    transaction_records = _count_records(transaction_master)
    transaction_history_records = _count_records(transaction_history)
    manager_count = _count_records(manager_behavior)
    market_records = _count_records(league_market)
    tx_page_error = _page_error_code(transactions)

    capabilities: List[Dict[str, Any]] = []

    capabilities.append(_capability(
        "league_info", "League metadata", AVAILABLE if _exists(RAW_DIR / "league_info.json") and league_teams > 0 else MISSING,
        layer="Fetch", required=True,
        reason=f"League teams detected: {league_teams}." if league_teams > 0 else "league_info.json is missing or contains no teams.",
        impact="Required for all fantasy-league analysis.", evidence={"team_count": league_teams},
    ))
    capabilities.append(_capability(
        "player_pool", "Player pool", AVAILABLE if _exists(RAW_DIR / "fantrax_player_pool.json") and player_pool_count > 0 else MISSING,
        layer="Fetch", required=True,
        reason=f"Player pool records detected: {player_pool_count}." if player_pool_count > 0 else "fantrax_player_pool.json is missing or empty.",
        impact="Required for player and roster intelligence.", evidence={"record_count": player_pool_count},
    ))
    capabilities.append(_capability(
        "team_profiles", "Team profiles", AVAILABLE if team_profile_count > 0 else PARTIAL if league_teams > 0 else MISSING,
        layer="Knowledge", required=False,
        reason=f"Team profile records detected: {team_profile_count}." if team_profile_count > 0 else "Team profile output is not built yet, but league teams exist." if league_teams > 0 else "No league teams available.",
        impact="Team analysis is stronger when team profiles are built.", evidence={"record_count": team_profile_count},
    ))
    capabilities.append(_capability(
        "player_master", "Player master", AVAILABLE if player_master_count > 0 else PARTIAL if player_pool_count > 0 else MISSING,
        layer="Build", required=False,
        reason=f"Player master records detected: {player_master_count}." if player_master_count > 0 else "Player pool exists but player master output is not built yet." if player_pool_count > 0 else "No player pool available.",
        impact="Player lookup uses the best available player evidence.", evidence={"record_count": player_master_count},
    ))

    if _has_auth_error(transactions):
        tx_status = SESSION_REQUIRED
        tx_reason = "Fantrax transactions require an authenticated browser Cookie header."
    elif not _exists(RAW_DIR / "transactions.json"):
        tx_status = MISSING
        tx_reason = "transactions.json is missing."
    elif transaction_rows <= 0:
        tx_status = PARTIAL
        tx_reason = "transactions.json exists but has no transaction rows."
    else:
        tx_status = AVAILABLE
        tx_reason = f"Transaction rows detected: {transaction_rows}."

    capabilities.append(_capability(
        "transactions", "Transactions", tx_status, layer="Fetch", required=False,
        reason=tx_reason,
        impact="Manager activity and trade-market intelligence are limited when unavailable.",
        evidence={"transaction_rows": transaction_rows, "page_error": tx_page_error},
    ))

    tx_available = tx_status in {AVAILABLE, PARTIAL} and transaction_rows > 0
    capabilities.append(_capability(
        "transaction_history", "Transaction history", AVAILABLE if transaction_history_records > 0 else SESSION_REQUIRED if tx_status == SESSION_REQUIRED else MISSING,
        layer="Knowledge", required=False,
        reason=f"Transaction history records detected: {transaction_history_records}." if transaction_history_records > 0 else "Transaction history depends on transaction capability.",
        impact="Required for active-manager analysis.", evidence={"record_count": transaction_history_records},
    ))
    capabilities.append(_capability(
        "manager_activity", "Manager activity", AVAILABLE if manager_count > 0 else SESSION_REQUIRED if tx_status == SESSION_REQUIRED else MISSING,
        layer="Intelligence", required=False,
        reason=f"Managers analyzed: {manager_count}." if manager_count > 0 else "Manager behavior depends on transaction history.",
        impact="Most-active-manager questions are limited when unavailable.", evidence={"manager_count": manager_count},
    ))
    capabilities.append(_capability(
        "trade_market", "Trade market", AVAILABLE if market_records > 0 and transaction_records > 0 else SESSION_REQUIRED if tx_status == SESSION_REQUIRED else MISSING,
        layer="Intelligence", required=False,
        reason="League market output is available." if market_records > 0 and transaction_records > 0 else "Trade-market intelligence depends on transaction evidence.",
        impact="Trade-market questions are limited when unavailable.", evidence={"market_records": market_records, "canonical_transactions": transaction_records},
    ))

    capabilities.append(_capability(
        "live_scores", "Live scores", NOT_SUPPORTED, layer="Fetch", required=False,
        reason="Live scoring is not implemented in Scout Alpha.",
        impact="No effect on static league analysis.", evidence={},
    ))

    by_key = {item["key"]: item for item in capabilities}
    available = [c for c in capabilities if c["status"] == AVAILABLE]
    limited = [c for c in capabilities if c["status"] in {PARTIAL, SESSION_REQUIRED, MISSING} and not c.get("required")]
    failed_required = [c for c in capabilities if c.get("required") and c["status"] not in {AVAILABLE, PARTIAL}]

    intelligence = {
        "league_analysis": "ready" if not failed_required and by_key["league_info"]["available"] else "blocked",
        "team_analysis": "ready" if by_key["team_profiles"]["available"] or by_key["league_info"]["available"] else "limited",
        "player_analysis": "ready" if by_key["player_master"]["available"] or by_key["player_pool"]["available"] else "blocked",
        "manager_activity": "ready" if by_key["manager_activity"]["status"] == AVAILABLE else "limited",
        "trade_market": "ready" if by_key["trade_market"]["status"] == AVAILABLE else "limited",
    }

    return {
        "provider": provider_label,
        "status": "failed" if failed_required else "partial" if limited else "complete",
        "capabilities": capabilities,
        "by_key": by_key,
        "available_count": len(available),
        "limited_count": len(limited),
        "failed_required_count": len(failed_required),
        "required_failures": failed_required,
        "intelligence": intelligence,
        "summary": {
            "available": [c["key"] for c in capabilities if c["status"] == AVAILABLE],
            "limited": [c["key"] for c in limited],
            "blocked": [c["key"] for c in failed_required],
        },
    }


def capability_lines(report: Dict[str, Any]) -> List[str]:
    """Render concise capability lines for Scout and validation output."""
    icons = {
        AVAILABLE: "✓",
        PARTIAL: "⚠",
        SESSION_REQUIRED: "⚠",
        MISSING: "—",
        NOT_SUPPORTED: "—",
        FAILED: "✗",
    }
    lines: List[str] = []
    for cap in report.get("capabilities", []):
        if not isinstance(cap, dict):
            continue
        icon = icons.get(str(cap.get("status")), "—")
        lines.append(f"{icon} {cap.get('label')} — {cap.get('status')}: {cap.get('reason')}")
    return lines


def capability_dashboard(report: Dict[str, Any]) -> Dict[str, Any]:
    """Return a UI-friendly capability dashboard payload."""
    return {
        "provider": report.get("provider"),
        "status": report.get("status"),
        "available_count": report.get("available_count", 0),
        "limited_count": report.get("limited_count", 0),
        "failed_required_count": report.get("failed_required_count", 0),
        "capabilities": report.get("capabilities", []),
        "intelligence": report.get("intelligence", {}),
        "lines": capability_lines(report),
    }
