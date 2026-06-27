"""
Athena Evaluation Engine.

Sprint 3E.4 introduces the deterministic question-to-evaluation path used by
Scout:

Question -> Intent Classification -> Evaluation Planner -> Execute Intelligence
Modules -> Evidence Collection -> Confidence -> Evaluation -> Scout Response.

The engine only evaluates evidence already present in Athena outputs. It does
not fetch provider data and it does not invent facts when evidence is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Callable

SUPPORTED_INTENTS = {
    "analyze_league",
    "analyze_team",
    "player_profile",
    "most_active_managers",
    "trade_market",
}


@dataclass
class EvaluationContext:
    question: str
    mode: str = "fantasy"
    provider: str = "unknown"
    files_loaded: list[str] = field(default_factory=list)
    raw_status: dict[str, bool] = field(default_factory=dict)
    league_profile: dict[str, Any] = field(default_factory=dict)
    knowledge_readiness: dict[str, Any] = field(default_factory=dict)
    team_profiles: list[dict[str, Any]] = field(default_factory=list)
    manager_behavior: dict[str, Any] = field(default_factory=dict)
    league_market: dict[str, Any] = field(default_factory=dict)
    transaction_history: dict[str, Any] = field(default_factory=dict)
    player_contracts: dict[str, Any] = field(default_factory=dict)
    player_master: list[dict[str, Any]] = field(default_factory=list)
    player_profiles: list[dict[str, Any]] = field(default_factory=list)
    player_values: list[dict[str, Any]] = field(default_factory=list)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _num(value: Any) -> str:
    if value is None:
        return "unknown"
    try:
        number = float(value)
        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.2f}"
    except Exception:
        return str(value)


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            return [row for row in records if isinstance(row, dict)]
    return []


def _readiness_score(ctx: EvaluationContext) -> float:
    readiness = ctx.knowledge_readiness or {}
    if not isinstance(readiness, dict):
        return 0.0
    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    return _safe_float(
        summary.get("overall_readiness_score")
        or readiness.get("overall_readiness_score")
        or readiness.get("overall_readiness")
    )


def _missing_domains(ctx: EvaluationContext) -> list[str]:
    readiness = ctx.knowledge_readiness or {}
    domains = readiness.get("domains") if isinstance(readiness, dict) else []
    missing: list[str] = []
    if isinstance(domains, list):
        for row in domains:
            if isinstance(row, dict) and _lower(row.get("status")) in {"missing", "partial"}:
                missing.append(_text(row.get("domain") or row.get("name")))
    elif isinstance(domains, dict):
        for name, row in domains.items():
            if isinstance(row, dict) and _lower(row.get("status")) in {"missing", "partial"}:
                missing.append(_text(name))
    return [item for item in missing if item]


def _manager_records(ctx: EvaluationContext) -> list[dict[str, Any]]:
    return _records(ctx.manager_behavior)


def _transaction_count(row: dict[str, Any]) -> int:
    facts = row.get("observed_facts") if isinstance(row.get("observed_facts"), dict) else {}
    return _safe_int(facts.get("transaction_count") or row.get("transaction_count"))


def _team_names(ctx: EvaluationContext) -> list[str]:
    return sorted([_text(team.get("team_name")) for team in ctx.team_profiles if team.get("team_name")])


def _find_team(ctx: EvaluationContext, query: str) -> tuple[dict[str, Any] | None, bool]:
    q = _lower(query)
    for team in ctx.team_profiles:
        name = _lower(team.get("team_name"))
        if name and name in q:
            return team, False
    for team in ctx.team_profiles:
        owner = _lower(team.get("manager_name") or team.get("owner_name"))
        if owner and owner in q:
            return team, False
    return (ctx.team_profiles[0], True) if ctx.team_profiles else (None, False)


def _league_average(ctx: EvaluationContext, key: str) -> float | None:
    values = [_safe_float(team.get(key), None) for team in ctx.team_profiles if team.get(key) not in (None, "")]
    values = [value for value in values if value is not None]
    return round(sum(values) / len(values), 3) if values else None


def _normalize_name(value: Any) -> str:
    name = _lower(value)
    if "," in name:
        parts = [part.strip() for part in name.split(",", 1)]
        if len(parts) == 2:
            name = f"{parts[1]} {parts[0]}"
    return " ".join(name.replace(".", "").split())


def _candidate_player_terms(question: str) -> list[str]:
    q = question.strip()
    patterns = ["tell me about", "what about", "analyze", "player", "about"]
    lowered = q.lower()
    for pattern in patterns:
        lowered = lowered.replace(pattern, " ")
    return [term for term in {q, lowered.strip()} if term]


def _find_player(ctx: EvaluationContext, question: str) -> dict[str, Any] | None:
    rows = ctx.player_values or ctx.player_profiles or ctx.player_master
    q_norm = _normalize_name(question)
    terms = [_normalize_name(term) for term in _candidate_player_terms(question)]
    best: tuple[int, dict[str, Any]] | None = None
    for row in rows:
        name = _normalize_name(row.get("player_name") or row.get("nhl_player_name"))
        if not name:
            continue
        score = 0
        if name in q_norm or any(name in term for term in terms):
            score = 100 + len(name)
        else:
            tokens = [token for token in name.split() if len(token) > 1]
            matched_tokens = [token for token in tokens if token in q_norm]
            # Avoid accidental one-token matches from common substrings, e.g.
            # Bo matching the word about. A player match needs either multiple
            # name tokens or one distinctive long token.
            if len(matched_tokens) >= 2:
                score = len(matched_tokens) * 10
            elif matched_tokens and len(matched_tokens[0]) >= 5:
                score = 8
        if score and (best is None or score > best[0]):
            best = (score, row)
    return best[1] if best else None


def classify_intent(question: str, mode: str = "fantasy") -> dict[str, Any]:
    q = _lower(question)
    if (mode or "fantasy").lower() == "public":
        return {"intent": "public_sports_overview", "confidence": 0.9, "signals": ["public_mode"]}
    if not q:
        return {"intent": "help", "confidence": 1.0, "signals": ["empty_question"]}

    checks = [
        ("analyze_league", ["analyze my league", "analyze league", "league overview", "overview of my league"]),
        ("analyze_team", ["analyze my team", "my team", "analyze team", "team average", "league average", "compare"]),
        ("player_profile", ["tell me about", "player", "what about"]),
        ("most_active_managers", ["most active", "active managers", "aggressive managers", "who is active", "who are active"]),
        ("trade_market", ["trade market", "market", "liquidity", "activity", "trading"]),
    ]
    for intent, terms in checks:
        hits = [term for term in terms if term in q]
        if hits:
            return {"intent": intent, "confidence": min(0.95, 0.72 + (len(hits) * 0.06)), "signals": hits}
    return {"intent": "help", "confidence": 0.4, "signals": []}


def plan_evaluation(intent: str) -> dict[str, Any]:
    plans = {
        "analyze_league": {
            "modules": ["knowledge_readiness", "league_profile", "team_profiles", "league_market", "manager_behavior"],
            "files": ["Output/knowledge_readiness.json", "Output/league_profile.json", "Output/team_profiles.json", "Output/league_market.json", "Output/manager_behavior.json"],
        },
        "analyze_team": {
            "modules": ["team_profiles", "valuation_engine", "league_average_context"],
            "files": ["Output/team_profiles.json", "Output/player_values.json"],
        },
        "player_profile": {
            "modules": ["player_values", "player_profiles", "player_contracts", "player_master"],
            "files": ["Output/player_values.json", "Output/player_profiles.json", "Output/player_contracts.json", "Output/player_master.json"],
        },
        "most_active_managers": {
            "modules": ["manager_behavior", "transaction_history"],
            "files": ["Output/manager_behavior.json", "Output/transaction_history.json"],
        },
        "trade_market": {
            "modules": ["league_market", "manager_behavior", "transaction_history"],
            "files": ["Output/league_market.json", "Output/manager_behavior.json", "Output/transaction_history.json"],
        },
    }
    return plans.get(intent, {"modules": [], "files": []})


def _evidence(label: str, value: Any, source: str) -> dict[str, Any]:
    return {"label": label, "value": value, "source": source}


def _confidence(base: float, evidence_count: int, missing_count: int, intent_confidence: float) -> float:
    score = base + min(evidence_count, 8) * 0.025 - min(missing_count, 8) * 0.035
    score = (score * 0.75) + (intent_confidence * 0.25)
    return round(max(0.05, min(0.95, score)), 3)


def _evaluate_league(ctx: EvaluationContext, intent_confidence: float) -> dict[str, Any]:
    market = ctx.league_market or {}
    liquidity = market.get("market_liquidity") if isinstance(market.get("market_liquidity"), dict) else {}
    classification = liquidity.get("classification", market.get("market_liquidity", "unknown")) if isinstance(liquidity, dict) else "unknown"
    readiness = _readiness_score(ctx)
    evidence = [
        _evidence("Knowledge readiness score", readiness or "unknown", "Output/knowledge_readiness.json"),
        _evidence("Teams profiled", len(ctx.team_profiles), "Output/team_profiles.json"),
        _evidence("Managers analyzed", market.get("manager_count", "unknown"), "Output/league_market.json"),
        _evidence("Canonical transactions", market.get("transaction_count", "unknown"), "Output/league_market.json"),
        _evidence("Asset movements", market.get("asset_movement_count", "unknown"), "Output/league_market.json"),
        _evidence("Market liquidity", classification, "Output/league_market.json"),
    ]
    observed = [f"{item['label']}: {item['value']}." for item in evidence]
    limitations = _missing_domains(ctx) or []
    limitations.extend(["Finance-page balances, relationship graph, injury availability, and historical player trends are not yet authoritative unless their domains are present in Athena outputs."])
    return {
        "title": "League analysis",
        "engine_conclusion": "Athena can evaluate this league from current league profile, team profile, manager behavior, and market-liquidity evidence.",
        "observed_facts": observed,
        "known_limitations": limitations,
        "cards": [
            {"label": "Readiness", "value": readiness or "unknown"},
            {"label": "Teams", "value": len(ctx.team_profiles)},
            {"label": "Transactions", "value": market.get("transaction_count", "unknown")},
            {"label": "Market", "value": classification},
        ],
        "evidence_used": evidence,
        "confidence": _confidence(0.66, len(evidence), len(limitations), intent_confidence),
    }


def _evaluate_team(ctx: EvaluationContext, question: str, intent_confidence: float) -> dict[str, Any]:
    team, fallback = _find_team(ctx, question)
    if not team:
        return _no_evidence("Analyze team", "No team profiles are available. Run Athena sync/build first.", intent_confidence)
    league_total_avg = _league_average(ctx, "total_asset_value")
    league_asset_avg = _league_average(ctx, "average_asset_value")
    team_total = _safe_float(team.get("total_asset_value"))
    team_avg = _safe_float(team.get("average_asset_value"))
    total_delta = round(team_total - league_total_avg, 3) if league_total_avg is not None else None
    top_assets = team.get("top_assets") if isinstance(team.get("top_assets"), list) else []
    evidence = [
        _evidence("Team", team.get("team_name", "unknown"), "Output/team_profiles.json"),
        _evidence("Roster size", team.get("roster_size", "unknown"), "Output/team_profiles.json"),
        _evidence("Team total asset value", team_total, "Output/team_profiles.json"),
        _evidence("League average total asset value", league_total_avg, "Output/team_profiles.json"),
        _evidence("Total asset value delta", total_delta, "Output/team_profiles.json"),
        _evidence("Team average asset value", team_avg, "Output/team_profiles.json"),
        _evidence("League average asset value", league_asset_avg, "Output/team_profiles.json"),
    ]
    if top_assets:
        evidence.append(_evidence("Top assets", "; ".join([_text(row.get("player_name")) for row in top_assets[:5]]), "Output/team_profiles.json"))
    conclusion = f"Athena evaluated {team.get('team_name')} against the current league roster-value baseline."
    if total_delta is not None:
        if total_delta > 0:
            conclusion = f"{team.get('team_name')} is above league average by total roster value in the current Athena valuation model."
        elif total_delta < 0:
            conclusion = f"{team.get('team_name')} is below league average by total roster value in the current Athena valuation model."
        else:
            conclusion = f"{team.get('team_name')} is approximately league average by total roster value."
    limitations = list(team.get("limitations") or [])
    if fallback:
        limitations.insert(0, "Scout did not detect a team name, so Athena evaluated the first available team profile as a temporary fallback.")
    limitations.append("This is an evaluation of current Athena valuation outputs, not a final autonomous roster-management recommendation.")
    return {
        "title": f"Team analysis: {team.get('team_name')}",
        "engine_conclusion": conclusion,
        "observed_facts": [f"{item['label']}: {_num(item['value'])}." for item in evidence if item["value"] is not None],
        "known_limitations": limitations,
        "cards": [
            {"label": "Team total", "value": round(team_total, 2)},
            {"label": "League avg", "value": round(league_total_avg or 0, 2)},
            {"label": "Delta", "value": round(total_delta or 0, 2)},
            {"label": "Roster", "value": team.get("roster_size", "unknown")},
        ],
        "evidence_used": evidence,
        "confidence": _confidence(_safe_float(team.get("confidence"), 0.62), len(evidence), len(limitations), intent_confidence),
    }


def _evaluate_player(ctx: EvaluationContext, question: str, intent_confidence: float) -> dict[str, Any]:
    player = _find_player(ctx, question)
    if not player:
        return _no_evidence("Player profile", "Athena could not identify a player from the current player outputs.", intent_confidence)
    dimensions = player.get("dimensions") if isinstance(player.get("dimensions"), dict) else {}
    evidence = [
        _evidence("Player", player.get("player_name") or player.get("nhl_player_name"), "Output/player_values.json"),
        _evidence("Position", player.get("position"), "Output/player_values.json"),
        _evidence("Fantasy team", player.get("fantasy_team") or player.get("owner_team"), "Output/player_values.json"),
        _evidence("NHL team", player.get("nhl_team"), "Output/player_values.json"),
        _evidence("Overall asset value", player.get("overall_asset_value") or player.get("asset_value"), "Output/player_values.json"),
        _evidence("Current points", player.get("current_points"), "Output/player_values.json"),
        _evidence("Points per game", player.get("points_per_game"), "Output/player_values.json"),
        _evidence("Age", player.get("age"), "Output/player_values.json"),
        _evidence("Contract expiry", player.get("contract_expiry_year") or player.get("contract_year"), "Output/player_values.json"),
        _evidence("Contract runway", player.get("contract_years_remaining"), "Output/player_values.json"),
    ]
    dimension_bits = []
    for key in ["current", "future", "contract", "scarcity", "risk", "market"]:
        if key in dimensions:
            dimension_bits.append(f"{key}: {_num(dimensions.get(key))}")
    if dimension_bits:
        evidence.append(_evidence("Valuation dimensions", "; ".join(dimension_bits), "Output/player_values.json"))
    observed = [f"{item['label']}: {_num(item['value'])}." for item in evidence if item.get("value") not in (None, "")]
    if player.get("evidence") and isinstance(player.get("evidence"), list):
        observed.extend([f"Model evidence: {item}" for item in player.get("evidence", [])[:4]])
    limitations = ["Athena can only discuss player facts present in current player-value/profile outputs; missing production, injury, or trend inputs are not inferred."]
    confidence_values = [_safe_float(player.get("confidence"), 0.0)]
    if isinstance(player.get("evidence_completeness"), (int, float)):
        confidence_values.append(_safe_float(player.get("evidence_completeness")))
    base = mean([v for v in confidence_values if v]) if any(confidence_values) else 0.58
    return {
        "title": f"Player evaluation: {player.get('player_name') or player.get('nhl_player_name')}",
        "engine_conclusion": f"Athena found a current player evaluation for {player.get('player_name') or player.get('nhl_player_name')} and can explain the available valuation evidence.",
        "observed_facts": observed,
        "known_limitations": limitations,
        "cards": [
            {"label": "Value", "value": player.get("overall_asset_value") or player.get("asset_value") or "unknown"},
            {"label": "Position", "value": player.get("position") or "unknown"},
            {"label": "Fantasy team", "value": player.get("fantasy_team") or player.get("owner_team") or "unknown"},
            {"label": "PPG", "value": player.get("points_per_game") or "unknown"},
        ],
        "evidence_used": evidence,
        "confidence": _confidence(base, len(evidence), len(limitations), intent_confidence),
    }


def _evaluate_active_managers(ctx: EvaluationContext, intent_confidence: float) -> dict[str, Any]:
    managers = sorted(_manager_records(ctx), key=_transaction_count, reverse=True)
    top = managers[:5]
    evidence = []
    for row in top:
        facts = row.get("observed_facts") if isinstance(row.get("observed_facts"), dict) else row
        profile = row.get("inferred_profile") if isinstance(row.get("inferred_profile"), dict) else row
        evidence.append(_evidence(row.get("manager_name"), {"transactions": facts.get("transaction_count", 0), "activity": profile.get("activity_band", "unknown"), "style": profile.get("transaction_style", "unknown")}, "Output/manager_behavior.json"))
    if not top:
        market_top = ctx.league_market.get("most_active_managers") if isinstance(ctx.league_market, dict) else []
        if isinstance(market_top, list):
            for row in market_top[:5]:
                if isinstance(row, dict):
                    evidence.append(_evidence(row.get("manager_name") or row.get("team_name"), row, "Output/league_market.json"))
    observed = []
    for item in evidence:
        val = item["value"]
        if isinstance(val, dict):
            observed.append(f"{item['label']}: {val.get('transactions', val.get('transaction_count', 'unknown'))} transactions, {val.get('activity', val.get('activity_band', 'unknown'))} activity, {val.get('style', val.get('transaction_style', 'unknown'))} style.")
        else:
            observed.append(f"{item['label']}: {val}.")
    if not observed:
        observed = ["No manager behavior records are available yet."]
    limitations = ["This measures observed completed transactions only. It does not include rejected offers, negotiations, or informal trade talks."]
    return {
        "title": "Most active managers",
        "engine_conclusion": "Athena ranks active managers by observed transaction evidence in the current transaction-history window.",
        "observed_facts": observed,
        "known_limitations": limitations,
        "cards": [{"label": item["label"], "value": (item["value"].get("transactions") if isinstance(item["value"], dict) else item["value"])} for item in evidence],
        "evidence_used": evidence,
        "confidence": _confidence(0.64, len(evidence), len(limitations), intent_confidence),
    }


def _evaluate_trade_market(ctx: EvaluationContext, intent_confidence: float) -> dict[str, Any]:
    market = ctx.league_market or {}
    liquidity = market.get("market_liquidity") if isinstance(market.get("market_liquidity"), dict) else {}
    classification = liquidity.get("classification", market.get("market_liquidity", "unknown")) if isinstance(liquidity, dict) else "unknown"
    score = liquidity.get("score", "unknown") if isinstance(liquidity, dict) else "unknown"
    drivers = liquidity.get("drivers", []) if isinstance(liquidity, dict) else []
    limitations = liquidity.get("limitations", []) if isinstance(liquidity, dict) else []
    evidence = [
        _evidence("Market classification", classification, "Output/league_market.json"),
        _evidence("Liquidity score", score, "Output/league_market.json"),
        _evidence("Transactions", market.get("transaction_count", "unknown"), "Output/league_market.json"),
        _evidence("Asset movements", market.get("asset_movement_count", "unknown"), "Output/league_market.json"),
        _evidence("Managers", market.get("manager_count", "unknown"), "Output/league_market.json"),
    ]
    for driver in drivers[:5]:
        evidence.append(_evidence("Liquidity driver", driver, "Output/league_market.json"))
    observed = [f"{item['label']}: {item['value']}." for item in evidence]
    limitations = list(limitations) or ["No explicit market limitations were recorded in league_market.json."]
    limitations.append("Trade-market evaluation is based on completed transaction evidence, not private negotiation data.")
    return {
        "title": "Trade market evaluation",
        "engine_conclusion": f"Athena currently classifies this trade market as {classification} based on observed transaction activity.",
        "observed_facts": observed,
        "known_limitations": limitations,
        "cards": [
            {"label": "Classification", "value": classification},
            {"label": "Score", "value": score},
            {"label": "Transactions", "value": market.get("transaction_count", "unknown")},
            {"label": "Managers", "value": market.get("manager_count", "unknown")},
        ],
        "evidence_used": evidence,
        "confidence": _confidence(_safe_float(liquidity.get("confidence"), 0.6) if isinstance(liquidity, dict) else 0.6, len(evidence), len(limitations), intent_confidence),
    }


def _no_evidence(title: str, conclusion: str, intent_confidence: float) -> dict[str, Any]:
    return {
        "title": title,
        "engine_conclusion": conclusion,
        "observed_facts": [],
        "known_limitations": ["Athena did not have enough loaded evidence to evaluate this question deterministically."],
        "cards": [],
        "evidence_used": [],
        "confidence": _confidence(0.2, 0, 1, intent_confidence),
    }



def _public_overview(ctx: EvaluationContext, intent_confidence: float) -> dict[str, Any]:
    evidence = [
        _evidence("Mode", "Public Sports", "Scout mode selector"),
        _evidence("Provider", ctx.provider, "Evaluation context"),
    ]
    return {
        "title": "Public sports mode",
        "engine_conclusion": "Scout routes public sports questions separately from fantasy league questions; authoritative public-sports evaluation remains limited to Athena outputs currently available.",
        "observed_facts": ["Mode: Public Sports.", "Fantasy league context is not applied unless the question is routed to fantasy mode."],
        "known_limitations": ["NHL/NHLPA/CBA reasoning, cap, waivers, LTIR, and public trade-scenario modules are not yet authoritative in Scout."],
        "cards": [{"label": "Mode", "value": "Public Sports"}, {"label": "Fantasy context", "value": "off"}],
        "evidence_used": evidence,
        "confidence": _confidence(0.52, len(evidence), 1, intent_confidence),
    }

def _help(ctx: EvaluationContext, intent_confidence: float) -> dict[str, Any]:
    examples = [
        "Analyze my league",
        "Analyze my team",
        "Tell me about Auston Matthews",
        "Who are the most active managers?",
        "What's the trade market like?",
    ]
    evidence = [_evidence("Supported intents", list(SUPPORTED_INTENTS), "Intelligence/evaluation_engine.py")]
    return {
        "title": "Ask Scout",
        "engine_conclusion": "Scout can now route supported questions through Athena's deterministic Evaluation Engine.",
        "observed_facts": ["Try: " + example for example in examples],
        "known_limitations": ["Unsupported questions return guidance rather than invented answers."],
        "cards": [{"label": "Supported intents", "value": len(SUPPORTED_INTENTS)}],
        "evidence_used": evidence,
        "confidence": _confidence(0.75, 1, 1, intent_confidence),
    }


def execute_modules(intent: str, ctx: EvaluationContext, question: str, intent_confidence: float) -> dict[str, Any]:
    evaluators: dict[str, Callable[..., dict[str, Any]]] = {
        "analyze_league": lambda: _evaluate_league(ctx, intent_confidence),
        "analyze_team": lambda: _evaluate_team(ctx, question, intent_confidence),
        "player_profile": lambda: _evaluate_player(ctx, question, intent_confidence),
        "most_active_managers": lambda: _evaluate_active_managers(ctx, intent_confidence),
        "trade_market": lambda: _evaluate_trade_market(ctx, intent_confidence),
        "help": lambda: _help(ctx, intent_confidence),
        "public_sports_overview": lambda: _public_overview(ctx, intent_confidence),
    }
    return evaluators.get(intent, lambda: _help(ctx, intent_confidence))()


def evaluate(question: str, ctx: EvaluationContext) -> dict[str, Any]:
    classification = classify_intent(question, ctx.mode)
    intent = classification["intent"]
    intent_confidence = _safe_float(classification.get("confidence"), 0.4)
    plan = plan_evaluation(intent)
    executed = execute_modules(intent, ctx, question, intent_confidence)
    evidence_used = executed.get("evidence_used", [])
    developer = {
        "question": question,
        "context": {
            "mode": ctx.mode,
            "files_loaded": ctx.files_loaded,
            "raw_status": ctx.raw_status,
            "league": ctx.league_profile.get("league_name") if isinstance(ctx.league_profile, dict) else None,
            "sport": ctx.league_profile.get("sport") if isinstance(ctx.league_profile, dict) else None,
            "season": ctx.league_profile.get("season") if isinstance(ctx.league_profile, dict) else None,
        },
        "provider": ctx.provider,
        "intent": intent,
        "intent_classification": classification,
        "evaluation_plan": plan,
        "modules_executed": plan.get("modules", []),
        "evidence_used": evidence_used,
        "confidence": executed.get("confidence"),
        "evaluation": executed.get("engine_conclusion"),
        "natural_language_response": executed.get("engine_conclusion"),
    }
    return {
        "intent": intent,
        "title": executed.get("title", "Scout response"),
        "engine_conclusion": executed.get("engine_conclusion", "No deterministic evaluation is available."),
        "observed_facts": executed.get("observed_facts", []),
        "known_limitations": executed.get("known_limitations", []),
        "confidence": executed.get("confidence"),
        "cards": executed.get("cards", []),
        "developer": developer,
    }
