"""Athena-owned executable capability handlers.

Scout may expose compatibility facades, but executable specialist implementation
is owned here at the Athena boundary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from Scout.conversation.context import ScoutContext
from Scout.conversation.responses import developer_info, response

ORCHESTRATION_VERSION = "0.7.7.0.11"


from Athena.intent_planner import (
    AthenaIntentPlan as ScoutIntentPlan,
    _text, _has_any, _has_public_sports_context,
    _public_player_subjects_for, _public_player_profiles_for,
    comparison_semantics, plan_capability,
)


def scout_intent_plan(question: str, mode: str = "public") -> Optional[ScoutIntentPlan]:
    """Compatibility facade for Scout callers; Athena owns the plan."""
    return plan_capability(question, mode)


def _answer_player_temporal_comparison(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    from Athena.Inquiry.state import build_inquiry_state
    inquiry=build_inquiry_state(question,"public")
    profiles = _public_player_profiles_for(question)
    if len(profiles) != 1:
        from Athena.public_identity import resolve_public_player
        from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
        match = resolve_public_player(question)
        resolved = profile_for_entity(match.entity) if match is not None and match.entity is not None else None
        if resolved is not None: profiles = [resolved]
    if len(profiles) != 1: return _answer_player_comparison(ctx, question)
    from Knowledge.Intelligence.Entities.entity_registry import find_by_id
    from Knowledge.Intelligence.Public.player_evidence import player_evidence
    profile=profiles[0]; entity=find_by_id(profile.entity_id)
    evidence=player_evidence(profile.display_name,team=profile.team,position=profile.position,birth_date=entity.birth_date if entity else "")
    statistical=evidence.get("statistical_evidence",{}) if isinstance(evidence.get("statistical_evidence"),dict) else {}
    seasons=[row for row in statistical.get("season_series",evidence.get("season_history",[])) if isinstance(row,dict) and isinstance(row.get("gp"),(int,float)) and row["gp"]>0 and isinstance(row.get("points"),(int,float))]
    requested=inquiry.temporal_scope.value if inquiry.temporal_scope.kind in {"season_window","career_opening_window"} else None
    if inquiry.temporal_scope.kind=="career": requested=len(seasons)
    selected=(list(reversed(seasons))[:requested] if inquiry.temporal_scope.kind=="career_opening_window" and requested else seasons[:requested] if requested else seasons[:3])
    missing_count=max((requested or 0)-len(selected),0)
    if selected:
        facts=[f"{row['season']}: {row['points']} points in {row['gp']} NHL games." for row in selected]
        if requested:
            coverage=(f"The requested window is complete in current evidence." if not missing_count else f"The current evidence is short by {missing_count} season(s); Athena should acquire the missing history before treating the window as complete.")
            season_lines=" ".join(f"{row['season']}: {row['points']} points in {row['gp']} games ({row['points']/row['gp']:.2f} P/GP)." for row in selected)
            rates=[row['points']/row['gp'] for row in selected]
            trend_note=""
            if len(rates) >= 2:
                hi=max(range(len(rates)), key=lambda i: rates[i]); lo=min(range(len(rates)), key=lambda i: rates[i])
                trend_note=f" Within this window, the highest scoring rate is {selected[hi]['season']} at {rates[hi]:.2f} P/GP and the lowest is {selected[lo]['season']} at {rates[lo]:.2f} P/GP; the current-season sample is only {selected[0]['gp']} games."
            narrative=(f"{profile.display_name} has {len(selected)} verified NHL season records in the requested {inquiry.temporal_scope.label} window. {coverage} " + season_lines + trend_note)
        else:
            latest=selected[0]; narrative=f"{profile.display_name}'s recent verified NHL evidence begins with {latest['points']} points in {latest['gp']} games in {latest['season']}."
        confidence=.82 if not missing_count else .58
    else:
        facts=[]; narrative=f"I can identify {profile.display_name}, but verified NHL season evidence is unavailable for the requested window."; confidence=.35
    limitations=["Scoring rate alone does not establish why performance changed."]
    if missing_count: limitations.append(f"Requested {requested} seasons; only {len(selected)} are currently verified in canonical statistical evidence.")
    answer=response(intent="public_player_temporal_comparison",title=f"{profile.display_name}: {inquiry.temporal_scope.label if inquiry.temporal_scope.source=='user' else 'recent production'}",engine_conclusion=narrative,natural_language_response=narrative,observed_facts=facts,known_limitations=limitations,confidence=confidence,developer=developer_info("public_player_temporal_comparison",getattr(ctx,"files_loaded",[]),knowledge_used=["canonical_player_statistical_evidence"],intelligence_used=["temporal_scope","season_window_selection"],missing=(["missing_requested_season_history"] if missing_count else [])))
    answer["developer"]["comparison_semantics"]=comparison_semantics(question); answer["developer"]["subject_entity_id"]=profile.entity_id; answer["developer"]["inquiry_state"]=inquiry.to_dict(); answer["developer"]["requested_seasons"]=requested; answer["developer"]["available_selected_seasons"]=len(selected)
    return answer


def _answer_player_comparison(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    subjects = _public_player_subjects_for(question)
    profiles = [item.get("profile") for item in subjects if item.get("kind") == "profile" and item.get("profile") is not None]
    if not subjects:
        profiles = _public_player_profiles_for(question)
        subjects = [{"kind":"profile","name":getattr(p,"display_name","known player"),"profile":p} for p in profiles]
    try:
        from Knowledge.Intelligence.Public.public_answers import player_comparison_answer
    except Exception:
        player_comparison_answer = None  # type: ignore
    if player_comparison_answer is not None and len(profiles) >= 2:
        answer = player_comparison_answer(ctx, profiles, question)
        answer.setdefault("developer", {}).setdefault("orchestration", scout_intent_plan(question, "public").to_dict())
        return answer
    if len(subjects) >= 2:
        left, right = subjects[0], subjects[1]
        def subject_fact(item: Dict[str, Any]) -> str:
            if item.get("kind") == "profile":
                profile = item.get("profile")
                summary = str(getattr(profile, "career_identity", "") or getattr(profile, "summary", "") or "mature public profile available")
                return f"{item.get('name')}: {summary}"
            lifecycle = item.get("lifecycle") or {}
            state = str(lifecycle.get("lifecycle_state") or "current player").replace("_", " ")
            detail = ", ".join(x for x in [str(lifecycle.get("position") or "").strip(), str(lifecycle.get("team") or "").strip()] if x and x not in {"(N/A)", "N/A"})
            return f"{item.get('name')}: {state}" + (f" ({detail})" if detail else "")
        def subject_context(item: Dict[str, Any]) -> Dict[str, str]:
            if item.get("kind") == "profile":
                profile=item.get("profile")
                return {"position":str(getattr(profile,"position","") or ""), "team":str(getattr(profile,"team","") or ""), "draft":str(getattr(profile,"draft","") or ""), "stage":"established NHL player"}
            lc=item.get("lifecycle") or {}
            return {"position":str(lc.get("position") or ""), "team":str(lc.get("team") or ""), "draft":str(lc.get("draft") or ""), "stage":str(lc.get("lifecycle_state") or "prospect").replace("_"," ")}
        lcxt, rcxt = subject_context(left), subject_context(right)
        intersections=[]
        if "1st overall" in lcxt["draft"].lower() and "1st overall" in rcxt["draft"].lower():
            intersections.append("Both are supported as 1st-overall draft selections, creating a direct draft-status comparison across career stages.")
        if lcxt["team"] and rcxt["team"] and lcxt["team"] == rcxt["team"]:
            intersections.append(f"Both are tied by current evidence to the same organization ({lcxt['team']}), which makes organizational role and development context directly relevant.")
        if ("toronto maple leafs" in lcxt["draft"].lower() and rcxt["team"] == "TOR") or ("toronto maple leafs" in rcxt["draft"].lower() and lcxt["team"] == "TOR"):
            intersections.append("The evidence also establishes a Toronto first-overall lineage: the established player was drafted 1st overall by Toronto and the younger subject is currently resolved in Toronto's organization.")
        stage_text=f"{left.get('name')} is represented as {lcxt['stage']}; {right.get('name')} is represented as {rcxt['stage']}."
        role_bits=[]
        if lcxt["position"] or rcxt["position"]:
            role_bits.append(f"Position context: {left.get('name')} {lcxt['position'] or 'unknown'}; {right.get('name')} {rcxt['position'] or 'unknown'}.")
        assumptions=[f"I’m treating {item.get('assumed_from')} as {item.get('name')} here; if you meant someone else, I can switch the comparison." for item in (left,right) if item.get('assumed_from')]
        comparison_read = (
            f"{left.get('name')} and {right.get('name')} are at very different career stages, so the useful comparison is established NHL impact versus entry/development trajectory rather than matching mature career totals. "
            + stage_text + " " + " ".join(intersections + role_bits)
        ).strip()
        natural = " ".join(assumptions + [comparison_read])
        facts=[subject_fact(left), subject_fact(right)] + intersections + role_bits
        answer = response(intent="public_player_comparison", title=f"{left.get('name')} vs {right.get('name')}", engine_conclusion=natural, natural_language_response=natural, observed_facts=facts, known_limitations=["Comparison evidence depth differs between the resolved players; missing career statistics or scouting evidence are not inferred.", "Head-to-head, shared-team and cultural relationship evidence remain unavailable unless canonical evidence establishes them."], confidence=0.72, developer=developer_info("public_player_comparison", ctx.files_loaded, intelligence_used=["scout_intent_orchestration","player_lifecycle","comparison_semantics","career_intersection_composition"], missing=["symmetric_public_player_profiles","full_relationship_intelligence"]))
        answer.setdefault("developer", {})["comparison_semantics"] = comparison_semantics(question)
        return answer
    names = [str(item.get("name") or "known player") for item in subjects]
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


def _answer_pre_draft_context(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    from Knowledge.Intelligence.Fantasy.pre_draft_context import build_pre_draft_context
    intel = build_pre_draft_context()
    keeper = intel.get("keeper_state") or {}; capital = intel.get("draft_capital") or {}; available = intel.get("available_pool") or {}; hist = intel.get("historical_context") or {}
    findings = [str(x.get("statement")) for x in (hist.get("findings") or []) if x.get("statement")]
    natural = (f"The current evidence describes a {intel.get('season')} roster snapshot with {keeper.get('rostered_players')} rostered players across {keeper.get('teams_observed')} teams. "
        f"The league allows {keeper.get('expected_keeper_slots')} keeper slots, but this snapshot does not establish the final keeper selections. "
        f"The draft board contains {capital.get('configured_slots')} configured slots across {capital.get('configured_rounds')} rounds, with current ownership ranging from {capital.get('min_owned_slots')} to {capital.get('max_owned_slots')} slots per team. "
        "Those slots are draft capital/capacity, not a prediction that every slot will be exercised. "
        + ("Historical context: " + " ".join(findings) if findings else ""))
    facts=[f"Rostered pre-draft players: {keeper.get('rostered_players')}.",f"Configured current-draft slots: {capital.get('configured_slots')} across {capital.get('configured_rounds')} rounds.",f"Current slot ownership range: {capital.get('min_owned_slots')}–{capital.get('max_owned_slots')} per team.",f"Imported Fantrax snapshot contains {available.get('snapshot_fa_rows')} rows marked FA; current live availability is {'observed' if available.get('live_availability_observed') else 'not established by the synchronized player-pool evidence'}."]+findings
    answer = response(intent="fantasy_pre_draft_context",title=f"{intel.get('season')} pre-draft context",engine_conclusion="Athena combined the current roster snapshot, draft-capital ownership, available-pool evidence, and historical draft intelligence without treating rostered players as confirmed keepers or configured slots as selections.",natural_language_response=natural,observed_facts=facts,known_limitations=list(intel.get('limitations') or []),confidence=0.78,cards=[{"label":"Rostered players","value":keeper.get('rostered_players')},{"label":"Keeper slots","value":keeper.get('expected_keeper_slots')},{"label":"Draft-board slots","value":capital.get('configured_slots')},{"label":"Owned-slot range","value":f"{capital.get('min_owned_slots')}–{capital.get('max_owned_slots')}"}],developer=developer_info("fantasy_pre_draft_context",ctx.files_loaded,knowledge_used=["league_profile","player_pool_master","draft_picks","historical_draft_observations"],intelligence_used=["scout_intent_orchestration","pre_draft_context","historical_draft_intelligence","contextual_followup_generation"],files_read=list(dict.fromkeys(intel.get('files_read') or [])),missing=["keeper_selection_identity","live_free_agent_availability","historical_manager_identity","historical_franchise_continuity"]))
    answer["suggested_prompts"] = ["Where does the draft historically change character by round?", "How uneven is current draft capital across the league?", "What does the current keeper state imply about the available player pool?"] + (["Which historical draft patterns are most relevant to tomorrow's draft?"] if findings else [])
    return answer



def _answer_pre_draft_branch(ctx: ScoutContext, question: str, route: str) -> Dict[str, Any]:
    from Knowledge.Intelligence.Fantasy.pre_draft_context import build_pre_draft_context
    intel = build_pre_draft_context()
    keeper = intel.get("keeper_state") or {}
    capital = intel.get("draft_capital") or {}
    available = intel.get("available_pool") or {}
    hist = intel.get("historical_context") or {}
    findings = [str(x.get("statement")) for x in (hist.get("findings") or []) if isinstance(x, dict) and x.get("statement")]
    common_limits = list(intel.get("limitations") or [])
    if route == "fantasy_keeper_pool_context":
        pressure = (available.get("retention_pressure") or {}) if keeper.get("keeper_selection_established") else {}
        pressure_parts = []
        for pos, row in pressure.items() if isinstance(pressure, dict) else []:
            if not isinstance(row, dict):
                continue
            share = round(float(row.get("retained_share") or 0) * 100, 1)
            live_count = row.get("live_available")
            pressure_parts.append(f"{pos}: {row.get('retained')} retained ({share}% of keeper eligibility), {live_count} live-available observed")
        if available.get("live_availability_observed"):
            availability_sentence = f"Canonical synchronized player-pool evidence currently identifies {available.get('live_available_records')} available/waiver records; the final keeper pool still requires keeper-selection evidence."
        else:
            availability_sentence = "The synchronized player-pool evidence does not currently establish a live available-player population or final keeper selections, so Athena cannot rank current draft-pool scarcity yet."
        natural = (
            f"The current roster snapshot contains {keeper.get('rostered_players')} players across {keeper.get('teams_observed')} teams. "
            f"The league allows {keeper.get('expected_keeper_slots')} keeper slots, but the snapshot does not identify who will be kept or which rostered players will enter the draft pool. "
            + availability_sentence + " "
            f"The imported Fantrax snapshot contains {available.get('snapshot_fa_rows')} rows marked FA, but those rows are contextual snapshot evidence only and are not promoted into a current best-available list."
        )
        facts = [f"Rostered players in current snapshot: {keeper.get('rostered_players')}.", f"Expected keeper slots: {keeper.get('expected_keeper_slots')}."]
        facts.extend(pressure_parts)
        facts.append(f"Imported Fantrax snapshot FA rows: {available.get('snapshot_fa_rows')} (non-authoritative for live availability).")
        title = "Roster snapshot and available player pool"
    elif route == "fantasy_draft_capital_context":
        owners = capital.get("configured_slots_by_current_owner") or {}
        ordered = sorted(owners.items(), key=lambda kv: (-int(kv[1]), str(kv[0]))) if isinstance(owners, dict) else []
        natural = (f"Current draft capital is uneven but bounded: teams hold between {capital.get('min_owned_slots')} and {capital.get('max_owned_slots')} configured slots across {capital.get('configured_rounds')} rounds. "
                   "That distribution describes present pick ownership/capacity, not how many selections each team will ultimately exercise. Teams above the league baseline have more draft optionality; teams below it have less room to add through the current board unless they trade for capital or create roster space.")
        facts = [f"Configured draft slots: {capital.get('configured_slots')}.", f"Ownership range: {capital.get('min_owned_slots')}–{capital.get('max_owned_slots')} slots per team."] + [f"{name}: {count} configured slots." for name,count in ordered]
        title = "Current draft-capital distribution"
    else:
        natural = "Athena's canonical historical draft evidence shows that the draft changes materially by round rather than behaving like one uniform player market. " + (" ".join(findings) if findings else "Round-depth findings are not sufficiently resolved in the current historical evidence.")
        facts = findings or [f"Historical seasons available: {hist.get('season_count') or 0}."]
        title = "Historical draft patterns by round"
    answer = response(intent=route,title=title,engine_conclusion=natural,natural_language_response=natural,observed_facts=facts,known_limitations=common_limits,confidence=0.88,developer=developer_info(route,ctx.files_loaded,knowledge_used=["league_profile","player_pool_master","draft_picks","historical_draft_observations"],intelligence_used=["pre_draft_context","historical_draft_intelligence","contextual_followup_execution"],files_read=list(dict.fromkeys(intel.get("files_read") or [])),missing=["live_free_agent_availability","historical_manager_identity","historical_franchise_continuity"]))
    answer["normal_detail"] = True
    return answer

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


def _answer_longitudinal_draft(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    try:
        from Knowledge.LeagueHistory.evidence_registry import discover_historical_evidence
        evidence = discover_historical_evidence("draft_results")
    except Exception as exc:
        evidence = {"status": "missing", "seasons": [], "error": type(exc).__name__}
    seasons = list(evidence.get("seasons") or [])
    if not seasons:
        return response(
            intent="fantasy_longitudinal_draft",
            title="Historical draft evidence unavailable",
            engine_conclusion="Scout recognized the longitudinal draft question, but no canonical historical draft evidence is currently available to analyze.",
            natural_language_response="I recognized this as a multi-season league draft question, but I do not have canonical historical draft records available in this runtime, so I will not reconstruct or guess the history.",
            observed_facts=[], known_limitations=["Canonical historical draft evidence is missing from this runtime."], confidence=0.35,
            developer=developer_info("fantasy_longitudinal_draft", ctx.files_loaded, knowledge_used=["historical_evidence_registry"], intelligence_used=["scout_intent_orchestration"], files_read=[], missing=["historical_draft_results"]),
        )
    first, last = seasons[0], seasons[-1]
    selection_values = [int(item.get("selections") or 0) for item in seasons]
    slot_values = [int(item.get("configured_slots") or 0) for item in seasons]
    high = max(seasons, key=lambda item: int(item.get("selections") or 0))
    low = min(seasons, key=lambda item: int(item.get("selections") or 0))
    distinct_slots = sorted(set(slot_values))
    facts = [f"{item['season']}: {item['selections']} actual selections from {item['configured_slots']} configured slots." for item in seasons]
    identity_seasons = [item for item in seasons if item.get("identity_available")]
    resolved_team_names = sum(int(item.get("resolved_team_names") or 0) for item in seasons)
    resolved_player_names = sum(int(item.get("resolved_player_names") or 0) for item in seasons)
    resolved_positions = sum(int(item.get("resolved_positions") or 0) for item in seasons)
    total_selections = sum(selection_values)
    identity_text = (
        f" Same-season identity enrichment is available for {len(identity_seasons)} seasons: team names resolve for {resolved_team_names} selection observations, "
        f"positions for {resolved_positions}/{total_selections}, and player names for {resolved_player_names}/{total_selections}. "
        "Manager/person identity and cross-season franchise continuity remain unresolved because the acquired evidence does not establish them."
        if identity_seasons else
        " Historical player, position, franchise, and manager identity still needs same-season resolution before I can responsibly attribute these changes to particular managers or drafting preferences."
    )
    try:
        from Knowledge.Intelligence.Fantasy.historical_draft import build_historical_draft_intelligence
        draft_intelligence = build_historical_draft_intelligence()
    except Exception:
        draft_intelligence = {"status": "missing", "findings": [], "files_read": []}
    findings = list(draft_intelligence.get("findings") or [])
    supported_statements = [str(item.get("statement")) for item in findings if item.get("statement")]
    intelligence_text = (" Historical draft intelligence also finds: " + " ".join(supported_statements)) if supported_statements else ""
    natural = (
        f"Athena has canonical draft-result evidence for {len(seasons)} seasons, from {first['season']} through {last['season']}. "
        f"The draft has not produced a constant number of actual selections: the observed range is {low['selections']} in {low['season']} to {high['selections']} in {high['season']}. "
        f"Configured draft size also varied across the record ({', '.join(map(str, distinct_slots))} slots), so Athena should not project today's draft structure backward onto every season."
        + identity_text + intelligence_text
    )
    files = [str(item.get("artifact")) for item in seasons if item.get("artifact")]
    files += [str(item.get("identity_artifact")) for item in seasons if item.get("identity_artifact")]
    files += [str(item.get("enriched_artifact")) for item in seasons if item.get("enriched_artifact")]
    files += [str(item) for item in draft_intelligence.get("files_read", []) if item]
    files = list(dict.fromkeys(files))
    intelligence_available = draft_intelligence.get("status") == "available"
    conclusion = f"Across {len(seasons)} observed seasons, actual draft usage varied materially even when configured draft capacity was similar."
    if supported_statements:
        conclusion += " Position-resolved evidence supports additional league-level round-depth analysis without requiring manager attribution."
    return response(
        intent="fantasy_longitudinal_draft", title=f"League draft history: {first['season']}–{last['season']}",
        engine_conclusion=conclusion,
        natural_language_response=natural, observed_facts=facts + supported_statements,
        known_limitations=["Provider draft state is preserved as provider metadata and is not independently treated as proof of historical completion.", "Manager tendencies require resolved same-season manager identity, and cross-season team tendencies require established franchise continuity.", "Position findings use resolved same-season eligibility evidence; multi-position eligibility is preserved rather than forced into a single position."],
        confidence=0.90 if intelligence_available else 0.88, cards=[{"label":"Seasons","value":len(seasons)}, {"label":"Selection range","value":f"{min(selection_values)}–{max(selection_values)}"}, {"label":"Configured slot sizes","value":", ".join(map(str, distinct_slots))}],
        developer=developer_info("fantasy_longitudinal_draft", ctx.files_loaded, knowledge_used=["historical_evidence_registry", "historical_draft_results"] + (["historical_identity_resolution", "historical_draft_observations"] if identity_seasons else []), intelligence_used=["scout_intent_orchestration", "longitudinal_structural_comparison"] + (["historical_draft_intelligence"] if intelligence_available else []), files_read=files, missing=(["historical_manager_identity", "historical_franchise_continuity"] if identity_seasons else ["historical_team_identity", "historical_manager_identity", "historical_player_identity", "historical_position_context"])),
    )

def scout_orchestrated_answer(ctx: ScoutContext, question: str, mode: str = "public") -> Optional[Dict[str, Any]]:
    """Compatibility entry point; Athena owns the executable handler map."""
    plan = scout_intent_plan(question, mode)
    if plan is None:
        return None
    if plan.route == "live_event_intelligence":
        # Existing router calls its live handler before this entry point.
        return None
    from Athena.execution_registry import execute_specialist
    return execute_specialist(plan.route, ctx, question, mode=mode)


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
            "public_nhl_economic_context",
            "public_nhl_team_economic_state",
            "public_nhl_player_contract",
            "fantasy_longitudinal_draft",
            "fantasy_pre_draft_context",
            "fantasy_keeper_pool_context",
            "fantasy_draft_capital_context",
            "fantasy_historical_draft_context",
            "fantasy_roster_diagnostic",
            "fantasy_trade_directions",
            "fantasy_draft_strategy",
            "fantasy_rebuild_detection",
            "fantasy_contract_rule",
        ],
        "principle": "route intent before first-match capability execution",
    }


def _answer_nhl_economic_context(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    """Explain canonical league-wide economic context without inventing a club ledger."""
    from datetime import date
    from Knowledge.Economics.league_season_context import resolve_league_season_context

    q = _text(question)
    # Explicit season support is intentionally narrow and deterministic.
    season_match = re.search(r"\b(20\d{2})[-/]?(\d{2})\b", q)
    if season_match:
        season = f"{season_match.group(1)}-{season_match.group(2)}"
        economic = resolve_league_season_context(league_year=season)
    else:
        economic = resolve_league_season_context(as_of=date.today())
    upper = economic.upper_limit / 1_000_000
    lower = economic.lower_limit / 1_000_000
    midpoint = economic.midpoint / 1_000_000
    natural = (
        f"For the {economic.league_year} NHL League Year, the canonical Team Payroll Range is "
        f"${lower:.1f}M lower limit, ${midpoint:.1f}M midpoint and ${upper:.1f}M upper limit. "
        f"The rules environment resolved for {economic.as_of} is {economic.cba_label}.\n\n"
        "This is league-wide economic context, not a team cap calculation. Athena does not yet have the "
        "canonical club contract/adjustment ledger required to state a team's actual cap usage from this capability."
    )
    answer = response(
        intent="public_nhl_economic_context", title=f"NHL economic context: {economic.league_year}",
        engine_conclusion=natural, natural_language_response=natural,
        observed_facts=[
            f"Upper Limit: ${upper:.1f}M.", f"Midpoint: ${midpoint:.1f}M.", f"Lower Limit: ${lower:.1f}M.",
            f"CBA environment: {economic.cba_label} ({economic.cba_effective_from} through {economic.cba_effective_to}).",
        ], known_limitations=list(economic.limitations), confidence=0.98,
        developer=developer_info("public_nhl_economic_context", getattr(ctx, "files_loaded", []),
            knowledge_used=["league_season_context", "public_hockey_knowledge"],
            intelligence_used=["effective_dated_context_resolution"], missing=["canonical_team_economic_state"]),
    )
    answer["developer"]["league_season_context"] = economic.to_dict()
    return answer


def _answer_nhl_player_contract(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    """Answer from canonical professional contract evidence, never fantasy contracts."""
    from datetime import date
    from Knowledge.Contracts.player_contract_state import resolve_player_contract_state
    subjects = _public_player_subjects_for(question)
    profile = subjects[0].get("profile") if len(subjects) == 1 and isinstance(subjects[0], dict) else None
    entity_id = str(getattr(profile, "entity_id", "") or "")
    if not entity_id:
        return response(
            intent="public_nhl_player_contract", title="NHL contract evidence needs a player",
            engine_conclusion="Athena could not establish one public NHL player identity for this contract question.",
            natural_language_response="I need one clearly identified NHL player before applying contract evidence.",
            observed_facts=[], known_limitations=["Professional contract evidence cannot be attached to an unresolved player identity."],
            confidence=0.35, developer=developer_info("public_nhl_player_contract", getattr(ctx, "files_loaded", []), missing=["qualified_public_player_identity"]),
        )
    try:
        contract = resolve_player_contract_state(player_entity_id=entity_id, as_of=date.today())
    except LookupError as exc:
        return response(
            intent="public_nhl_player_contract", title="NHL contract evidence gap",
            engine_conclusion=str(exc), natural_language_response=str(exc), observed_facts=[],
            known_limitations=["The canonical NHL contract pack is intentionally incomplete in v0.7.1; absence is not evidence that a player is unsigned."],
            confidence=0.35, developer=developer_info("public_nhl_player_contract", getattr(ctx, "files_loaded", []), missing=["canonical_player_contract_state"]),
        )
    share = contract.cap_share(date.today())
    natural = (
        f"{contract.player_name}'s canonical NHL contract evidence shows a {contract.term_years}-year, "
        f"${contract.total_value / 1_000_000:.1f}M contract with {contract.team_name}, carrying a "
        f"${contract.aav / 1_000_000:.2f}M AAV through {contract.effective_to}. "
        f"At the current league upper limit, that AAV is {share * 100:.2f}% of the NHL cap. "
        "That percentage normalizes the contract to its league economic environment; it is not the club's total cap usage."
    )
    answer = response(
        intent="public_nhl_player_contract", title=f"{contract.player_name}: NHL contract state",
        engine_conclusion=natural, natural_language_response=natural,
        observed_facts=[
            f"Signed: {contract.signed_on}.", f"Effective: {contract.effective_from} through {contract.effective_to}.",
            f"AAV: ${contract.aav / 1_000_000:.2f}M.", f"Current upper-limit share: {share * 100:.2f}%.",
        ], known_limitations=list(contract.limitations), confidence=0.97,
        developer=developer_info("public_nhl_player_contract", getattr(ctx, "files_loaded", []),
            knowledge_used=["canonical_nhl_player_contract_state", "league_season_context"],
            intelligence_used=["effective_dated_contract_resolution", "cap_share_normalization"],
            missing=["canonical_team_economic_state", "complete_registered_spc"]),
    )
    answer["developer"]["player_contract_state"] = contract.to_dict(as_of=date.today())
    answer["developer"]["contract_subject"] = {"entity_id": entity_id, "display_name": contract.player_name}
    return answer


def _answer_nhl_team_economic_state(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    """Team-specific economic state; aggregate output is gated by ledger completeness."""
    from Knowledge.Teams.team_economic_state import resolve_team_economic_state
    from Knowledge.Economics.league_season_context import resolve_league_season_context
    try:
        team = resolve_team_economic_state(team_id="nhl.team.tor" if _has_any(_text(question), ["maple leafs","leafs","toronto"]) else "")
    except LookupError as exc:
        return response(intent="public_nhl_team_economic_state", title="NHL team economic evidence gap",
            engine_conclusion=str(exc), natural_language_response=str(exc), observed_facts=[],
            known_limitations=["Absence of a registered team state is not evidence of cap space or roster status."], confidence=0.35,
            developer=developer_info("public_nhl_team_economic_state", getattr(ctx,"files_loaded",[]), missing=["canonical_team_economic_state"]))
    economic=resolve_league_season_context(league_year=team.league_year)
    covered=team.covered_contracts()
    covered_names=", ".join(c.player_name for c in covered) or "none"
    natural=(
        f"For {team.team_name}, Athena has a canonical {team.league_year} team-state record, but the economic ledger is not complete enough to state actual cap usage or cap space. "
        f"The league upper limit is ${economic.upper_limit/1_000_000:.1f}M. Current canonical professional-contract coverage for this team contains {len(covered)} player contract(s): {covered_names}. "
        f"Roster evidence is currently classified as {team.roster_evidence_status.replace('_',' ')}. "
        "Athena will not add the covered contracts together and present that partial sum as the club's payroll."
    )
    answer=response(intent="public_nhl_team_economic_state", title=f"{team.team_name}: team economic state",
        engine_conclusion=natural, natural_language_response=natural,
        observed_facts=[f"{team.league_year} upper limit: ${economic.upper_limit/1_000_000:.1f}M.",
                        f"Canonical team contract coverage: {len(covered)} player(s): {covered_names}.",
                        f"Roster evidence status: {team.roster_evidence_status}.",
                        f"Aggregate cap usage status: {team.aggregate_cap_usage_status}."],
        known_limitations=list(team.limitations), confidence=0.96,
        developer=developer_info("public_nhl_team_economic_state", getattr(ctx,"files_loaded",[]),
            knowledge_used=["canonical_nhl_team_economic_state","canonical_nhl_player_contract_state","league_season_context"],
            intelligence_used=["team_state_reconciliation","economic_completeness_gate"],
            missing=["complete_registered_spc","complete_current_roster","team_cap_adjustment_ledger"]))
    answer["developer"]["team_economic_state"]=team.to_dict()
    answer["developer"]["league_season_context"]=economic.to_dict()
    return answer


def _answer_nhl_cap_reasoning(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    """Apply executable cap/CBA constraints to canonical NHL team state."""
    from Knowledge.Teams.team_economic_state import resolve_team_economic_state
    from Knowledge.Economics.league_season_context import resolve_league_season_context
    from Reasoning.Cap.cap_reasoning import evaluate_team_cap_state
    try:
        team = resolve_team_economic_state(team_id="nhl.team.tor" if _has_any(_text(question), ["maple leafs","leafs","toronto"]) else "")
    except LookupError as exc:
        return response(intent="public_nhl_cap_reasoning", title="NHL cap reasoning evidence gap",
            engine_conclusion=str(exc), natural_language_response=str(exc), observed_facts=[],
            known_limitations=["Executable cap reasoning requires a canonical team state."], confidence=0.35,
            developer=developer_info("public_nhl_cap_reasoning", getattr(ctx,"files_loaded",[]), missing=["canonical_team_economic_state"]))
    economic = resolve_league_season_context(league_year=team.league_year)
    determination = evaluate_team_cap_state(team, economic)
    covered = team.covered_contracts()
    covered_names = ", ".join(c.player_name for c in covered) or "none"
    natural = determination.explanation + (
        f" Canonical contract coverage currently contains {len(covered)} {team.team_name} player contract(s): {covered_names}. "
        "Athena is applying the cap rules here, not treating those covered contracts as the club's complete payroll."
    )
    answer = response(intent="public_nhl_cap_reasoning", title=f"{team.team_name}: executable cap determination",
        engine_conclusion=natural, natural_language_response=natural,
        observed_facts=[f"Determination: {determination.status}.",
                        f"{team.league_year} Team Payroll Range: ${economic.lower_limit/1_000_000:.1f}M-${economic.upper_limit/1_000_000:.1f}M.",
                        f"CBA environment: {economic.cba_label}.",
                        f"Canonical team contract coverage: {len(covered)} player(s): {covered_names}."],
        known_limitations=[item for item in team.limitations if not ("before the September 29, 2026 regular-season start" in item and __import__("datetime").date.today() >= __import__("datetime").date(2026,9,29))] + ["Special CBA cap treatments are not assumed without canonical factual inputs and applicable provision evidence."],
        confidence=0.97,
        developer=developer_info("public_nhl_cap_reasoning", getattr(ctx,"files_loaded",[]),
            knowledge_used=["canonical_nhl_team_economic_state","canonical_nhl_player_contract_state","league_season_context"],
            intelligence_used=["executable_cap_reasoning","effective_dated_cba_application","economic_completeness_gate"],
            missing=list(determination.unresolved_inputs)))
    answer["developer"]["cap_determination"] = determination.to_dict()
    answer["developer"]["team_economic_state"] = team.to_dict()
    answer["developer"]["league_season_context"] = economic.to_dict()
    return answer


def _transaction_team_id(question: str, inquiry=None) -> str:
    q=_text(question)
    if _has_any(q,["maple leafs","leafs","toronto"]): return "nhl.team.tor"
    if inquiry is None:
        from Athena.Inquiry.state import build_inquiry_state
        inquiry=build_inquiry_state(question, "public")
    if "Toronto Maple Leafs" in getattr(inquiry, "organizations", []): return "nhl.team.tor"
    protected={str(x).casefold() for x in getattr(inquiry, "protected_assets", [])}
    for profile in _public_player_profiles_for(question):
        name=str(getattr(profile,"display_name","") or "").casefold()
        team=str(getattr(profile,"team","") or "").upper()
        if team == "TOR" and (not protected or name in protected or any(p in name or name in p for p in protected)):
            return "nhl.team.tor"
    return ""


def _answer_nhl_organizational_assets(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    """Acquire the organization's current player universe, then classify control separately from location."""
    from Knowledge.Organizations.nhl_roster_evidence import acquire_team_player_evidence
    from Knowledge.Assets.organizational_rights_state import attach_rights_states, transaction_eligible
    org=acquire_team_player_evidence("TOR")
    players=attach_rights_states(list(org.get("roster") or [])+list(org.get("prospects") or []),"TOR")
    controlled=[x for x in players if (x.get("rights_state") or {}).get("control_status")=="controlled"]
    eligible=[x for x in controlled if transaction_eligible(x)]
    q=_text(question)
    asks_trade=_has_any(q,["trade","traded","tradeable","tradable","could actually be traded","movable"])
    asks_prospects=_has_any(q,["prospect","prospects","development players","young players"])
    selected=eligible if asks_trade else controlled
    if asks_prospects:
        selected=[x for x in selected if str(x.get("relationship") or "")=="prospect" or (isinstance(x.get("age"),int) and x.get("age")<=23)]
    # When the user names multiple organizational assets, compare that requested
    # set rather than widening the answer to every controlled Toronto asset.
    named_selected=[x for x in selected if str(x.get("name") or "").casefold() in q]
    if len(named_selected)>=2:
        selected=named_selected
    asks_reluctance=_has_any(q,["reluctant","reluctance","hardest to move","least willing","would you keep","most protect","significant","significance","differently significant"])
    from Reasoning.Significance import assess_asset_significance, assess_organizational_significance, significance_sort_key
    # Significance must consume the same material player evidence used by deeper
    # transaction investigation. Enrich the requested comparison set before
    # Player Intelligence is built; absence/failure remains explicit rather than
    # silently degrading the player to age + control.
    from Providers.NHL.nhl_client import NHLClient
    client=NHLClient()
    for asset in selected:
        pid=str(asset.get("nhl_player_id") or "")
        if pid:
            try:
                landing=client.get_player_landing(pid)
                if isinstance(landing,dict):
                    d=landing.get("draftDetails") if isinstance(landing.get("draftDetails"),dict) else {}
                    def _int_or_none(v):
                        try:return int(v) if v is not None else None
                        except (TypeError,ValueError):return None
                    asset["draft"]={"year":_int_or_none(d.get("year")),"round":_int_or_none(d.get("round")),"pick_in_round":_int_or_none(d.get("pickInRound")),"overall_pick":_int_or_none(d.get("overallPick")),"team_abbrev":str(d.get("teamAbbrev") or "")}
                    asset["player_landing_acquired"]=True
                    # Reuse the same career observations as the player-development
                    # specialist; no separate Scout interpretation or fabricated cause.
                    from Athena.player_development import _historical_levels
                    asset["development_history"] = _historical_levels(landing)
            except Exception as exc:
                asset.setdefault("enrichment_errors",[]).append(f"player_landing: {type(exc).__name__}: {exc}")
        asset["asset_significance"]=assess_asset_significance(asset)
        asset["organizational_significance"]=assess_organizational_significance(asset,organization="Toronto Maple Leafs")
    reluctance=sorted(selected,key=significance_sort_key,reverse=True) if asks_reluctance else []
    facts=[]
    for x in selected[:20]:
        rs=x.get("rights_state") or {}; obj=str(rs.get("transferable_object") or "unknown")
        facts.append(f"{x.get('name')}: {x.get('relationship')}; control {rs.get('control_status')}; transferable object {obj}; transaction state {rs.get('transaction_status')}.")
    natural=(f"NHL organizational evidence currently identifies {len(controlled)} Toronto-controlled player relationships, with {len(eligible)} eligible for transaction analysis subject to exact contract/rights restrictions. "
             "Athena treats playing location and organizational control separately: a player is not a Toronto trade asset merely because he plays for an affiliate, while a controlled prospect can remain a Toronto asset in junior, college or Europe. "
             "The current provider path does not yet establish every player's exact SPC versus unsigned-rights mechanism or a complete Toronto draft-pick inventory, so those distinctions remain explicit rather than invented.")
    answer=response(intent="public_nhl_organizational_assets",title="Toronto Maple Leafs: organizational asset rights",engine_conclusion=natural,natural_language_response=natural,observed_facts=facts,known_limitations=["Exact rights expiry, SPC clauses, NMC/NTC and other transfer restrictions require the corresponding contract/CBA evidence.","Draft capital is not yet acquired by this organizational-player path.","NHL provider prospect association establishes current organizational relationship but does not by itself identify every underlying rights mechanism."],confidence=.84,developer=developer_info("public_nhl_organizational_assets",getattr(ctx,"files_loaded",[]),knowledge_used=["nhl_current_roster","nhl_prospects","nhl_player_landing","organizational_rights_state"],intelligence_used=["control_vs_location_classification","transaction_eligibility","player_intelligence","asset_significance","organizational_significance"],missing=["complete_exact_rights_mechanisms","nhl_draft_pick_ownership"]))
    answer["developer"]["organizational_assets"]={"team":"TOR","controlled_count":len(controlled),"transaction_analysis_count":len(eligible),"query_subset":"prospects" if asks_prospects else "all_controlled_assets","selected_players":selected,"players":controlled,"reluctance_requested":asks_reluctance,"reluctance_ranking":reluctance,"acquisition_errors":org.get("acquisition_errors") or []}
    return answer

