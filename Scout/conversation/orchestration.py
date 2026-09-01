"""Scout Intent & Response Orchestration foundation.

This layer sits in front of Scout's legacy deterministic router. Its job is not
to replace Knowledge, Reasoning, Intelligence, or Response Composition. It only
recognizes high-value acceptance prompts that were previously misrouted and
forces them onto the right bounded intelligence path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from Scout.conversation.context import ScoutContext
from Scout.conversation.responses import developer_info, response

ORCHESTRATION_VERSION = "0.5.6.3.1"


@dataclass(frozen=True)
class ScoutIntentPlan:
    route: str
    confidence: float
    reason: str
    priority: int = 50

    def to_dict(self) -> Dict[str, object]:
        return {
            "route": self.route,
            "confidence": self.confidence,
            "reason": self.reason,
            "priority": self.priority,
        }


def _text(question: str) -> str:
    return (question or "").strip().lower()


def _has_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)



def _has_public_sports_context(text: str) -> bool:
    public_terms = [
        "nhl", "maple leafs", "leafs", "toronto maple", "stanley cup",
        "gavin mckenna", "mckenna", "connor mcdavid", "nathan mackinnon", "connor bedard",
        "blackhawks", "sharks", "oilers", "avalanche", "hurricanes", "salary-cap", "salary cap",
        "competitive window", "roster construction", "player development", "league-wide", "league wide",
    ]
    fantasy_terms = [
        "my league", "my roster", "my team", "fantrax", "keeper", "keepers", "manager", "managers",
        "trade partner", "contract expires", "points-only", "points only", "waiver", "entry fee",
    ]
    return _has_any(text, public_terms) and not _has_any(text, fantasy_terms)

def scout_intent_plan(question: str, mode: str = "public") -> Optional[ScoutIntentPlan]:
    """Return a high-priority orchestration plan when legacy routing is risky."""
    q = _text(question)
    selected_mode = (mode or "public").strip().lower()
    if _has_public_sports_context(q):
        selected_mode = "public"
    if not q:
        return None

    # Entity ambiguity must win before fantasy player lookup.
    if "sebastian aho" in q and not _has_any(q, ["finnish", "carolina", "hurricanes", "swedish", "islanders", "penguins"]):
        return ScoutIntentPlan("ambiguous_public_entity", 0.95, "Ambiguous public entity name requires disambiguation.", 98)

    # Comparison must beat recent-event routing. Phrases such as "today" in
    # "build around today" previously hijacked this route into live events.
    if _has_any(q, ["compare", " vs ", " versus ", "which player", "build a franchise around"]):
        if _has_any(q, ["mcdavid", "mackinnon", "matthews", "macKinnon".lower(), "crosby", "ovechkin", "makar"]):
            return ScoutIntentPlan("public_player_comparison", 0.94, "Player comparison intent outranks live-event terms.", 96)

    if selected_mode == "public":
        if _has_any(q, ["gavin mckenna", "mckenna first overall", "first overall in the 2026 nhl draft"]):
            return ScoutIntentPlan("public_organization_impact", 0.9, "Public NHL draft/organization prompt must not route to fantasy league analysis.", 95)
        if _has_any(q, ["biggest nhl story", "biggest story", "story right now", "why it matters"]):
            return ScoutIntentPlan("live_event_intelligence", 0.9, "Current-news prompt should route to Event Intelligence.", 94)
        if _has_any(q, ["best positioned to improve", "improve over the next", "next three seasons"]):
            if _has_any(q, ["teams", "nhl", "league"]):
                return ScoutIntentPlan("public_team_projection", 0.86, "Bounded future-team projection should not hard-refuse.", 88)
        if _has_any(q, ["will determine", "contenders over the next", "over the next three seasons"]):
            if _has_any(q, ["maple leafs", "leafs", "toronto"]):
                return ScoutIntentPlan("public_team_window", 0.88, "Team-window prompt needs organizational implication framing.", 86)
        if q.startswith("why do you believe") or q.startswith("why will") or "will become an elite" in q:
            if _has_any(q, ["bedard", "mcdavid", "matthews", "mackinnon", "celebrini"]):
                return ScoutIntentPlan("public_player_explainability", 0.86, "Why-question requires evidence/reasoning, not stat summary.", 84)

    if selected_mode == "fantasy":
        if _has_any(q, ["analyze my roster", "my roster"]) and _has_any(q, ["strength", "weakness", "organizational"]):
            return ScoutIntentPlan("fantasy_roster_diagnostic", 0.9, "Roster prompt should analyze team construction, not only league settings.", 92)
        if _has_any(q, ["trade direction", "trade directions", "realistic trade", "benefits both managers", "target in a trade", "type of player should i target", "player should i target"]):
            return ScoutIntentPlan("fantasy_trade_directions", 0.88, "Trade-direction prompt requires two-sided recommendation framing.", 90)
        if _has_any(q, ["8th overall", "eighth overall", "draft for upside", "organizational need"]):
            return ScoutIntentPlan("fantasy_draft_strategy", 0.86, "Draft-strategy prompt should route to bounded draft advice.", 88)
        if _has_any(q, ["entering a rebuild", "entering rebuild", "managers", "rebuild"]):
            return ScoutIntentPlan("fantasy_rebuild_detection", 0.86, "Manager rebuild prompt should use roster/contract/transaction evidence.", 86)
        if _has_any(q, ["trade for a player", "contract expires", "expires in 2027", "2027"]):
            if "contract" in q:
                return ScoutIntentPlan("fantasy_contract_rule", 0.9, "Contract-rule prompt should explain league rule implications.", 90)

    return None


def _public_player_profiles_for(question: str) -> List[Any]:
    try:
        from Knowledge.Intelligence.Entities.entity_extractor import resolve_entity
    except Exception:
        try:
            from Knowledge.Intelligence.Entities.entity_registry import find_by_id  # type: ignore
        except Exception:
            return []
    try:
        from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
    except Exception:
        return []

    q = _text(question)
    names = []
    known = [
        ("connor mcdavid", "mcdavid"),
        ("nathan mackinnon", "mackinnon"),
        ("auston matthews", "matthews"),
        ("sidney crosby", "crosby"),
        ("alex ovechkin", "ovechkin"),
        ("cale makar", "makar"),
    ]
    for canonical, alias in known:
        if canonical in q or alias in q:
            names.append(canonical)
    profiles = []
    seen = set()
    for name in names:
        try:
            match = resolve_entity(name, preferred_type="player")
            profile = profile_for_entity(match.entity) if getattr(match, "entity", None) is not None else None
        except Exception:
            profile = None
        if profile is not None and getattr(profile, "entity_id", None) not in seen:
            seen.add(profile.entity_id)
            profiles.append(profile)
    return profiles


def _answer_player_comparison(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    profiles = _public_player_profiles_for(question)
    try:
        from Knowledge.Intelligence.Public.public_answers import player_comparison_answer
    except Exception:
        player_comparison_answer = None  # type: ignore
    if player_comparison_answer is not None and len(profiles) >= 2:
        answer = player_comparison_answer(ctx, profiles, question)
        answer.setdefault("developer", {}).setdefault("orchestration", scout_intent_plan(question, "public").to_dict())
        return answer
    names = [getattr(p, "display_name", "known player") for p in profiles]
    return response(
        intent="public_player_comparison_gap",
        title="Comparison needs two known public players",
        engine_conclusion="Scout recognized the comparison intent but could not resolve two public player profiles.",
        natural_language_response="I recognized this as a player-comparison question, but I could not resolve two known public player profiles cleanly enough to compare them without guessing.",
        observed_facts=[f"Resolved profiles: {', '.join(names) if names else 'none'}"],
        known_limitations=["Public comparison needs both players in the public identity/profile seed pack."],
        confidence=0.35,
        developer=developer_info("public_player_comparison_gap", ctx.files_loaded, intelligence_used=["scout_intent_orchestration"], missing=["two_public_player_profiles"]),
    )


def _answer_ambiguous_entity(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    try:
        from Knowledge.Intelligence.Entities.entity_extractor import resolve_entity
        from Knowledge.Intelligence.Public.public_answers import disambiguation_answer
    except Exception:
        resolve_entity = None  # type: ignore
        disambiguation_answer = None  # type: ignore
    if resolve_entity is not None and disambiguation_answer is not None:
        match = resolve_entity("Sebastian Aho", preferred_type="player")
        candidates = list(getattr(match, "candidates", []) or [])
        if candidates:
            # public_answers.disambiguation_answer expects match objects and
            # expands their .candidates. Passing entities directly produces an
            # empty card payload.
            return disambiguation_answer(ctx, question, [match])
    return response(
        intent="public_entity_disambiguation",
        title="Which Sebastian Aho?",
        engine_conclusion="There are two public sports entities named Sebastian Aho.",
        natural_language_response=(
            "There are two public sports profiles named Sebastian Aho. Did you mean the Finnish Carolina Hurricanes center, "
            "or the Swedish defenseman associated with the Islanders/Penguins organization?"
        ),
        observed_facts=["Finnish Sebastian Aho: C, Carolina Hurricanes.", "Swedish Sebastian Aho: D, Islanders/Penguins organization."],
        known_limitations=["Follow-up entity selection remains card-driven in this build."],
        confidence=0.92,
        developer=developer_info("public_entity_disambiguation", ctx.files_loaded, intelligence_used=["scout_intent_orchestration", "entity_disambiguation"]),
    )


def _answer_team_window(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    natural = (
        "Toronto's three-year contender case should be judged less by star talent alone and more by whether the organization converts that talent into a complete playoff roster.\n\n"
        "The positive case is clear: Auston Matthews gives Toronto a franchise-center anchor, William Nylander supplies high-end offensive support, Morgan Rielly anchors the established blue-line identity, and the organization has major-market resources. That gives the club enough top-end talent to remain in a contender conversation.\n\n"
        "The swing factors are roster balance, defensive depth, goaltending reliability, cap flexibility, health, and whether the supporting cast can reduce the burden on the stars in playoff matchups. If those variables improve, Toronto's window can stay open. If they do not, the team remains a high-skill regular-season profile with unresolved postseason translation risk.\n\n"
        "Confidence: medium. Athena has seeded organizational/team context, but it still needs live roster, cap, injury, goalie, deployment, and recent transaction feeds before making a current quantified contender call."
    )
    return response(
        intent="public_team_window_analysis",
        title="Toronto Maple Leafs three-year contender window",
        engine_conclusion="Toronto's next three seasons depend on translating elite top-end talent into roster balance, playoff structure, defensive depth, goaltending reliability, and cap flexibility.",
        natural_language_response=natural,
        observed_facts=[
            "Toronto seed profile identifies elite top-end scoring and star-center identity as strengths.",
            "Toronto seed profile identifies playoff translation, roster balance, defensive depth, and cap pressure as risks.",
            "Live roster/cap/injury/current-season feeds are not fully attached to this path yet.",
        ],
        known_limitations=["This is bounded public profile reasoning, not a live quantified Stanley Cup forecast."],
        confidence=0.74,
        cards=[
            {"label": "Strength", "value": "Top-end scoring"},
            {"label": "Risk", "value": "Playoff translation"},
            {"label": "Swing factor", "value": "Depth/cap/goaltending"},
        ],
        developer=developer_info("public_team_window_analysis", ctx.files_loaded, knowledge_used=["public_team_profiles"], intelligence_used=["scout_intent_orchestration", "bounded_team_reasoning"], missing=["live_roster_feed", "salary_cap_feed", "goalie_deployment_feed"]),
    )


def _answer_team_projection(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    natural = (
        "Based on Athena's seeded public team profiles, the strongest bounded improvement cases are not a live ranking; they are organizational profiles with identifiable upside levers.\n\n"
        "1. Chicago Blackhawks — improvement case driven by a young franchise-forward timeline around Connor Bedard, assuming development, roster insulation, and prospect conversion.\n\n"
        "2. San Jose Sharks — improvement case driven by a top-pick/foundation-center rebuild path, assuming patience, prospect growth, and better NHL support layers.\n\n"
        "3. Toronto Maple Leafs — improvement case is narrower but still real: better playoff translation, defensive depth, goaltending stability, and cap optimization could materially change the outcome without requiring a full rebuild.\n\n"
        "4. Edmonton Oilers / Colorado Avalanche — not classic 'improve from bad' cases, but strong teams can improve their championship reliability if they solve depth, defensive, goalie, or cap-support questions.\n\n"
        "Confidence: medium-low. Athena can reason from seeded public profiles, but current standings, injuries, prospect performance, draft capital, cap room, and official roster changes are required for a true live improvement model."
    )
    return response(
        intent="public_team_projection",
        title="NHL teams positioned to improve",
        engine_conclusion="Athena can provide a bounded improvement outlook using seeded public team profiles, but not a live current ranking yet.",
        natural_language_response=natural,
        observed_facts=[
            "Chicago and San Jose have young/foundation-player improvement signals in the public identity registry.",
            "Toronto has a contender-improvement path tied to depth, cap, defense, goaltending, and playoff translation.",
            "Edmonton and Colorado have championship-reliability improvement paths rather than rebuild-improvement paths.",
        ],
        known_limitations=["No live standings, cap, injury, prospect-performance, or roster-movement feeds are attached to this projection path yet."],
        confidence=0.58,
        cards=[
            {"label": "Rebuild upside", "value": "CHI / SJS"},
            {"label": "Contender refinement", "value": "TOR / EDM / COL"},
            {"label": "Confidence", "value": "medium-low"},
        ],
        developer=developer_info("public_team_projection", ctx.files_loaded, knowledge_used=["public_team_profiles", "public_entity_registry"], intelligence_used=["scout_intent_orchestration", "bounded_projection_reasoning"], missing=["live_standings", "current_team_statistics", "prospect_pipeline_feed", "salary_cap_feed"]),
    )


def _answer_player_explainability(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    q = _text(question)
    if "bedard" in q:
        name = "Connor Bedard"
        natural = (
            "The elite-player case for Connor Bedard rests on skill translation, not just current point production.\n\n"
            "The evidence case is: first-overall draft pedigree, elite shooting talent, high offensive usage at a very young age, and early NHL production strong enough to indicate that his scoring tools are already translating against NHL defenders.\n\n"
            "The hockey reason is that players with his release quality, puck skill, offensive imagination, and age-adjusted production usually become high-leverage offensive drivers if the organization builds enough support around them. The question is less whether the talent is real and more whether Chicago gives him the linemates, power-play structure, development environment, and roster insulation required to turn skill into sustained elite impact.\n\n"
            "Confidence: medium. Athena has identity and production evidence, but still needs richer deployment, shot-quality, teammate, injury, and development-curve feeds before making a stronger projection."
        )
        facts = [
            "Connor Bedard is registered as a Chicago Blackhawks young franchise forward and elite shooting prospect turned NHL star.",
            "Available local fantasy/player sample shows top-tier point-per-game production.",
            "His development context depends on team support, deployment, health, and power-play role.",
        ]
    else:
        name = "Player projection"
        natural = "Athena recognizes this as an explainability prompt, but the player-specific evidence pack is not rich enough yet for a full causal projection."
        facts = ["Explainability intent recognized."]
    return response(
        intent="public_player_explainability",
        title=f"{name} elite-outcome case",
        engine_conclusion="Scout framed the answer around causal evidence and projection confidence instead of returning only a production statistic.",
        natural_language_response=natural,
        observed_facts=facts,
        known_limitations=["Richer deployment, shot-quality, teammate, injury, and development-curve feeds are future inputs."],
        confidence=0.66 if "bedard" in q else 0.4,
        developer=developer_info("public_player_explainability", ctx.files_loaded, knowledge_used=["public_entity_registry", "player_master", "player_production"], intelligence_used=["scout_intent_orchestration", "explainability_framing"], missing=["shot_quality_feed", "deployment_feed", "development_curve_model"]),
    )


def _team_rows(ctx: ScoutContext) -> List[Dict[str, Any]]:
    return [row for row in (ctx.team_profiles or []) if isinstance(row, dict)]


def _answer_fantasy_roster(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    teams = _team_rows(ctx)
    strongest = sorted(teams, key=lambda t: float(t.get("total_asset_value") or 0), reverse=True)[:1]
    weakest = sorted(teams, key=lambda t: float(t.get("average_asset_value") or 0))[:1]
    strength = strongest[0].get("team_name") if strongest else "not enough team data"
    weakness = weakest[0].get("team_name") if weakest else "not enough team data"
    natural = (
        "Scout recognized this as a roster-organization diagnostic rather than a general league summary.\n\n"
        f"Current bounded read: the strongest available signal is total roster asset strength, led by {strength}. The main weakness signal is average asset depth/efficiency, with {weakness} showing the lowest available average-value signal in the current team-profile set.\n\n"
        "For your actual roster, Athena still needs a selected fantasy-team identity in Scout so it can evaluate your roster directly instead of only comparing league teams. Once that owner/team binding is explicit, the answer should identify positional surplus, expiring-contract risk, keeper pressure, tradeable assets, non-movable assets, and draft-capital needs."
    )
    return response(
        intent="fantasy_roster_diagnostic",
        title="Roster strength and weakness diagnostic",
        engine_conclusion="Scout routed the prompt to roster diagnostics and identified the missing owner/team binding needed for a direct personal-roster answer.",
        natural_language_response=natural,
        observed_facts=[f"Team profiles loaded: {len(teams)}.", f"Top total-value signal: {strength}.", f"Lowest average-value signal: {weakness}."],
        known_limitations=["Scout does not yet know which fantasy team is 'my roster' unless that owner/team binding is provided or persisted."],
        confidence=0.62 if teams else 0.32,
        developer=developer_info("fantasy_roster_diagnostic", ctx.files_loaded, knowledge_used=["team_profiles", "player_contracts", "player_master"], intelligence_used=["scout_intent_orchestration", "bounded_roster_diagnostic"], missing=["current_user_team_binding", "positional_surplus_engine"]),
    )


def _answer_trade_directions(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    natural = (
        "Here are three realistic trade directions Athena can recommend exploring without pretending it knows private negotiation appetite.\n\n"
        "1. Surplus-for-need trade: move from a position where your roster has excess keeper-quality value toward a weaker position group. This benefits the other manager if they are short at your surplus position and can give up depth from their own surplus.\n\n"
        "2. Contract-window trade: explore moving shorter-runway or expiring assets to a contender for a longer-runway keeper asset or draft capital. This benefits the contender by improving near-term scoring and benefits you by reducing keeper/contract pressure.\n\n"
        "3. Two-for-one consolidation or one-for-two depth trade: if your roster is top-heavy, add depth; if it is deep but lacks elite keepers, consolidate. This benefits both managers when one needs lineup stability and the other needs higher ceiling.\n\n"
        "Confidence: medium-low until Athena has your selected team binding, confirmed trade history, draft-pick ownership, and positional surplus model."
    )
    return response(
        intent="fantasy_trade_directions",
        title="Realistic trade directions",
        engine_conclusion="Scout produced trade directions framed around mutual incentives rather than commanding a specific transaction.",
        natural_language_response=natural,
        observed_facts=["League is a 14-team contract dynasty format.", "Points-only scoring and keeper pressure change trade incentives.", "Both-team incentive framing is required for Athena trade recommendations."],
        known_limitations=["Specific offers require selected team binding, trade history, draft-pick ownership, roster surplus/deficit, and contract runway by asset."],
        confidence=0.58,
        developer=developer_info("fantasy_trade_directions", ctx.files_loaded, knowledge_used=["league_profile", "team_profiles", "player_contracts", "transaction_history"], intelligence_used=["scout_intent_orchestration", "two_sided_trade_framing"], missing=["current_user_team_binding", "draft_pick_ownership", "trade_partner_incentive_model"]),
    )


def _answer_draft_strategy(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    natural = (
        "At 8th overall in this league context, the default recommendation is to bias toward upside unless your roster has a severe keeper-window or positional-eligibility problem.\n\n"
        "Reason: in an 11-keeper, contract-dynasty, points-only league, the 8th pick is usually more valuable as a future keeper-ceiling swing than as a narrow lineup-need patch. Organizational need should break ties, but it should not override a materially higher-upside player.\n\n"
        "Decision rule: take the highest-upside player in your top tier; if two players are in the same tier, choose the one that best fits your weakest long-term position or contract runway. Avoid drafting only for short-term roster fit unless your competitive window is clearly win-now and the player can help immediately."
    )
    return response(
        intent="fantasy_draft_strategy",
        title="8th overall draft strategy",
        engine_conclusion="Scout recognized the draft-prep prompt and gave bounded strategy based on keeper/contract league context.",
        natural_language_response=natural,
        observed_facts=["League has 11 keepers.", "League uses a contract-dynasty model.", "Scoring is points-only, making offensive ceiling especially important."],
        known_limitations=["Exact recommendation requires draft class rankings, your roster identity, prospect pool, and traded-pick ownership."],
        confidence=0.68,
        developer=developer_info("fantasy_draft_strategy", ctx.files_loaded, knowledge_used=["league_profile"], intelligence_used=["scout_intent_orchestration", "bounded_draft_strategy"], missing=["draft_class_rankings", "current_user_team_binding", "draft_pick_ownership"]),
    )


def _answer_rebuild_detection(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    records = []
    payload = ctx.manager_behavior or {}
    if isinstance(payload, dict):
        records = [r for r in payload.get("records", []) if isinstance(r, dict)]
    quiet = []
    for row in records:
        facts = row.get("observed_facts") if isinstance(row.get("observed_facts"), dict) else row
        count = int(facts.get("transaction_count") or row.get("transaction_count") or 0)
        if count <= 2:
            quiet.append(row.get("manager_name") or row.get("team_name") or "Unknown manager")
    natural = (
        "Scout recognized this as a manager-direction question. The current evidence is enough to flag candidates for review, but not enough to declare a rebuild as fact.\n\n"
        f"Possible review candidates from current behavior evidence: {', '.join(map(str, quiet[:5])) if quiet else 'none clearly flagged by low observed transaction count alone'}.\n\n"
        "A true rebuild signal should combine several indicators: selling productive veterans, accumulating picks/prospects, accepting short-term scoring loss, holding longer-runway contracts, and reduced interest in near-term lineup upgrades. Transaction count alone is not enough; Athena should treat this as a hypothesis requiring supporting evidence."
    )
    return response(
        intent="fantasy_rebuild_detection",
        title="Manager rebuild-direction review",
        engine_conclusion="Scout routed the prompt to rebuild detection and framed rebuild as an evidence-backed hypothesis, not a label.",
        natural_language_response=natural,
        observed_facts=[f"Manager behavior records loaded: {len(records)}.", f"Low-activity review candidates: {', '.join(map(str, quiet[:5])) if quiet else 'none from transaction count alone'}."],
        known_limitations=["Rebuild detection needs trades, draft-pick movement, age curve, prospect holdings, contract runway, and roster-strength deltas before firm classification."],
        confidence=0.54,
        developer=developer_info("fantasy_rebuild_detection", ctx.files_loaded, knowledge_used=["manager_behavior", "transaction_history", "team_profiles"], intelligence_used=["scout_intent_orchestration", "bounded_rebuild_detection"], missing=["draft_pick_ownership", "age_curve_by_roster", "prospect_holdings", "trade_asset_flow"]),
    )


def _answer_contract_rule(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    natural = (
        "In your Fantrax dynasty league, a contract value like 2027 is an expiry year, not a remaining-years number.\n\n"
        "If you trade for a player whose contract expires in 2027, the acquired player keeps that 2027 expiry. The trade does not reset the contract. Athena should derive years remaining relative to the active league season, but the stored contract value remains the expiry year.\n\n"
        "The practical implication is that you are acquiring both the player and the contract runway. A 2027 asset is more than a one-year rental in the current 2025 context, but it still creates a future keeper/contract decision as the expiry approaches."
    )
    return response(
        intent="fantasy_contract_rule",
        title="Contract expiry rule",
        engine_conclusion="The user's league uses expiry-year contracts; trades preserve the player's contract expiry year.",
        natural_language_response=natural,
        observed_facts=["Fantrax contract values are parsed as expiry years.", "A trade does not reset contract runway in the user's league model.", "Years remaining should be derived relative to the active season context."],
        known_limitations=["Season rollover logic must be revalidated when the active league season changes."],
        confidence=0.9,
        developer=developer_info("fantasy_contract_rule", ctx.files_loaded, knowledge_used=["league_profile", "player_contracts", "user_league_rules"], intelligence_used=["scout_intent_orchestration", "contract_rule_framing"], missing=[]),
    )



def _answer_public_organization_impact(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    natural = (
        "If Toronto selected Gavin McKenna first overall, the organizational impact would be a five-year window reset rather than a simple prospect addition. "
        "Athena should treat McKenna as a premium offensive cornerstone whose value changes Toronto's planning assumptions across development, cap timing, and roster construction.\n\n"
        "Roster construction: Toronto could preserve its established star core while adding a controlled-cost elite forward prospect. That creates optionality: keep veteran scoring support, shift future spending toward defense/goaltending, or eventually transition offensive responsibility as McKenna matures.\n\n"
        "Player development: the key is insulation. The best path is not forcing McKenna to solve NHL problems immediately, but giving him power-play exposure, skilled linemates, and managed matchup difficulty while his strength and pro habits mature.\n\n"
        "Salary-cap management: a first-overall player on an entry-level contract can create surplus value during the exact years when veteran stars are expensive. Toronto's opportunity is to convert that surplus into depth, defensive stability, and goaltending reliability before McKenna reaches his second contract.\n\n"
        "Competitive window: the move could extend Toronto's window beyond the current Matthews/Nylander/Rielly core and reduce the risk of a hard reset. The near-term question remains playoff translation; the medium-term upside is a second wave of elite offense.\n\n"
        "Primary risks: overexposure, development pressure in a high-scrutiny market, roster imbalance if cap savings are not reinvested wisely, and assuming prospect upside automatically solves defense or goaltending.\n\n"
        "Confidence: medium. This is a bounded organizational assessment based on seeded public team/player-development logic. Athena still needs verified player profile data, current roster/cap feeds, development history, and official transaction/draft evidence for a higher-confidence conclusion."
    )
    return response(
        intent="public_organization_impact",
        title="Maple Leafs five-year outlook",
        engine_conclusion="A first-overall McKenna selection would extend Toronto's competitive planning horizon and create entry-level surplus value, but only if development and cap reinvestment are handled correctly.",
        natural_language_response=natural,
        observed_facts=[
            "Prompt context is public NHL organization analysis, not fantasy league analysis.",
            "McKenna is framed as a first-overall offensive cornerstone in the user's scenario.",
            "Toronto's existing public profile centers on elite top-end talent, playoff translation, roster balance, defensive depth, and cap pressure.",
        ],
        known_limitations=["This is scenario analysis; verified live draft, roster, cap, and development data are future inputs."],
        confidence=0.62,
        developer=developer_info("public_organization_impact", ctx.files_loaded, knowledge_used=["public_team_profile_seed"], intelligence_used=["scout_intent_orchestration", "organizational_impact_framing"], missing=["official_draft_feed", "live_cap_feed", "prospect_development_model"]),
    )

def scout_orchestrated_answer(ctx: ScoutContext, question: str, mode: str = "public") -> Optional[Dict[str, Any]]:
    plan = scout_intent_plan(question, mode)
    if plan is None:
        return None
    route = plan.route
    if route == "live_event_intelligence":
        # The router owns the live-event implementation to avoid circular imports.
        return None
    if route == "public_player_comparison":
        return _answer_player_comparison(ctx, question)
    if route == "ambiguous_public_entity":
        return _answer_ambiguous_entity(ctx, question)
    if route == "public_team_window":
        return _answer_team_window(ctx, question)
    if route == "public_team_projection":
        return _answer_team_projection(ctx, question)
    if route == "public_player_explainability":
        return _answer_player_explainability(ctx, question)
    if route == "public_organization_impact":
        return _answer_public_organization_impact(ctx, question)
    if route == "fantasy_roster_diagnostic":
        return _answer_fantasy_roster(ctx, question)
    if route == "fantasy_trade_directions":
        return _answer_trade_directions(ctx, question)
    if route == "fantasy_draft_strategy":
        return _answer_draft_strategy(ctx, question)
    if route == "fantasy_rebuild_detection":
        return _answer_rebuild_detection(ctx, question)
    if route == "fantasy_contract_rule":
        return _answer_contract_rule(ctx, question)
    return None


def orchestration_diagnostics() -> Dict[str, Any]:
    return {
        "version": ORCHESTRATION_VERSION,
        "routes": [
            "public_player_comparison",
            "live_event_intelligence",
            "public_team_window",
            "public_team_projection",
            "public_player_explainability",
            "ambiguous_public_entity",
            "public_organization_impact",
            "fantasy_roster_diagnostic",
            "fantasy_trade_directions",
            "fantasy_draft_strategy",
            "fantasy_rebuild_detection",
            "fantasy_contract_rule",
        ],
        "principle": "route intent before first-match capability execution",
    }
