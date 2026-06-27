"""
Scout deterministic question router.

This is intentionally simple for Scout Alpha. It maps common plain-language
questions to Athena outputs and returns structured answer parts.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from Scout.conversation.context import (
    ScoutContext,
    find_team,
    get_team_names,
    league_average_asset_value,
    league_average_team_value,
    load_context,
)
from Scout.conversation.responses import developer_info, response

PROJECT_ROOT = Path(__file__).resolve().parents[2]


LEAGUE_INTENT_RE = re.compile(
    r"\b(analy[sz]e|assess|review|summari[sz]e|diagnose|grade)\b.*\b(my\s+)?(league|team|roster|draft|keepers?)\b|\b(my\s+)?(league|team|roster)\b.*\b(analy[sz]e|assessment|weakness|strength|draft|prep|recommend)",
    re.IGNORECASE,
)

PLAYER_COMMAND_RE = re.compile(
    r"^\s*(analy[sz]e|tell\s+me\s+about|show\s+me|profile|evaluate|who\s+is|what\s+about)\s+(.+?)\s*$",
    re.IGNORECASE,
)


def _looks_like_league_intent(q: str) -> bool:
    text = (q or "").strip().lower()
    if not text:
        return False
    direct = [
        "analyze my league",
        "analyse my league",
        "assess my league",
        "review my league",
        "league analysis",
        "league assessment",
        "draft prep",
        "team weaknesses",
        "roster weaknesses",
        "my roster",
        "my team",
    ]
    return any(item in text for item in direct) or bool(LEAGUE_INTENT_RE.search(text))


def _normalise_player_prompt(question: str) -> str:
    """Strip conversational wrappers while preserving the likely player name.

    This makes `Auston Matthews`, `Analyze Auston Matthews`, and
    `Tell me about Auston Matthews` converge before Player Intelligence runs.
    Fuzzy matching and ambiguous-name resolution remain owned by the lower
    identity/intelligence layers.
    """
    raw = (question or "").strip()
    match = PLAYER_COMMAND_RE.match(raw)
    if match:
        return match.group(2).strip(' .?!"\'') or raw
    return raw


def _no_silent_failure_response(ctx: ScoutContext, question: str, selected_mode: str) -> Dict[str, Any]:
    prompt = (question or "").strip()
    return response(
        intent="clarify_or_help",
        title="Scout needs one more detail",
        engine_conclusion=(
            "I could not route that question to a confident Athena intelligence path yet. "
            "Ask about a player, your fantasy league, a team/roster weakness, draft prep, manager activity, "
            "league market, contracts, or public sports context."
        ),
        observed_facts=[
            f"User prompt: {prompt or '(empty)'}.",
            f"Selected mode: {selected_mode or 'unknown'}.",
            "Scout returned a clarifying response instead of silently failing or inventing an answer.",
        ],
        known_limitations=[
            "Scout Alpha still uses deterministic routing before full natural-language planning.",
            "If this was a player question, try the player name only or include first and last name.",
            "If this was a league question, try 'Analyze my league' or 'Show my team weaknesses'.",
        ],
        confidence=0.35,
        cards=[
            {"label": "Try", "value": "Analyze my league", "prompt": "Analyze my league", "action": "ask_prompt"},
            {"label": "Try", "value": "Auston Matthews", "prompt": "Auston Matthews", "action": "ask_prompt"},
            {"label": "Try", "value": "What evidence did you use?", "prompt": "What evidence did you use?", "action": "ask_prompt"},
        ],
        developer=developer_info(
            "clarify_or_help",
            ctx.files_loaded,
            knowledge_used=[],
            intelligence_used=["scout_router"],
            files_read=[],
            missing=["full_natural_language_planner"],
        ),
    )

try:
    from Knowledge.Sources.public_hockey_retrieval import retrieve_public_hockey_knowledge
except Exception:  # pragma: no cover - public knowledge is optional until packs exist
    retrieve_public_hockey_knowledge = None  # type: ignore

try:
    from Knowledge.Intelligence.Routing.request_router import analyze_public_request
    from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
    from Knowledge.Intelligence.Public.public_team_profiles import profile_for_team_entity
    from Knowledge.Intelligence.Public.public_answers import (
        disambiguation_answer,
        player_profile_answer,
        player_comparison_answer,
        team_profile_answer,
        team_comparison_answer,
        gap_answer,
    )
except Exception:  # pragma: no cover - PIF public layer remains optional during partial installs
    analyze_public_request = None  # type: ignore
    profile_for_entity = None  # type: ignore
    profile_for_team_entity = None  # type: ignore
    disambiguation_answer = None  # type: ignore
    player_profile_answer = None  # type: ignore
    player_comparison_answer = None  # type: ignore
    team_profile_answer = None  # type: ignore
    team_comparison_answer = None  # type: ignore
    gap_answer = None  # type: ignore


try:
    from Knowledge.Intelligence.Routing.multi_sport_router import route_multi_sport_query
except Exception:  # pragma: no cover - multi-sport routing is additive
    route_multi_sport_query = None  # type: ignore


try:
    from Knowledge.Events.live_intelligence import is_recent_event_query, select_live_evidence, live_intelligence_diagnostics
except Exception:  # pragma: no cover - live intelligence remains optional during partial installs
    is_recent_event_query = None  # type: ignore
    select_live_evidence = None  # type: ignore
    live_intelligence_diagnostics = None  # type: ignore

try:
    from Intelligence.Runtime import run_runtime_trace
except Exception:  # pragma: no cover - runtime diagnostics are additive
    run_runtime_trace = None  # type: ignore
try:
    from Intelligence.Player.player_intelligence import evaluate_player
except Exception:  # pragma: no cover - player intelligence is optional during partial installs
    evaluate_player = None  # type: ignore

try:
    from Intelligence.Context.context_intelligence import infer_evaluation_profile, apply_context_profile
except Exception:  # pragma: no cover - context intelligence is optional during partial installs
    infer_evaluation_profile = None  # type: ignore
    apply_context_profile = None  # type: ignore


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def _num(value: Any) -> str:
    try:
        if isinstance(value, float):
            return f"{value:,.2f}"
        return f"{int(value):,}"
    except Exception:
        return str(value)


def _manager_records(ctx: ScoutContext) -> List[Dict[str, Any]]:
    payload = ctx.manager_behavior or {}
    records = payload.get("records") if isinstance(payload, dict) else []
    return [r for r in records if isinstance(r, dict)]


def _market(ctx: ScoutContext) -> Dict[str, Any]:
    return ctx.league_market or {}


def _contracts(ctx: ScoutContext) -> List[Dict[str, Any]]:
    payload = ctx.player_contracts or {}
    records = payload.get("records") if isinstance(payload, dict) else []
    return [r for r in records if isinstance(r, dict)]


def _safe_round(value: Any, digits: int = 2) -> Any:
    try:
        return round(float(value), digits)
    except Exception:
        return value


def _league_profile_summary(ctx: ScoutContext) -> Dict[str, Any]:
    profile = ctx.league_profile if isinstance(ctx.league_profile, dict) else {}
    raw = ctx.raw_league_info if isinstance(getattr(ctx, "raw_league_info", None), dict) else {}
    teams = ctx.team_profiles or []
    roster_limits = profile.get("roster_limits") if isinstance(profile.get("roster_limits"), dict) else {}
    lineup_slots = profile.get("lineup_slots") if isinstance(profile.get("lineup_slots"), list) else []
    lineup = []
    for slot in lineup_slots:
        if isinstance(slot, dict) and slot.get("position"):
            lineup.append(f"{slot.get('active_slots', slot.get('max_active', '?'))}{slot.get('position')}")
    league_history_id = raw.get("leagueHistoryId") or raw.get("league_history_id") or profile.get("league_history_id")
    return {
        "league_name": profile.get("league_name") or raw.get("leagueName") or "unknown",
        "sport": profile.get("sport") or raw.get("sport") or "unknown",
        "season": profile.get("season") or raw.get("season") or "unknown",
        "team_count": profile.get("team_count") or len(teams) or "unknown",
        "roster_continuity": profile.get("roster_continuity") or "unknown",
        "league_subtype": profile.get("league_subtype") or "unknown",
        "scoring_model": profile.get("scoring_model") or "unknown",
        "scoring_detail": profile.get("scoring_detail") or "unknown",
        "competition_model": profile.get("competition_model") or "unknown",
        "lineup_lock_model": profile.get("lineup_lock_model") or "unknown",
        "keeper_count": profile.get("keeper_count") or "unknown",
        "contract_model": profile.get("contract_model") or "unknown",
        "contract_years": profile.get("contract_years") or "unknown",
        "historical_seasons": profile.get("historical_seasons") or "unknown",
        "asset_classes": profile.get("asset_classes") or [],
        "lineup": ", ".join(lineup) if lineup else "unknown",
        "max_players": roster_limits.get("max_total_players") or raw.get("rosterInfo", {}).get("maxTotalPlayers") or "unknown",
        "league_history_id": league_history_id or "not detected",
    }


def _manager_coverage(ctx: ScoutContext) -> Dict[str, Any]:
    teams = ctx.team_profiles or []
    managers = _manager_records(ctx)
    manager_ids = {str(row.get("team_id") or row.get("manager_id") or "") for row in managers}
    missing = []
    for team in teams:
        team_id = str(team.get("team_id") or "")
        if team_id and team_id not in manager_ids:
            missing.append(team.get("team_name") or team_id)
    total_transactions = 0
    for row in managers:
        facts = row.get("observed_facts") if isinstance(row.get("observed_facts"), dict) else row
        try:
            total_transactions += int(facts.get("transaction_count") or row.get("transaction_count") or 0)
        except Exception:
            pass
    average_per_team = round(total_transactions / len(teams), 2) if teams else 0
    average_active_manager = round(total_transactions / len(managers), 2) if managers else 0
    return {
        "teams": len(teams),
        "managers_with_activity": len(managers),
        "managers_without_activity": max(len(teams) - len(managers), 0),
        "missing_manager_activity": missing,
        "total_observed_transactions": total_transactions,
        "average_transactions_per_team": average_per_team,
        "average_transactions_per_active_manager": average_active_manager,
    }


def _draft_pick_status(ctx: ScoutContext) -> Dict[str, Any]:
    # Draft-pick files are not yet part of ScoutContext. Keep this bounded but
    # explicit so Scout can explain what is known versus missing.
    draft_results = PROJECT_ROOT / "Raw" / "draft_results.json"
    draft_picks = PROJECT_ROOT / "Raw" / "draft_picks.json"
    return {
        "draft_results_available": draft_results.exists(),
        "draft_picks_available": draft_picks.exists(),
        "status": "available" if draft_results.exists() or draft_picks.exists() else "not_synced_yet",
    }


def analyze_league(ctx: ScoutContext | None = None) -> Dict[str, Any]:
    ctx = ctx or load_context()
    market = _market(ctx)
    readiness = ctx.knowledge_readiness or {}
    readiness_summary = readiness.get("summary") if isinstance(readiness, dict) else {}
    liquidity = market.get("market_liquidity") if isinstance(market.get("market_liquidity"), dict) else {}
    profile = _league_profile_summary(ctx)
    coverage = _manager_coverage(ctx)
    draft_status = _draft_pick_status(ctx)

    subtype = str(profile.get("league_subtype") or "").replace("_", " ").strip()
    continuity = str(profile.get("roster_continuity") or "").replace("_", " ").strip()
    league_type = subtype or continuity or "unknown"
    if continuity and continuity not in league_type:
        league_type = f"{league_type} ({continuity})"
    asset_classes = profile.get("asset_classes") or []

    observed = [
        f"League: {profile['league_name']} ({profile['sport']} {profile['season']}).",
        f"League type: {league_type}; scoring: {profile['scoring_detail']} / {profile['scoring_model']}; competition: {profile['competition_model']}.",
        f"Keeper/contract model: {profile['keeper_count']} keepers, {profile['contract_model']}, {profile['contract_years']} contract years.",
        f"Lineup model: {profile['lineup_lock_model']} lock, active lineup {profile['lineup']}, roster max {profile['max_players']}.",
        f"Asset classes detected: {', '.join(asset_classes) if asset_classes else 'unknown'}.",
        f"Knowledge readiness score: {readiness_summary.get('overall_readiness_score', 'unknown')}.",
        f"Teams loaded: {coverage['teams']}; managers with observed transaction activity: {coverage['managers_with_activity']}; managers without observed activity: {coverage['managers_without_activity']}.",
        f"Canonical transactions: {market.get('transaction_count', coverage['total_observed_transactions'])}; asset movements: {market.get('asset_movement_count', 'unknown')}.",
        f"Average observed transactions: {coverage['average_transactions_per_team']} per team; {coverage['average_transactions_per_active_manager']} per active manager.",
        f"Market liquidity: {liquidity.get('classification', market.get('market_liquidity', 'unknown'))}.",
        f"League history identifier: {profile['league_history_id']}.",
        f"Draft-pick files: {draft_status['status']}.",
    ]
    if coverage["missing_manager_activity"]:
        observed.append("Teams with no observed transaction activity in this sync window: " + ", ".join(map(str, coverage["missing_manager_activity"])) + ".")

    limitations = []
    for item in liquidity.get("limitations", []) if isinstance(liquidity, dict) else []:
        limitations.append(str(item))
    if draft_status["status"] != "available":
        limitations.append("Draft results and draft-pick ownership are not synced yet, so draft-pick strategy is recognized as important but not fully evaluated.")
    if profile["league_history_id"] == "not detected":
        limitations.append("League history linkage was not detected yet; long-term league trend analysis requires historical season pulls.")
    else:
        limitations.append("League history ID is detected, but historical season trend fetching is not implemented in Scout Alpha yet.")
    limitations.extend([
        "Manager behavior is based on observed transaction history; managers with no observed moves are inactive in this data window, not necessarily inactive owners.",
        "Scout Alpha uses existing Athena outputs; it does not yet fetch the Fantrax finance page.",
        "Natural-language answers are deterministic templates in this alpha, not freeform AI reasoning.",
    ])

    cards = [
        {"label": "League type", "value": profile.get("league_subtype", "unknown")},
        {"label": "Keeper model", "value": f"{profile.get('keeper_count')} keepers"},
        {"label": "Teams", "value": coverage["teams"]},
        {"label": "Managers active", "value": f"{coverage['managers_with_activity']}/{coverage['teams']}"},
        {"label": "Avg tx/team", "value": coverage["average_transactions_per_team"]},
        {"label": "Transactions", "value": market.get("transaction_count", coverage["total_observed_transactions"])},
        {"label": "Market", "value": liquidity.get("classification", market.get("market_liquidity", "unknown"))},
        {"label": "History", "value": "detected" if profile["league_history_id"] != "not detected" else "missing"},
    ]

    return response(
        intent="analyze_league",
        title="League analysis",
        engine_conclusion=(
            f"Athena identifies this as a {league_type} league with {profile['team_count']} teams, "
            f"{profile['keeper_count']} keepers, {profile['contract_model']}, {profile['scoring_detail']} scoring, "
            f"and a {profile['lineup_lock_model']} lineup model. Current behavior evidence shows "
            f"{coverage['managers_with_activity']} of {coverage['teams']} managers with observed transaction activity and "
            f"{coverage['total_observed_transactions']} observed manager transactions in the synced history window."
        ),
        observed_facts=observed,
        known_limitations=limitations,
        confidence=0.84,
        cards=cards,
        developer=developer_info(
            "analyze_league",
            ctx.files_loaded,
            knowledge_used=["league_profile", "team_profile", "transaction_history", "player_contracts", "knowledge_readiness"],
            intelligence_used=["manager_behavior", "league_market", "league_profile_summary"],
            files_read=["Output/league_profile.json", "Output/knowledge_readiness.json", "Output/manager_behavior.json", "Output/league_market.json", "Raw/league_info.json"],
            missing=["finance_profile", "relationship_graph", "historical_season_fetch", "draft_pick_ownership_sync", "injury_availability"],
        ),
    )

def most_active_managers(ctx: ScoutContext) -> Dict[str, Any]:
    def _transaction_count(row):
        facts = row.get("observed_facts") if isinstance(row.get("observed_facts"), dict) else {}
        return int(facts.get("transaction_count") or row.get("transaction_count") or 0)

    managers = sorted(_manager_records(ctx), key=_transaction_count, reverse=True)
    top = managers[:5]
    observed = []
    for row in top:
        facts = row.get("observed_facts") if isinstance(row.get("observed_facts"), dict) else row
        profile = row.get("inferred_profile") if isinstance(row.get("inferred_profile"), dict) else row
        observed.append(
            f"{row.get('manager_name')}: {facts.get('transaction_count', 0)} transactions, "
            f"{profile.get('activity_band', 'unknown')} activity, "
            f"{profile.get('transaction_style', 'unknown')} style."
        )
    if not observed:
        observed = ["No manager behavior records are available yet."]

    return response(
        intent="most_active_managers",
        title="Most active managers",
        engine_conclusion="The most active managers are the ones with the highest observed transaction counts in the current transaction-history window.",
        observed_facts=observed,
        known_limitations=["This measures observed transaction activity only. It does not yet include trade negotiations, rejected trades, or official finance-page balances."],
        confidence=0.86 if top else 0.2,
        cards=[{"label": row.get("manager_name"), "value": _transaction_count(row)} for row in top],
        developer=developer_info(
            "most_active_managers",
            ctx.files_loaded,
            knowledge_used=["transaction_history"],
            intelligence_used=["manager_behavior"],
            files_read=["Output/manager_behavior.json"],
            missing=["relationship_graph", "trade_history"],
        ),
    )


def league_market(ctx: ScoutContext) -> Dict[str, Any]:
    market = _market(ctx)
    liquidity = market.get("market_liquidity") if isinstance(market.get("market_liquidity"), dict) else {}
    drivers = liquidity.get("drivers", []) if isinstance(liquidity, dict) else []
    limitations = liquidity.get("limitations", []) if isinstance(liquidity, dict) else []
    classification = liquidity.get("classification", market.get("market_liquidity", "unknown"))
    score = liquidity.get("score", "unknown")

    observed = [
        f"Market classification: {classification}.",
        f"Liquidity score: {score}.",
        f"Transactions: {market.get('transaction_count', 'unknown')}.",
        f"Asset movements: {market.get('asset_movement_count', 'unknown')}.",
    ]
    observed.extend([f"Driver: {driver}" for driver in drivers[:5]])

    return response(
        intent="league_market",
        title="League market",
        engine_conclusion=f"Athena currently classifies this league market as {classification} based on observed transaction activity.",
        observed_facts=observed,
        known_limitations=limitations or ["No explicit market limitations were recorded."],
        confidence=liquidity.get("confidence") if isinstance(liquidity, dict) else 0.6,
        cards=[
            {"label": "Classification", "value": classification},
            {"label": "Score", "value": score},
            {"label": "Transactions", "value": market.get("transaction_count", "unknown")},
            {"label": "Managers", "value": market.get("manager_count", "unknown")},
        ],
        developer=developer_info(
            "league_market",
            ctx.files_loaded,
            knowledge_used=["transaction_history"],
            intelligence_used=["league_market", "manager_behavior"],
            files_read=["Output/league_market.json", "Output/manager_behavior.json"],
            missing=["finance_profile", "relationship_graph"],
        ),
    )


def expiring_contracts(ctx: ScoutContext) -> Dict[str, Any]:
    records = _contracts(ctx)
    expiring = [r for r in records if str(r.get("contract_band") or r.get("contract_status") or "").lower() == "expiring" or int(r.get("years_remaining") or r.get("contract_years_remaining") or 99) <= 0]
    by_team: Dict[str, int] = {}
    examples: List[str] = []
    for row in expiring:
        team = row.get("fantasy_team") or "Unknown"
        by_team[team] = by_team.get(team, 0) + 1
        if len(examples) < 10:
            examples.append(f"{row.get('player_name')} ({team})")

    top = sorted(by_team.items(), key=lambda item: item[1], reverse=True)[:8]
    observed = [f"Expiring contracts found: {len(expiring)}."]
    observed.extend([f"{team}: {count}" for team, count in top])
    if examples:
        observed.append("Examples: " + "; ".join(examples) + ".")

    return response(
        intent="expiring_contracts",
        title="Expiring contracts",
        engine_conclusion="Athena can identify expiring contracts from live Fantrax contract values that have been normalized into contract runway fields.",
        observed_facts=observed,
        known_limitations=["Contract logic uses the active season context. The engine should be revalidated when the season rolls over."],
        confidence=0.9 if records else 0.2,
        cards=[{"label": team, "value": count} for team, count in top],
        developer=developer_info(
            "expiring_contracts",
            ctx.files_loaded,
            knowledge_used=["player_contracts"],
            intelligence_used=[],
            files_read=["Output/player_contracts.json"],
            missing=["future keeper decisions", "official offseason keeper state"],
        ),
    )


def compare_team(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    q = question.lower()
    team = None
    for candidate in get_team_names(ctx):
        if candidate.lower() in q:
            team = find_team(ctx, candidate)
            break
    if not team and ctx.team_profiles:
        # Alpha fallback: use first team and explain limitation.
        team = ctx.team_profiles[0]
        fallback = True
    else:
        fallback = False

    if not team:
        return response(
            intent="compare_team",
            title="Compare team",
            engine_conclusion="Athena cannot compare a team because no team profiles are available yet.",
            observed_facts=[],
            known_limitations=["Run the league analysis pipeline first."],
            confidence=0.0,
            developer=developer_info("compare_team", ctx.files_loaded, missing=["team_profiles"]),
        )

    league_total_avg = league_average_team_value(ctx)
    league_asset_avg = league_average_asset_value(ctx)
    team_total = float(team.get("total_asset_value") or 0)
    team_avg = float(team.get("average_asset_value") or 0)
    total_delta = round(team_total - league_total_avg, 3) if league_total_avg is not None else None
    avg_delta = round(team_avg - league_asset_avg, 3) if league_asset_avg is not None else None

    conclusion = f"Athena compared {team.get('team_name')} against current league roster-value averages."
    if total_delta is not None:
        if total_delta > 0:
            conclusion = f"{team.get('team_name')} is above league average by total roster value in the current Athena valuation model."
        elif total_delta < 0:
            conclusion = f"{team.get('team_name')} is below league average by total roster value in the current Athena valuation model."
        else:
            conclusion = f"{team.get('team_name')} is approximately league average by total roster value."

    observed = [
        f"Team total asset value: {_num(team_total)}.",
        f"League average total asset value: {_num(league_total_avg)}.",
        f"Total value delta: {_num(total_delta)}.",
        f"Team average asset value: {_num(team_avg)}.",
        f"League average asset value: {_num(league_asset_avg)}.",
        f"Average asset value delta: {_num(avg_delta)}.",
    ]
    top_assets = team.get("top_assets") or []
    if top_assets:
        observed.append("Top assets: " + "; ".join([f"{a.get('player_name')} ({a.get('position')})" for a in top_assets[:5]]) + ".")

    limitations = list(team.get("limitations") or [])
    if fallback:
        limitations.insert(0, "Scout Alpha did not detect a team name in the question, so it used the first available team profile as a fallback.")
    limitations.append("This comparison uses Athena's current valuation model, which is still early and should not be treated as final trade value.")

    return response(
        intent="compare_team",
        title=f"Team comparison: {team.get('team_name')}",
        engine_conclusion=conclusion,
        observed_facts=observed,
        known_limitations=limitations,
        confidence=team.get("confidence", 0.65),
        cards=[
            {"label": "Team total", "value": round(team_total, 2)},
            {"label": "League avg", "value": round(league_total_avg or 0, 2)},
            {"label": "Delta", "value": round(total_delta or 0, 2)},
            {"label": "Roster", "value": team.get("roster_size")},
        ],
        developer=developer_info(
            "compare_team",
            ctx.files_loaded,
            knowledge_used=["team_profile", "player_profile", "valuation_engine"],
            intelligence_used=[],
            files_read=["Output/team_profiles.json"],
            missing=["relationship_graph", "historical_player_trends", "injury_availability"],
        ),
    )


def limitations(ctx: ScoutContext) -> Dict[str, Any]:
    readiness = ctx.knowledge_readiness or {}
    missing = []
    if isinstance(readiness, dict):
        domains = readiness.get("domains") or []
        if isinstance(domains, list):
            missing = [d.get("domain") for d in domains if isinstance(d, dict) and d.get("status") == "missing"]
    if not missing:
        missing = ["finance_profile", "relationship_graph", "historical_player_trends", "injury_availability"]

    return response(
        intent="limitations",
        title="Known limitations",
        engine_conclusion="Athena is functional, but Scout Alpha should clearly expose what the engine does not know yet.",
        observed_facts=[f"Missing or limited domain: {item}" for item in missing],
        known_limitations=["This is expected in Alpha. Missing domains should become backlog items when real questions repeatedly expose them."],
        confidence=0.9,
        developer=developer_info(
            "limitations",
            ctx.files_loaded,
            knowledge_used=["knowledge_readiness"],
            intelligence_used=[],
            files_read=["Output/knowledge_readiness.json"],
            missing=missing,
        ),
    )


def public_sports_overview(ctx: ScoutContext) -> Dict[str, Any]:
    return response(
        intent="public_sports_overview",
        title="Public sports mode",
        engine_conclusion="Scout can route public hockey questions separately from fantasy league questions and can now retrieve bounded evidence from compact NHL rulebook and NHL/NHLPA MOU knowledge packs.",
        observed_facts=[
            "Mode: Public Sports.",
            "Public hockey knowledge packs are used for NHL rulebook and NHL/NHLPA MOU topics.",
            "Fantasy league context is not applied in this mode unless explicitly connected to a fantasy question.",
        ],
        known_limitations=[
            "This layer retrieves source/topic evidence only; full legal, cap, waiver, and LTIR calculations require dedicated intelligence modules.",
            "Current answers remain deterministic and bounded to available knowledge-pack evidence.",
        ],
        confidence=0.72,
        cards=[
            {"label": "Mode", "value": "Public Sports"},
            {"label": "Rulebook", "value": "available"},
            {"label": "CBA/MOU", "value": "available"},
        ],
        developer=developer_info(
            "public_sports_overview",
            ctx.files_loaded,
            knowledge_used=["public_hockey_knowledge_packs", "nhl_rulebook", "nhl_nhlpa_mou"],
            intelligence_used=[],
            files_read=["Knowledge/Packs/NHL/rulebook/2025_2026", "Knowledge/Packs/NHL/cba/2025_mou"],
            missing=["cap_calculator", "waiver_eligibility_engine", "ltir_calculator", "current_event_interpretation"],
        ),
    )


def _plain_rule_explanation(question: str, evidence: List[Dict[str, Any]]) -> str | None:
    """Return a simple user-facing explanation for common rule lookup prompts.

    The retrieval layer may correctly find a rule section without explaining it.
    This helper keeps Scout useful for basic public rules questions while still
    preserving the evidence/source details in observed facts and developer output.
    """
    q = (question or "").lower()
    labels = " ".join(str(item.get("label", "")) for item in evidence).lower()
    summaries = " ".join(str(item.get("summary", "")) for item in evidence).lower()
    haystack = q + " " + labels + " " + summaries
    if "icing" in haystack:
        return (
            "In hockey, icing is a stoppage that usually happens when a team shoots or clears the puck from its own side of center ice all the way past the opponent's goal line without it being touched. "
            "When icing is called, play stops and the faceoff comes back into the offending team's defensive zone. "
            "There are exceptions and judgment details, such as waved-off icing, shorthanded situations, and race/line-change rules, so Athena uses the NHL rulebook evidence below as the authoritative reference."
        )
    if "off-side" in haystack or "offside" in haystack or "off side" in haystack:
        return (
            "In hockey, offside generally means an attacking player entered the offensive zone before the puck. "
            "When offside is called, play is stopped and the faceoff is moved outside the attacking zone. "
            "Specific delayed-offside and tag-up details depend on the NHL rulebook evidence below."
        )
    if "face-off" in haystack or "faceoff" in haystack or "face off" in haystack:
        return (
            "A faceoff is the restart mechanism used after many stoppages. Officials drop the puck between opposing players at the appropriate faceoff spot based on why play stopped. "
            "The exact location and procedure are governed by the NHL game-flow rules referenced below."
        )
    return None


def _public_rule_source_links(question: str, evidence: List[Dict[str, Any]], explanation: str | None) -> List[Dict[str, Any]]:
    """Build compact source-link metadata for Scout UI rule evidence popups."""
    links: List[Dict[str, Any]] = []
    for item in evidence[:3]:
        refs = item.get("authority_refs", []) or []
        ref = str(refs[0] if refs else "registered topic")
        source_title = str(item.get("source_title") or "Public hockey knowledge pack")
        label = str(item.get("label") or "Rule evidence")
        summary = str(item.get("summary") or "")
        popup_parts = [source_title, ref]
        if explanation:
            popup_parts.extend(["", "Athena explanation:", explanation])
        if summary:
            popup_parts.extend(["", "Knowledge-pack evidence:", summary])
        popup_parts.extend(["", "Note: Athena currently stores section-level rule evidence for this topic. Use the source and rule/section location above as the authoritative rulebook reference."])
        links.append({
            "label": label,
            "title": f"{label} — {source_title}",
            "rule_reference": ref,
            "source_title": source_title,
            "summary": summary,
            "popup_text": "\n".join(popup_parts),
        })
    return links


def public_hockey_answer(ctx: ScoutContext, question: str, mode: str = "public_sports") -> Dict[str, Any]:
    """Bind Scout public-sports questions to compact public hockey retrieval.

    This answer does not perform legal/cap calculations. It reports only the
    evidence Athena found in verified/generated knowledge packs and clearly
    bounds the limitation when a question needs a dedicated intelligence module.
    """
    if retrieve_public_hockey_knowledge is None:
        return response(
            intent="public_hockey_knowledge",
            title="Public hockey knowledge unavailable",
            engine_conclusion="Athena could not load the public hockey retrieval layer.",
            observed_facts=[],
            known_limitations=["Run the public hockey knowledge pack builder and retrieval validation."],
            confidence=0.1,
            developer=developer_info("public_hockey_knowledge", ctx.files_loaded, missing=["Knowledge.Sources.public_hockey_retrieval"]),
        )

    retrieval = retrieve_public_hockey_knowledge(question, project_root=PROJECT_ROOT, mode=mode, limit=5, auto_build=False)
    evidence = retrieval.get("evidence", []) or []
    if not evidence:
        answer = response(
            intent="public_hockey_knowledge",
            title="Public hockey knowledge unavailable",
            engine_conclusion="Athena could not find a matching NHL rulebook or NHL/NHLPA MOU knowledge-pack topic for this question.",
            observed_facts=[f"Packs checked: {retrieval.get('packs_checked', 0)}."],
            known_limitations=list(retrieval.get("limitations") or []),
            confidence=retrieval.get("confidence", 0.25),
            cards=[
                {"label": "Mode", "value": "Public Sports"},
                {"label": "Evidence", "value": 0},
                {"label": "Status", "value": retrieval.get("status", "no_match")},
            ],
            developer=developer_info(
                "public_hockey_knowledge",
                ctx.files_loaded,
                knowledge_used=["public_hockey_knowledge_packs"],
                files_read=["Knowledge/Packs/NHL"],
                missing=["matching_public_hockey_topic"],
            ),
        )
        answer["natural_language_response"] = "I do not have a matching public hockey knowledge-pack topic for that question yet, so I will not invent an answer."
        answer["developer"]["retrieval"] = retrieval
        return answer

    top = evidence[:3]
    source_phrases = []
    observed = []
    for item in evidence[:5]:
        refs = "; ".join(item.get("authority_refs", []) or ["registered topic"])
        source_phrases.append(f"{item.get('label')} ({refs})")
        observed.append(f"{item.get('label')}: {item.get('summary')} Source: {item.get('source_title')} — {refs}.")

    rule_explanation = _plain_rule_explanation(question, evidence)
    conclusion = "Athena found public hockey knowledge-pack evidence relevant to this question: " + "; ".join(source_phrases[:3]) + "."
    if rule_explanation:
        natural = rule_explanation
    else:
        natural = (
            "I found bounded public hockey evidence for this question. "
            + "The strongest matches are "
            + "; ".join(source_phrases[:3])
            + ". I can use these as evidence, but this is not yet a full legal, salary-cap, LTIR, or waiver calculator."
        )
    answer = response(
        intent="public_hockey_knowledge",
        title="Public hockey knowledge",
        engine_conclusion=conclusion,
        observed_facts=observed,
        known_limitations=list(retrieval.get("limitations") or []),
        confidence=retrieval.get("confidence", 0.6),
        cards=[
            {"label": "Evidence", "value": retrieval.get("evidence_count", len(evidence))},
            {"label": "Packs", "value": retrieval.get("packs_checked", 0)},
            {"label": "Top source", "value": top[0].get("document_type", "unknown") if top else "none"},
        ],
        developer=developer_info(
            "public_hockey_knowledge",
            ctx.files_loaded,
            knowledge_used=["public_hockey_knowledge_packs", "nhl_rulebook", "nhl_nhlpa_mou"],
            intelligence_used=[],
            files_read=["Knowledge/Packs/NHL/rulebook/2025_2026", "Knowledge/Packs/NHL/cba/2025_mou"],
            missing=["cap_calculator", "waiver_eligibility_engine", "ltir_calculator", "current_event_interpretation"],
        ),
    )
    answer["natural_language_response"] = natural
    answer["source_links"] = _public_rule_source_links(question, evidence, rule_explanation)
    answer["raw_reasoning_output"] = conclusion
    answer["developer"]["retrieval"] = retrieval
    answer["developer"]["evidence_used"] = evidence
    answer["developer"]["raw_reasoning_output"] = conclusion
    return answer



def player_intelligence_answer(ctx: ScoutContext, question: str, mode: str = "fantasy") -> Dict[str, Any]:
    if evaluate_player is None:
        return response(
            intent="player_analysis",
            title="Player intelligence unavailable",
            engine_conclusion="Athena could not load the Player Intelligence module.",
            observed_facts=[],
            known_limitations=["Validate Sprint 4B.1 before using player intelligence in Scout."],
            confidence=0.1,
            developer=developer_info("player_analysis", ctx.files_loaded, missing=["Intelligence.Player.player_intelligence"]),
        )

    mode_key = "public" if (mode or "").lower() == "public" else "fantasy"
    evaluation = evaluate_player(question, mode=mode_key, project_root=PROJECT_ROOT)
    selected_profile = mode_key
    if infer_evaluation_profile is not None:
        selected_profile = infer_evaluation_profile(question, default=mode_key)
    if apply_context_profile is not None and evaluation.get("status") == "available":
        evaluation = apply_context_profile(evaluation, profile=selected_profile, question=question)

    # Scout Build 001: route available player evidence through Reasoning and
    # compose an executive assessment. Fall back to the raw player intelligence
    # response if the reasoning layer is unavailable.
    reasoning_assessment = None
    executive_brief = None
    if evaluation.get("status") == "available":
        try:
            from Reasoning.adapters.player_evidence_adapter import build_player_profile_from_evaluation
            from Reasoning.reasoning_engine import ReasoningEngine
            from Reasoning.composition.executive_brief import ExecutiveBriefComposer

            profile = build_player_profile_from_evaluation(evaluation, fallback_name=question)
            reasoning_assessment = ReasoningEngine().reason_about_player(profile, evaluation)
            executive_brief = ExecutiveBriefComposer().build_player_brief(
                reasoning_assessment,
                evaluation=evaluation,
                question=question,
                mode=mode_key,
            )
        except Exception as ex:  # pragma: no cover - fallback keeps Scout usable
            executive_brief = None
            evaluation.setdefault("developer", {}).setdefault("missing", []).append(f"reasoning_composition_error:{ex}")

    cards = []
    player = evaluation.get("player") if isinstance(evaluation.get("player"), dict) else {}
    profiles = evaluation.get("profiles") if isinstance(evaluation.get("profiles"), dict) else {}
    production = profiles.get("production") if isinstance(profiles.get("production"), dict) else {}
    contract = profiles.get("contract") if isinstance(profiles.get("contract"), dict) else {}

    if executive_brief:
        cards.extend(executive_brief.get("cards") or [])
    else:
        if player.get("position"):
            cards.append({"label": "Position", "value": player.get("position")})
        if player.get("nhl_team"):
            cards.append({"label": "NHL team", "value": player.get("nhl_team")})
        if production.get("points") is not None:
            cards.append({"label": "Points", "value": int(production.get("points") or 0)})
        if production.get("points_per_game") is not None:
            cards.append({"label": "PPG", "value": round(float(production.get("points_per_game") or 0), 3)})
        if mode_key == "fantasy" and player.get("fantasy_team"):
            cards.append({"label": "Fantasy team", "value": player.get("fantasy_team")})
        if mode_key == "fantasy" and contract.get("years_remaining") is not None:
            cards.append({"label": "Contract", "value": contract.get("years_remaining")})

    context_profile = evaluation.get("context_profile") if isinstance(evaluation.get("context_profile"), dict) else {}
    if context_profile:
        cards.append({"label": "Profile", "value": context_profile.get("profile_label", selected_profile)})
        cards.append({"label": "Context", "value": context_profile.get("context_readiness", "unknown")})

    conclusion = (
        executive_brief.get("executive_summary")
        if executive_brief
        else evaluation.get("contextual_evaluation") or evaluation.get("evaluation", "Athena completed a bounded player evaluation.")
    )

    observed = list(evaluation.get("observed_facts") or [])
    if executive_brief:
        evidence_counts = executive_brief.get("evidence_counts") if isinstance(executive_brief.get("evidence_counts"), dict) else {}
        observed = [
            f"{str(label).replace('_', ' ').title()} evidence available: {count}."
            for label, count in evidence_counts.items()
        ]
        if not observed:
            observed = list(executive_brief.get("supporting_evidence") or [])[:6]

    answer = response(
        intent="player_analysis",
        title=(executive_brief or {}).get("title") or evaluation.get("title", "Player intelligence"),
        engine_conclusion=conclusion,
        observed_facts=observed,
        known_limitations=list(evaluation.get("limitations") or []),
        confidence=(executive_brief or {}).get("confidence", evaluation.get("confidence", 0.5)),
        cards=cards,
        developer=developer_info(
            "player_analysis",
            ctx.files_loaded,
            knowledge_used=["player_master", "player_production", "player_profile", "player_contracts", "player_status"],
            intelligence_used=["player_intelligence", "reasoning_engine", "executive_brief_composer"] if executive_brief else ["player_intelligence"],
            files_read=(evaluation.get("developer") or {}).get("files_read", []),
            missing=(evaluation.get("developer") or {}).get("missing", []),
        ),
    )

    answer["natural_language_response"] = (
        executive_brief.get("natural_language_response")
        if executive_brief
        else evaluation.get("contextual_evaluation") or evaluation.get("evaluation", answer.get("engine_conclusion"))
    )
    answer["developer"]["player_evaluation"] = evaluation
    if reasoning_assessment is not None:
        answer["developer"]["reasoning_assessment"] = (
            reasoning_assessment.as_dict() if hasattr(reasoning_assessment, "as_dict") else str(reasoning_assessment)
        )
    if executive_brief:
        answer["developer"]["executive_brief"] = executive_brief
    if context_profile:
        answer["developer"]["context_profile"] = context_profile
    answer["developer"]["modules_executed"] = [
        "Intelligence.Player.evaluate_player",
        "Intelligence.Context.apply_context_profile",
        "ReasoningEngine.reason_about_player",
        "ExecutiveBriefComposer.build_player_brief",
    ] if executive_brief else ["Intelligence.Player.evaluate_player", "Intelligence.Context.apply_context_profile"]
    return answer

def help_response(ctx: ScoutContext, question: str = "") -> Dict[str, Any]:
    examples = [
        "Analyze my league",
        "Who are the most active managers?",
        "Show the league market",
        "Show expiring contracts",
        "Compare Alien Agenda to league average",
        "What are the known limitations?",
    ]
    return response(
        intent="help",
        title="Ask Scout",
        engine_conclusion="Scout Alpha can answer a small set of deterministic questions using the Athena outputs that already exist.",
        observed_facts=["Try: " + example for example in examples],
        known_limitations=["Unsupported questions will return guidance rather than invented answers."],
        confidence=1.0,
        cards=[{"label": "Try", "value": example, "prompt": example, "action": "ask_prompt"} for example in examples[:4]],
        developer=developer_info(
            "help",
            ctx.files_loaded,
            knowledge_used=[],
            intelligence_used=[],
            files_read=[],
            missing=[],
        ),
    )



def _diagnostic_runtime_answer(ctx: ScoutContext, question: str, selected_mode: str) -> Dict[str, Any]:
    """Answer Scout self-diagnostic prompts using runtime/debug data."""
    q = (question or "").lower()
    trace_payload: Dict[str, Any] = {}
    stages: List[Dict[str, Any]] = []
    ledger: List[Dict[str, Any]] = []
    limitations: List[str] = []
    if run_runtime_trace is not None:
        sample_question = "Who is Auston Matthews?" if "module" in q else (question or "What can Athena currently answer?")
        try:
            trace = run_runtime_trace(sample_question, mode=selected_mode or "public")
            trace_payload = trace.to_dict() if hasattr(trace, "to_dict") else {}
            stages = trace_payload.get("stages", []) if isinstance(trace_payload.get("stages"), list) else []
            ledger = trace_payload.get("evidence_ledger", []) if isinstance(trace_payload.get("evidence_ledger"), list) else []
            limitations = list(trace_payload.get("limitations") or [])
        except Exception as exc:  # noqa: BLE001
            limitations.append(f"Runtime trace failed: {type(exc).__name__}: {exc}")
    else:
        limitations.append("Runtime orchestration layer is unavailable.")

    module_names = [str(stage.get("name")) for stage in stages if isinstance(stage, dict) and stage.get("name")]
    observed = []
    if module_names:
        observed.append("Runtime stages executed: " + ", ".join(module_names) + ".")
    for stage in stages:
        if isinstance(stage, dict):
            observed.append(f"{stage.get('name')}: {stage.get('status')} — {stage.get('detail')}")
    if ledger:
        observed.append("Evidence ledger: " + "; ".join(f"{item.get('source')}={item.get('evidence_count')}" for item in ledger if isinstance(item, dict)) + ".")
    if not observed:
        observed = ["Scout diagnostic routing executed, but no runtime stages were returned."]
    title = "Scout runtime diagnostics"
    if "evidence" in q:
        title = "Scout evidence trace"
    elif "module" in q:
        title = "Scout modules executed"
    elif "pipeline" in q or "trace" in q:
        title = "Scout pipeline trace"
    cards = [
        {"label": "Stages", "value": len(stages)},
        {"label": "Status", "value": trace_payload.get("status", "unknown") if trace_payload else "unknown"},
        {"label": "Evidence", "value": len(ledger)},
    ]
    return response(
        intent="scout_runtime_diagnostics",
        title=title,
        engine_conclusion="Scout routed this as a runtime diagnostic request and returned the available pipeline trace instead of asking for clarification.",
        observed_facts=observed[:12],
        known_limitations=limitations or ["Runtime diagnostics are observational; they do not change the underlying answer path."],
        confidence=0.86 if stages else 0.45,
        cards=cards,
        developer=developer_info(
            "scout_runtime_diagnostics",
            ctx.files_loaded,
            knowledge_used=["runtime_trace", "evidence_ledger"],
            intelligence_used=["runtime_orchestration", "scout_acceptance_hotfix"],
            files_read=["Intelligence/Runtime/orchestrator.py"],
            missing=[] if stages else ["runtime_trace_output"],
        ) | {"runtime_trace": trace_payload},
    )



def _normalize_public_query_text(question: str) -> str:
    """Normalize common fan shorthand before deterministic public routing.

    This keeps phrasing such as "Leaf's weakness" from missing the
    Toronto Maple Leafs entity and falling into broad contender analysis.
    """
    text = (question or "").strip().lower()
    text = re.sub(r"\bleaf['’]?s\b", "leafs", text)
    text = re.sub(r"\bmaple leaf['’]?s\b", "maple leafs", text)
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_targeted_team_query(question: str) -> bool:
    q = _normalize_public_query_text(question)
    team_terms = (
        "leafs", "maple leafs", "toronto", "oilers", "edmonton",
        "hurricanes", "carolina", "avalanche", "colorado",
        "stars", "dallas", "panthers", "florida",
    )
    return any(term in q for term in team_terms)


_PUBLIC_ANALYTICAL_RE = re.compile(
    r"\b(contenders?|stanley cup|cup contender|best teams?|teams? (?:are )?strongest|strongest teams?|strongest .* teams?|top teams?|who improved|improved the most|why .* contenders?|championship window|playoff contender|playoff ceiling|how good (?:is|are)|chances? (?:this year|next season|right now)?|how far can|are .* good|why .* struggled|why .* struggle|weakness(?:es)?|what.*weak(?:ness|nesses)|where.*weak|flaws?|problems?)\b",
    re.IGNORECASE,
)


def _is_public_analytical_query(question: str) -> bool:
    """Detect broad public-analysis prompts that should not fall to clarify."""
    text = (question or "").strip()
    if not text:
        return False
    return bool(_PUBLIC_ANALYTICAL_RE.search(text))


def _team_score_from_seed(profile: Any, question: str) -> float:
    """Small deterministic seed-only contender score used until live standings are attached."""
    text = (question or "").lower()
    score = 0.5
    blob = " ".join([
        str(getattr(profile, "identity", "")),
        str(getattr(profile, "history", "")),
        str(getattr(profile, "organizational_context", "")),
        str(getattr(profile, "roster_context", "")),
        " ".join(getattr(profile, "public_questions", []) or []),
    ]).lower()
    if "championship" in blob or "stanley cup" in blob or "won stanley" in blob:
        score += 0.12
    if "star" in blob or "elite" in blob or "franchise" in blob:
        score += 0.12
    if "sustained contention" in blob or "championship window" in blob or "proven championship" in blob:
        score += 0.14
    if "depth" in blob or "goaltending" in blob or "health" in blob or "cap" in blob:
        score -= 0.04
    # Question-specific hints.
    if "oilers" in text and "edmonton" in str(getattr(profile, "display_name", "")).lower():
        score += 0.1
    if "leafs" in text and "toronto" in str(getattr(profile, "display_name", "")).lower():
        score += 0.1
    if "hurricanes" in text and "carolina" in str(getattr(profile, "display_name", "")).lower():
        score += 0.1
    if "avalanche" in text and "colorado" in str(getattr(profile, "display_name", "")).lower():
        score += 0.1
    return max(0.1, min(0.95, round(score, 3)))


def _public_analytical_answer(ctx: ScoutContext, question: str, selected_mode: str) -> Dict[str, Any]:
    """Bounded public analytical response for broad team/contender questions.

    This intentionally uses seeded public team profiles plus available capability
    visibility. It should answer coherently instead of asking for clarification,
    while clearly stating that live standings, current roster/cap, and odds/market
    inputs are not attached yet.
    """
    try:
        from Knowledge.Intelligence.Public.public_team_profiles import public_team_profiles
    except Exception:
        public_team_profiles = lambda: []  # type: ignore

    profiles = list(public_team_profiles() or [])
    if not profiles:
        return response(
            intent="public_analytical_route",
            title="Public analytical route unavailable",
            engine_conclusion="I recognized this as a public analytical sports question, but no public team profiles are currently available.",
            observed_facts=[f"Question: {question}"],
            known_limitations=["Public team seed profiles are required before broad contender/ranking questions can be answered."],
            confidence=0.32,
            developer=developer_info(
                "public_analytical_route",
                ctx.files_loaded,
                knowledge_used=[],
                intelligence_used=["public_analytical_routing"],
                missing=["public_team_profiles"],
            ),
        )

    q = _normalize_public_query_text(question)
    target_terms = {
        "oilers": "edmonton",
        "edmonton": "edmonton",
        "leafs": "toronto",
        "maple leafs": "toronto",
        "toronto": "toronto",
        "hurricanes": "carolina",
        "carolina": "carolina",
        "avalanche": "colorado",
        "colorado": "colorado",
        "stars": "dallas",
        "dallas": "dallas",
        "panthers": "florida",
        "florida": "florida",
    }
    selected = []
    for term, name_part in target_terms.items():
        if term in q:
            selected = [p for p in profiles if name_part in str(getattr(p, "display_name", "")).lower()]
            break
    if not selected:
        selected = sorted(profiles, key=lambda p: _team_score_from_seed(p, question), reverse=True)[:4]

    observed: List[str] = []
    natural_lines: List[str] = []
    cards: List[Dict[str, Any]] = []
    for idx, profile in enumerate(selected, 1):
        score = _team_score_from_seed(profile, question)
        name = getattr(profile, "display_name", "Unknown team")
        identity = str(getattr(profile, "identity", "")).rstrip(".")
        org = str(getattr(profile, "organizational_context", "")).rstrip(".")
        roster = str(getattr(profile, "roster_context", "")).rstrip(".")
        natural_lines.append(f"{idx}. {name}: {org or identity}")
        if roster:
            natural_lines.append(f"   Current lens: {roster}")
        observed.append(f"{name}: contender signal {score}; {identity}")
        cards.append({"label": name, "value": f"{int(score*100)}% seed signal"})

    if selected and len(selected) == 1:
        selected_name = getattr(selected[0], 'display_name', 'Team')
        if any(term in q for term in ["weakness", "weaknesses", "risk", "risks", "problem", "problems", "struggle", "struggles", "struggling", "hold them back"]):
            title = f"{selected_name} weakness analysis"
            conclusion = (
                f"I recognized this as a targeted weakness/risk question about {selected_name}, not a general team profile."
            )
        elif 'defens' in q and ('oilers' in q or 'edmonton' in q):
            title = f"{selected_name} defensive analysis"
            conclusion = (
                "Edmonton's defensive struggles are best framed as a support-structure problem around an elite offensive core, "
                "not as evidence that the offensive core is insufficient."
            )
        else:
            title = f"{selected_name} analytical profile"
            conclusion = (
                f"I recognized this as a public analytical question about {selected_name}. "
                "Using the available public team profile, this answer can discuss identity, championship window, and roster-context questions, but not live standings or cap math yet."
            )
    else:
        title = "Public NHL contender analysis"
        conclusion = (
            "I recognized this as a public analytical NHL question. Based on the current seeded public team profiles, Athena can frame likely contender tiers, "
            "but it cannot yet produce a live standings/statistical ranking."
        )

    weakness_terms = ["weakness", "weaknesses", "risk", "risks", "problem", "problems", "struggle", "struggles", "struggling", "hold them back", "what's wrong", "whats wrong"]
    if selected and len(selected) == 1 and any(term in q for term in weakness_terms):
        profile = selected[0]
        name = getattr(profile, "display_name", "This team")
        risks = list(getattr(profile, "risks", []) or [])
        strengths = list(getattr(profile, "strengths", []) or [])
        analytical = str(getattr(profile, "analytical_read", "")).rstrip(".")
        roster = str(getattr(profile, "roster_context", "")).rstrip(".")
        roster = roster.replace("Seed context recognizes", "The available public profile recognizes")
        roster = roster.replace("future inputs", "needed for current-state analysis")
        competitive = str(getattr(profile, "competitive_identity", "")).rstrip(".")
        if 'defens' in q and ('oilers' in q or 'edmonton' in q):
            natural = (
                "Edmonton's defensive problem is not explained by a lack of offensive talent. It is a roster-balance and support-structure problem: the available team profile identifies an elite McDavid/Draisaitl offensive core, but the unresolved variables around that core are defense, goaltending, depth, health, cap flexibility, and deployment.\n\n"
                "High-end centers can tilt the ice and create scoring, but they do not automatically solve defensive-zone exits, matchup depth, penalty killing, save-percentage volatility, or the quality of the second and third defensive pairs. When a team is built around elite offense, every weakness behind that core becomes more visible because the championship expectation is higher.\n\n"
                "The analytical read is: Edmonton can have enough top-end talent to contend while still being structurally vulnerable if the supporting defense/goaltending layer is inconsistent."
            )
        else:
            named_risks = ", ".join(risks) if risks else "the support layer around the core"
            named_strengths = ", ".join(strengths) if strengths else "the team's established strengths"
            paragraphs = [
                f"{name} does not have one single weakness; the concern is whether the support layer is strong enough for the team's best traits to translate in high-leverage games.",
                f"The main risk areas Athena can identify from the current public profile are: {named_risks}.",
                f"That matters because the positive case is built around {named_strengths}. If those strengths are not supported by depth, structure, health, and postseason execution, the team can look strong on paper while still being vulnerable in high-leverage games.",
            ]
            if competitive:
                paragraphs.append(f"Competitive context: {competitive}.")
            if analytical:
                paragraphs.append(f"Analytical read: {analytical}.")
            if roster:
                paragraphs.append(f"Current context: {roster}.")
            natural = "\n\n".join(paragraphs)
    elif selected and len(selected) == 1:
        profile = selected[0]
        name = getattr(profile, "display_name", "This team")
        org = str(getattr(profile, "organizational_context", "")).rstrip(".")
        identity = str(getattr(profile, "identity", "")).rstrip(".")
        competitive = str(getattr(profile, "competitive_identity", "")).rstrip(".")
        analytical = str(getattr(profile, "analytical_read", "")).rstrip(".")
        roster = str(getattr(profile, "roster_context", "")).rstrip(".")
        core = list(getattr(profile, "core_players", []) or [])
        strengths = list(getattr(profile, "strengths", []) or [])
        risks = list(getattr(profile, "risks", []) or [])
        if "chance" in q or "this year" in q or "contender" in q or "how good" in q:
            opening = (
                f"{name} should be treated as a serious contender profile in Athena's current seeded public model, "
                "but not as a quantified prediction yet."
            )
        else:
            opening = f"{name} can be evaluated from its public identity, roster shape, strengths, and unresolved risk profile."
        paragraphs = [
            opening,
            "Organizational context: " + (org or identity),
        ]
        if competitive:
            paragraphs.append("Competitive identity: " + competitive)
        if core:
            paragraphs.append("Core read: " + ", ".join(core) + " anchor the profile.")
        if strengths:
            paragraphs.append("Why the case is positive: " + ", ".join(strengths) + ".")
        if risks:
            paragraphs.append("What can keep the ceiling from translating: " + ", ".join(risks) + ".")
        if analytical:
            paragraphs.append("Analytical lens: " + analytical)
        if roster:
            paragraphs.append("Roster read: " + roster)
        natural = "\n\n".join(part for part in paragraphs if part and not part.endswith(": "))
    elif "improved" in q or "offseason" in q:
        natural_intro = (
            "I can identify this as an offseason-improvement question, but Athena does not yet have a verified current transaction/roster-change feed attached. "
            "I will not rank improvement from stale or unrelated events. Based on seeded team context, the most useful current answer is what evidence is needed: trades/signings, cap movement, injuries, roster exits, and depth-chart changes."
        )
        natural = natural_intro + "\n" + "\n".join(natural_lines)
    else:
        natural_intro = (
            "Based on Athena's current public team profiles, not live standings or betting markets, the strongest seeded contender cases are:"
        )
        natural = natural_intro + "\n" + "\n".join(natural_lines)
    natural += (
        "\n\nFor a sharper current answer, Athena still needs current standings, injuries, playoff context, official roster/cap changes, recent transactions, goalie/deployment data, and current performance trends. "
        "Until those are attached, this should be treated as a bounded public profile analysis rather than a live ranking."
    )

    return response(
        intent="public_analytical_route",
        title=title,
        engine_conclusion=conclusion,
        observed_facts=observed[:8],
        known_limitations=[
            "This is a bounded seeded-profile analysis, not a live contender ranking.",
            "Live standings, current team statistics, cap, injury, and verified transaction feeds are not yet fully attached to this answer path.",
        ],
        confidence=0.68,
        cards=cards,
        natural_language_response=natural,
        developer=developer_info(
            "public_analytical_route",
            ctx.files_loaded,
            knowledge_used=["public_team_profiles", "public_identity_graph"],
            intelligence_used=["public_analytical_routing", "seeded_team_reasoning"],
            files_read=["Knowledge/Intelligence/Public/public_team_profiles.py"],
            missing=["live_standings", "current_team_statistics", "cap_feed", "official_transaction_feed"],
        ),
    )



def _event_date_label(event: Dict[str, Any]) -> str:
    value = str(event.get("published_at") or "").strip()
    return value or "date not provided by source"


def _event_source_links(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    links: List[Dict[str, Any]] = []
    for idx, event in enumerate(events[:8], 1):
        if not isinstance(event, dict):
            continue
        title = str(event.get("title") or f"Event {idx}").strip()
        summary = str(event.get("summary") or "").strip()
        url = str(event.get("url") or "").strip()
        published = _event_date_label(event)
        links.append({
            "label": f"Source {idx}",
            "title": title,
            "url": url,
            "summary": summary,
            "popup_text": f"{summary}\n\nPublished: {published}\nSource: {event.get('source_id', 'unknown')}\nURL: {url or 'not provided'}",
        })
    return links


def _compose_live_event_narrative(question: str, live: Dict[str, Any], events: List[Dict[str, Any]]) -> str:
    q = (question or "").lower()
    requested_types = set(str(x).lower() for x in (live.get("requested_event_types") or []))
    if not events:
        return ""
    if "trade" in requested_types or "trades" in q or "transaction" in requested_types:
        header = f"I found {len(events)} confirmed NHL trade/transaction item(s) from the configured live sources. I excluded rumor, grades, roundup, and speculation articles unless the item described an actual completed transaction."
    else:
        header = f"I found {len(events)} recent NHL event item(s) from the configured live sources."
    lines = [header]
    for idx, event in enumerate(events[:6], 1):
        title = str(event.get("title") or "Untitled event").strip()
        summary = str(event.get("summary") or "").strip()
        date = _event_date_label(event)
        source = str(event.get("source_id") or "source").strip()
        if summary and summary.lower() != title.lower():
            lines.append(f"{idx}. {title}. {summary} Source: {source}; date: {date}.")
        else:
            lines.append(f"{idx}. {title}. Source: {source}; date: {date}.")
    if live.get("ignored_count"):
        lines.append(f"I ignored {live.get('ignored_count')} lower-quality or non-matching item(s), including articles that matched the word 'trade' but were not confirmed transaction records.")
    return "\n\n".join(lines)

def _live_events_answer(ctx: ScoutContext, question: str, selected_mode: str) -> Dict[str, Any]:
    """Answer recent-event prompts with live/cached RSS evidence when configured."""
    if select_live_evidence is None:
        return response(
            intent="live_event_intelligence",
            title="Live intelligence unavailable",
            engine_conclusion="Scout could not load the live intelligence consumption layer.",
            observed_facts=[],
            known_limitations=["Validate Knowledge.Events.live_intelligence before testing recent-event prompts."],
            confidence=0.15,
            developer=developer_info("live_event_intelligence", ctx.files_loaded, missing=["Knowledge.Events.live_intelligence"]),
        )
    scout_live_default = os.environ.get("ATHENA_SCOUT_LIVE_NETWORK", "1").strip().lower() not in {"0", "false", "no", "off"}
    live = select_live_evidence(question=question, mode=selected_mode or "public", allow_network=scout_live_default, limit=6)
    events = live.get("events", []) if isinstance(live.get("events"), list) else []
    observed = []
    for event in events[:6]:
        if not isinstance(event, dict):
            continue
        date = event.get("published_at") or "date unavailable"
        observed.append(f"{event.get('event_type', 'news')}: {event.get('title')} — {event.get('summary')} ({date})")
    if not observed:
        observed = [
            f"RSS feeds configured: {live.get('feed_count', 0)}.",
            "No live/cached RSS events matched this prompt.",
        ]
    if events:
        natural = _compose_live_event_narrative(question, live, events)
        conclusion = "Scout selected source-backed live/cached event evidence for this recent-event question."
    else:
        requested_types = live.get("requested_event_types") or []
        requested_teams = live.get("requested_team_terms") or []
        if live.get("status") == "configured_no_matching_events" and (requested_types or requested_teams):
            team_terms = set(str(x).lower() for x in requested_teams)
            if {"maple", "leafs"} <= team_terms or "toronto" in team_terms:
                target = "Maple Leafs"
            else:
                target = "requested team/entity"
            event_type = ", ".join(str(x) for x in requested_types) or "event"
            natural = (
                f"I do not have a confirmed {target} {event_type} item from the configured live sources. "
                "I will not substitute an unrelated team or validation sample. "
                "If live RSS/network access is enabled and still returns no match, Athena needs a structured transaction/cap feed for exact trade assets and salary-cap impact."
            )
        else:
            natural = "RSS feeds are configured, but no usable live event evidence was selected for this prompt. I will not fill the gap with unrelated sample events."
        conclusion = natural
    cards = [
        {"label": "Feeds", "value": live.get("feed_count", 0)},
        {"label": "Events", "value": live.get("event_count", 0)},
        {"label": "Used", "value": live.get("selected_count", 0)},
        {"label": "Network", "value": "on" if live.get("network_enabled") else "off"},
    ]
    answer = response(
        intent="live_event_intelligence",
        title="Recent NHL events",
        engine_conclusion=conclusion,
        observed_facts=observed,
        known_limitations=list(live.get("limitations") or []),
        confidence=0.78 if events else 0.42,
        cards=cards,
        developer=developer_info(
            "live_event_intelligence",
            ctx.files_loaded,
            knowledge_used=["Knowledge.Events.live_sources", "Knowledge.Events.live_intelligence"],
            intelligence_used=["live_evidence_selection", "scout_runtime_acceptance_hotfix"],
            files_read=["Knowledge/Events/live_sources.py", "Knowledge/Events/live_intelligence.py"],
            missing=[] if events else ["selected_live_events"],
        ),
    )
    answer["natural_language_response"] = natural
    answer["source_links"] = _event_source_links(events)
    answer["developer"]["live_evidence"] = live
    answer["developer"]["evidence_ledger"] = live.get("evidence_ledger", [])
    return answer

def _multi_sport_route_card(ctx: ScoutContext, question: str, selected_mode: str) -> Dict[str, Any] | None:
    if route_multi_sport_query is None:
        return None
    route = route_multi_sport_query(question, mode=selected_mode)
    if route.route == "multi_sport_public" and not route.sport and not route.league and not route.entities:
        return None
    if route.confidence < 0.65 and route.route == "multi_sport_context":
        return None
    labels = list(route.entity_labels)
    source_text = ", ".join(route.allowed_sources) if route.allowed_sources else "identity registry"
    facts = [
        f"Route: {route.route}.",
        f"Sport/league: {route.sport or 'unknown'} / {route.league or 'unknown'}.",
        f"Allowed sources: {source_text}.",
    ]
    if labels:
        facts.append("Matched entities: " + ", ".join(labels[:4]) + ".")
    facts.extend(list(route.evidence[:3]))
    limitations = []
    if route.ambiguity:
        limitations.append("This query has an ambiguous identity match; Scout should ask the user to choose the intended entity before deeper reasoning.")
    else:
        limitations.append("This routing layer classifies sport/entity/source context; deeper statistical reasoning remains delegated to the sport knowledge and intelligence layers.")
    return response(
        intent=route.route,
        title="Multi-Sport Scout Routing",
        engine_conclusion=(
            "Scout identified the sport-aware routing context and separated public/provider-neutral sources "
            "from fantasy-owner context before deeper reasoning."
        ),
        observed_facts=facts,
        known_limitations=limitations,
        confidence=route.confidence,
        cards=[
            {"label": "Sport", "value": route.sport or "unknown"},
            {"label": "League", "value": route.league or "unknown"},
            {"label": "Intent", "value": route.intent},
            {"label": "Route", "value": route.route},
        ],
        developer=developer_info(
            route.route,
            ctx.files_loaded,
            knowledge_used=["Knowledge.Identity", "Knowledge.Intelligence.Routing.multi_sport_router"],
            intelligence_used=["multi_sport_scout_routing"],
            files_read=[],
            missing=["sport_statistical_knowledge_pack"] if route.route != "multi_sport_disambiguation" else ["user_disambiguation_selection"],
        ),
    )


def route_question(question: str, ctx: ScoutContext | None = None, mode: str = "fantasy") -> Dict[str, Any]:
    ctx = ctx or load_context()
    raw_question = (question or "").strip()
    q = raw_question.lower()
    selected_mode = (mode or "fantasy").strip().lower()

    if not q:
        return help_response(ctx, question)

    diagnostic_terms = ["what intelligence modules executed", "what modules executed", "what evidence did you use", "show pipeline trace", "pipeline trace", "runtime trace", "explain your reasoning"]
    if any(term in q for term in diagnostic_terms):
        return _diagnostic_runtime_answer(ctx, raw_question, selected_mode)

    if is_recent_event_query is not None and is_recent_event_query(raw_question):
        return _live_events_answer(ctx, raw_question, selected_mode)

    # League/team intent must win before player routing. This prevents prompts
    # such as "Analyze my league" from being treated as a failed player lookup.
    if _looks_like_league_intent(raw_question):
        return analyze_league(ctx)

    if any(term in q for term in ["most active", "active managers", "aggressive managers", "who is active", "who are active"]):
        return most_active_managers(ctx)

    if any(term in q for term in ["league market", "market", "liquidity", "activity"]):
        return league_market(ctx)

    if any(term in q for term in ["expiring", "contract", "contracts"]):
        return expiring_contracts(ctx)

    if any(term in q for term in ["limitation", "missing", "gaps", "what don't", "what dont", "what do not"]):
        return limitations(ctx)

    if selected_mode == "public":
        if any(term in q for term in ["overview", "what can", "help", "public sports"]):
            return public_sports_overview(ctx)

        if is_recent_event_query is not None and is_recent_event_query(raw_question):
            return _live_events_answer(ctx, raw_question, selected_mode)

        multi_sport_card = _multi_sport_route_card(ctx, raw_question, selected_mode)
        # Runtime continuation hotfix: routing output is diagnostic context, not
        # the final user-facing answer. Only stop here when the route requires
        # explicit user disambiguation; otherwise continue into the public
        # intelligence/knowledge layers so prompts such as "who are the Maple
        # Leafs" produce a team answer instead of a routing summary.
        # Multi-sport disambiguation is routing metadata. In public mode, let the
        # public identity layer build the user-facing candidate profiles/cards.
        if multi_sport_card is not None and multi_sport_card.get("intent") == "multi_sport_disambiguation" and analyze_public_request is None:
            return multi_sport_card

        # PIF Build 003: public intent/entity routing must run before generic
        # player evaluation or rulebook retrieval. This prevents public player,
        # comparison, draft, and event questions from leaking into fantasy owner
        # data or unrelated NHL/NHLPA MOU topics.
        if analyze_public_request is not None:
            public_route = analyze_public_request(raw_question)
            if public_route.route == "disambiguate_entity" and disambiguation_answer is not None:
                return disambiguation_answer(ctx, raw_question, public_route.entities)
            if public_route.route == "player_comparison" and player_comparison_answer is not None and profile_for_entity is not None:
                profiles = []
                for match in public_route.entities:
                    profile = profile_for_entity(match.entity) if getattr(match, "entity", None) is not None else None
                    if profile is not None:
                        profiles.append(profile)
                if len(profiles) >= 2:
                    return player_comparison_answer(ctx, profiles, raw_question)
            if public_route.route == "team_comparison" and team_comparison_answer is not None and profile_for_team_entity is not None:
                profiles = []
                for match in public_route.entities:
                    profile = profile_for_team_entity(match.entity) if getattr(match, "entity", None) is not None else None
                    if profile is not None:
                        profiles.append(profile)
                if len(profiles) >= 2:
                    return team_comparison_answer(ctx, profiles, raw_question)
            if public_route.route == "player_intelligence" and player_profile_answer is not None and profile_for_entity is not None:
                entity = public_route.entities[0].entity if public_route.entities else None
                profile = profile_for_entity(entity) if entity is not None else None
                if profile is not None:
                    return player_profile_answer(ctx, profile, raw_question)
            if public_route.route == "team_intelligence" and team_profile_answer is not None and profile_for_team_entity is not None:
                # Targeted contender/championship questions are analytical prompts,
                # not simple identity/profile requests. Keep narrow team-profile
                # questions on the seed profile path, but let questions such as
                # "Why are the Oilers contenders?" reach the bounded analytical
                # route so Scout explains contender logic instead of only
                # describing the team.
                normalized_public_question = _normalize_public_query_text(raw_question)
                if any(term in normalized_public_question for term in ["contender", "contenders", "championship window", "stanley cup", "cup contender"]):
                    return _public_analytical_answer(ctx, raw_question, selected_mode)
                entity = public_route.entities[0].entity if public_route.entities else None
                profile = profile_for_team_entity(entity) if entity is not None else None
                if profile is not None:
                    return team_profile_answer(ctx, profile, raw_question)
            if public_route.route in {"draft_intelligence_gap", "prospect_intelligence_gap", "event_intelligence_gap", "public_intelligence_gap"} and gap_answer is not None:
                if public_route.route == "public_intelligence_gap" and _is_public_analytical_query(raw_question):
                    return _public_analytical_answer(ctx, raw_question, selected_mode)
                return gap_answer(ctx, "More verified public evidence needed", public_route.route, raw_question, public_route.allowed_domains, public_route.blocked_domains)
            if public_route.route == "rulebook_knowledge":
                return public_hockey_answer(ctx, question, mode="public_sports")

        # Broad public analytical fallback. This runs after canonical public
        # intent/entity routing so targeted questions such as "Leafs weakness"
        # cannot be hijacked by the seeded contender-ranking path.
        if _is_public_analytical_query(raw_question):
            return _public_analytical_answer(ctx, raw_question, selected_mode)

        # Fallback for partially installed PIF: try Player Intelligence for bare names
        # and conversational wrappers. If unavailable, use bounded public hockey packs.
        player_prompt = _normalise_player_prompt(raw_question)
        candidate = player_intelligence_answer(ctx, player_prompt, mode="public")
        player_eval = candidate.get("developer", {}).get("player_evaluation", {}) if isinstance(candidate.get("developer"), dict) else {}
        if candidate.get("confidence", 0) > 0.2 or player_eval.get("status") in {"available", "ambiguous"}:
            return candidate

        hockey = public_hockey_answer(ctx, question, mode="public_sports")
        if hockey.get("confidence", 0) > 0.3:
            return hockey
        return _no_silent_failure_response(ctx, question, selected_mode)

    if any(term in q for term in ["compare", "league average", "team average"]):
        return compare_team(ctx, question)

    # Fantasy mode: try player intelligence for bare names and player-like questions.
    player_prompt = _normalise_player_prompt(raw_question)
    candidate = player_intelligence_answer(ctx, player_prompt, mode="fantasy")
    player_eval = candidate.get("developer", {}).get("player_evaluation", {}) if isinstance(candidate.get("developer"), dict) else {}
    if player_eval.get("status") in {"available", "ambiguous"}:
        return candidate

    return _no_silent_failure_response(ctx, question, selected_mode)