def _answer_nhl_transaction_scenario(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    """Evaluate a bounded NHL transaction hypothetical without mutating canonical state."""
    from Knowledge.Teams.team_economic_state import resolve_team_economic_state
    from Knowledge.Economics.league_season_context import resolve_league_season_context
    from Knowledge.Contracts.player_contract_state import resolve_player_contract_state
    from Reasoning.Transactions.scenario_engine import acquire_contract, release_contract, evaluate_transaction_scenario
    q=_text(question)
    from Athena.Inquiry.state import build_inquiry_state, select_primary_player_subject
    inquiry=build_inquiry_state(question, "public")
    try:
        team=resolve_team_economic_state(team_id=_transaction_team_id(question, inquiry))
    except LookupError as exc:
        return response(intent="public_nhl_transaction_scenario",title="NHL transaction scenario evidence gap",engine_conclusion=str(exc),natural_language_response=str(exc),observed_facts=[],known_limitations=["A canonical team state is required."],confidence=0.35,developer=developer_info("public_nhl_transaction_scenario",getattr(ctx,"files_loaded",[]),missing=["canonical_team_economic_state"]))
    profile=select_primary_player_subject(question, _public_player_profiles_for(question))
    player_id=getattr(profile, "entity_id", "") if profile is not None else ""
    try:
        contract=resolve_player_contract_state(player_entity_id=player_id,as_of=team.as_of)
    except LookupError as exc:
        natural=f"The hypothetical can be discussed, but Athena cannot calculate its contract/cap delta: {exc}"
        return response(intent="public_nhl_transaction_scenario",title=f"{team.team_name}: transaction scenario evidence gap",engine_conclusion=natural,natural_language_response=natural,observed_facts=[],known_limitations=["Scenario cap deltas require canonical professional contract evidence."],confidence=0.45,developer=developer_info("public_nhl_transaction_scenario",getattr(ctx,"files_loaded",[]),missing=["canonical_transaction_contract_evidence"]))
    # Whole-picture investigation: missing local evidence triggers registered NHL acquisition
    # before Athena is allowed to describe roster/player evidence as unavailable.
    from Athena.Investigation.nhl_transaction import investigate_nhl_transaction
    target_team = str(getattr(profile, "team", "") or "")
    investigation = investigate_nhl_transaction(inquiry=inquiry, buyer_abbrev="TOR", target_team_abbrev=target_team or "EDM", target_name=contract.player_name)
    candidates = list(investigation.evidence.get("candidate_assets") or [])
    candidate_names = [str(x.get("name") or "") for x in candidates if str(x.get("name") or "")]
    candidate_text = ", ".join(candidate_names[:5])
    if "salary_cap" in inquiry.constraints_waived:
        from Athena.Inquiry.execution import construct_transaction_paths
        construction = construct_transaction_paths(team_name=team.team_name, target_name=contract.player_name,
                                                   protected_assets=inquiry.protected_assets, cap_waived=True,
                                                   acquisition_price_known=False)
        path_text = " ".join(f"{item['label']}: {item['analysis']}" for item in construction["paths"])
        named = (f" Current NHL evidence gives Athena a non-protected candidate pool led by {candidate_text}. " if candidate_text else " NHL roster/prospect acquisition did not yield a usable named candidate pool, so Athena will not invent one. ")
        natural=(f"For this hypothetical, salary-cap feasibility is explicitly waived. {construction['conclusion']} "
                 f"{named}{path_text} These names are evidence-backed assets to examine, not a claim that Edmonton wants them or that the package is sufficient.")
        observed=[f"Transaction subject: {contract.player_name}.", "Waived constraint: salary cap.",
                  f"Protected assets: {', '.join(inquiry.protected_assets) or 'none specified'}."]
        observed.extend(f"Construction path — {item['label']}: {item['analysis']}" for item in construction["paths"])
        answer=response(intent="public_nhl_transaction_scenario",title=f"{team.team_name}: cap-waived transaction construction",engine_conclusion=natural,natural_language_response=natural,observed_facts=observed,known_limitations=["Athena does not yet have verified acquisition-price or counterparty-willingness evidence, so these are bounded construction paths rather than a claimed sufficient offer.","Waiving a constraint for analysis does not erase the real-world rule."],confidence=.82,developer=developer_info("public_nhl_transaction_scenario",getattr(ctx,"files_loaded",[]),knowledge_used=["canonical_nhl_player_contract_state"],intelligence_used=["inquiry_state","constraint_waiver","adaptive_inquiry_execution","transaction_construction"],missing=["verified_acquisition_price","verified_counterparty_willingness","verified_current_roster_asset_values"]))
        answer["developer"]["inquiry_state"]=inquiry.to_dict(); answer["developer"]["canonical_contract_state"]=contract.to_dict(as_of=team.as_of); answer["developer"]["adaptive_execution"]=construction; answer["developer"]["investigation_state"]=investigation.to_dict()
        return answer
    outgoing = contract.team_id == team.team_id and _has_any(q,["trade away","trade matthews","move matthews","send matthews","deal matthews","lose matthews"])
    op=release_contract(contract) if outgoing else acquire_contract(contract)
    economic=resolve_league_season_context(league_year=team.league_year)
    scenario=evaluate_transaction_scenario(team,economic,scenario_id=f"{team.team_id}:{op.operation}:{contract.player_entity_id}",operations=(op,),assumptions=("No unasserted salary retention or additional transaction components are assumed.",))
    named = (f" NHL roster/prospect acquisition identified non-protected Toronto assets to examine, including {candidate_text}." if candidate_text else " NHL roster/prospect acquisition did not produce a usable named candidate pool.")
    natural=scenario.explanation+f" The evidenced contract used is {contract.player_name} at ${contract.aav/1_000_000:.2f}M AAV.{named} Athena must evaluate why those assets could fit the other organization and why Toronto could rationally surrender them; fit is analysis, not evidence of front-office intent. No salary retention or additional transaction components are assumed unless stated."
    answer=response(intent="public_nhl_transaction_scenario",title=f"{team.team_name}: transaction scenario",engine_conclusion=natural,natural_language_response=natural,observed_facts=[f"Scenario operation: {op.operation} {contract.player_name}.",f"Evidenced cap-charge delta: ${op.cap_charge_delta/1_000_000:+.2f}M.",f"Canonical current state remains unchanged.",f"Scenario cap determination: {scenario.cap_determination.get('status')}."],known_limitations=[item for item in team.limitations if not ("before the September 29, 2026 regular-season start" in item and __import__("datetime").date.today() >= __import__("datetime").date(2026,9,29))]+["A transaction scenario is hypothetical state, not evidence that a transaction occurred.","Retention legality and other special mechanics require separately executable CBA provisions and factual inputs."],confidence=0.96,developer=developer_info("public_nhl_transaction_scenario",getattr(ctx,"files_loaded",[]),knowledge_used=["canonical_nhl_team_economic_state","canonical_nhl_player_contract_state","league_season_context"],intelligence_used=["transaction_scenario_engine","hypothetical_state_isolation","executable_cap_reasoning"],missing=list(scenario.unresolved_inputs)))
    answer["developer"]["transaction_scenario"]=scenario.to_dict(); answer["developer"]["canonical_contract_state"]=contract.to_dict(as_of=team.as_of); answer["developer"]["canonical_team_state_unchanged"]=team.to_dict(); answer["developer"]["investigation_state"]=investigation.to_dict()
    return answer


def _answer_nhl_player_asset_state(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    """Present canonical player/organizational asset state without inventing market value."""
    from datetime import date
    from Knowledge.Assets.player_asset_state import resolve_player_asset_state
    profiles = _public_player_profiles_for(question)
    if len(profiles) != 1:
        return response(intent="public_nhl_player_asset_state", title="NHL player asset state",
                        engine_conclusion="I need one resolved NHL player to build an organizational asset state.",
                        natural_language_response="I need one resolved NHL player to build an organizational asset state.",
                        observed_facts=[], known_limitations=["Player identity is unresolved or ambiguous."], confidence=0.35,
                        developer=developer_info("public_nhl_player_asset_state", getattr(ctx,"files_loaded",[]),
                        knowledge_used=["public_entity_registry"], intelligence_used=["player_asset_state"], missing=["resolved_player_identity"]))
    profile=profiles[0]
    try:
        state=resolve_player_asset_state(player_entity_id=profile.entity_id,as_of=date.today())
    except LookupError as exc:
        text=str(exc)
        return response(intent="public_nhl_player_asset_state", title=f"{profile.display_name}: organizational asset state",
                        engine_conclusion=text,natural_language_response=text,observed_facts=[],
                        known_limitations=[text],confidence=0.4,
                        developer=developer_info("public_nhl_player_asset_state",getattr(ctx,"files_loaded",[]),
                        knowledge_used=["player_asset_state"],intelligence_used=["asset_state_composition"],missing=["canonical_asset_state"]))
    contract_text=(f" His canonical contract evidence carries a ${state.aav/1_000_000:.2f}M AAV through {state.effective_to}"
                   f" ({state.cap_share_of_upper_limit*100:.2f}% of the current league upper limit)." if state.aav else
                   " Canonical professional contract/control evidence is not registered for this player/date.")
    production_text=(f" Canonical statistical evidence is {state.production_freshness}"
                     + (f"; the latest observed season is {state.latest_observed_season}." if state.latest_observed_season else "."))
    conclusion=(f"{state.player_name} is a {state.age}-year-old {state.position} in the {state.career_stage.replace('_',' ')} career stage, "
                f"currently tied by canonical identity evidence to {state.team_id}.{contract_text}{production_text} "
                "Athena is treating these as asset dimensions, not converting them into an unsupported trade-value score.")
    facts=[
        f"Career stage: {state.career_stage.replace('_',' ')}; age {state.age}.",
        f"Organizational relationship: {state.organizational_relationship} ({state.team_id}).",
        f"Evidence dimensions: {', '.join(state.evidence_dimensions)}.",
    ]
    if state.aav: facts.append(f"Canonical contract: ${state.aav/1_000_000:.2f}M AAV through {state.effective_to}.")
    if state.career_totals: facts.append("Canonical career totals are available to the asset-state layer.")
    answer=response(intent="public_nhl_player_asset_state",title=f"{state.player_name}: organizational asset state",
                    engine_conclusion=conclusion,natural_language_response=conclusion,observed_facts=facts,
                    known_limitations=list(state.limitations),confidence=0.84 if state.aav and state.production_authority=="canonical_statistical_evidence" else 0.7,
                    developer=developer_info("public_nhl_player_asset_state",getattr(ctx,"files_loaded",[]),
                    knowledge_used=["public_entity_registry","canonical_player_statistical_evidence","canonical_nhl_contract_state"],
                    intelligence_used=["player_organizational_asset_state"],missing=list(state.missing_dimensions)))
    answer["developer"]["player_asset_state"]=state.to_dict()
    return answer


def _answer_nhl_organizational_plausibility(ctx: ScoutContext, question: str) -> Dict[str, Any]:
    """Assess organizational plausibility without turning contextual fit into claimed intent."""
    from Knowledge.Teams.team_economic_state import resolve_team_economic_state
    from Knowledge.Economics.league_season_context import resolve_league_season_context
    from Knowledge.Contracts.player_contract_state import resolve_player_contract_state
    from Knowledge.Assets.player_asset_state import resolve_player_asset_state
    from Knowledge.Intelligence.Public.public_team_profiles import get_public_team_profile
    from Reasoning.Transactions.scenario_engine import acquire_contract, evaluate_transaction_scenario
    from Reasoning.Organizations.plausibility import assess_organizational_plausibility
    q=_text(question)
    from Athena.Inquiry.state import build_inquiry_state, select_primary_player_subject
    inquiry=build_inquiry_state(question, "public")
    try:
        team=resolve_team_economic_state(team_id=_transaction_team_id(question, inquiry))
    except LookupError as exc:
        text=str(exc)
        return response(intent="public_nhl_organizational_plausibility",title="Organizational plausibility evidence gap",engine_conclusion=text,natural_language_response=text,observed_facts=[],known_limitations=["Canonical team state is required."],confidence=.35,developer=developer_info("public_nhl_organizational_plausibility",getattr(ctx,"files_loaded",[]),missing=["canonical_team_state"]))
    profiles=_public_player_profiles_for(question)
    profile=select_primary_player_subject(question, profiles)
    if profile is None:
        text="I need one resolved NHL transaction subject to assess this organizational scenario."
        return response(intent="public_nhl_organizational_plausibility",title=f"{team.team_name}: plausibility evidence gap",engine_conclusion=text,natural_language_response=text,observed_facts=[],known_limitations=[text],confidence=.35,developer=developer_info("public_nhl_organizational_plausibility",getattr(ctx,"files_loaded",[]),missing=["resolved_player_identity"]))
    try:
        contract=resolve_player_contract_state(player_entity_id=profile.entity_id,as_of=team.as_of)
        asset=resolve_player_asset_state(player_entity_id=profile.entity_id,as_of=team.as_of)
    except LookupError as exc:
        text=f"The organizational scenario can be investigated, but the canonical player/contract state is incomplete: {exc}"
        return response(intent="public_nhl_organizational_plausibility",title=f"{team.team_name}: plausibility evidence gap",engine_conclusion=text,natural_language_response=text,observed_facts=[],known_limitations=[text],confidence=.45,developer=developer_info("public_nhl_organizational_plausibility",getattr(ctx,"files_loaded",[]),missing=["canonical_player_asset_or_contract_state"]))
    economic=resolve_league_season_context(league_year=team.league_year)
    op=acquire_contract(contract)
    scenario=evaluate_transaction_scenario(team,economic,scenario_id=f"{team.team_id}:plausibility:{asset.player_entity_id}",operations=(op,),assumptions=("No unasserted salary retention, outgoing assets or additional transaction components are assumed.",))
    team_profile=get_public_team_profile("nhl.team.toronto_maple_leafs") if team.abbreviation=="TOR" else None
    if team_profile is None:
        text="Canonical economic state exists, but no matching public organizational profile is registered for this team."
        return response(intent="public_nhl_organizational_plausibility",title=f"{team.team_name}: organizational context gap",engine_conclusion=text,natural_language_response=text,observed_facts=[],known_limitations=[text],confidence=.45,developer=developer_info("public_nhl_organizational_plausibility",getattr(ctx,"files_loaded",[]),missing=["public_team_profile"]))
    assessment=assess_organizational_plausibility(team_profile=team_profile,team_state=team,player_asset_state=asset,scenario=scenario)
    from Athena.Inquiry.execution import construct_transaction_paths
    construction=construct_transaction_paths(team_name=team.team_name,target_name=asset.player_name,
                                             protected_assets=inquiry.protected_assets,cap_waived=False,
                                             acquisition_price_known="verified_acquisition_price" not in assessment.unresolved_inputs)
    natural=assessment.explanation
    if assessment.fit_considerations: natural+=" Fit evidence: "+" ".join(assessment.fit_considerations)
    if assessment.friction_considerations: natural+=" Friction: "+" ".join(assessment.friction_considerations)
    natural+=" Construction read: "+construction["conclusion"]+" "+" ".join(f"{item['label']}: {item['analysis']}" for item in construction["paths"])
    answer=response(intent="public_nhl_organizational_plausibility",title=f"{team.team_name} / {asset.player_name}: organizational plausibility",
        engine_conclusion=natural,natural_language_response=natural,observed_facts=list(assessment.established_facts),
        known_limitations=list(assessment.limitations)+list(assessment.hypotheses),confidence=.78,
        developer=developer_info("public_nhl_organizational_plausibility",getattr(ctx,"files_loaded",[]),
        knowledge_used=["canonical_nhl_team_economic_state","player_organizational_asset_state","public_team_profile","canonical_nhl_player_contract_state"],
        intelligence_used=["organizational_plausibility","transaction_scenario_engine","executable_cap_reasoning","adaptive_inquiry_execution","transaction_construction"],
        missing=list(assessment.unresolved_inputs)))
    answer["developer"]["organizational_plausibility"]=assessment.to_dict()
    answer["developer"]["transaction_scenario"]=scenario.to_dict()
    answer["developer"]["inquiry_state"]=inquiry.to_dict()
    answer["developer"]["adaptive_execution"]=construction
    return answer
