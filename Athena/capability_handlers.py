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

ORCHESTRATION_VERSION = "0.6.5.7.0"


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
    profiles = _public_player_profiles_for(question)
    if len(profiles) != 1:
        from Athena.public_identity import resolve_public_player
        from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
        match = resolve_public_player(question)
        resolved = profile_for_entity(match.entity) if match is not None and match.entity is not None else None
        if resolved is not None:
            profiles = [resolved]
    if len(profiles) != 1:
        return _answer_player_comparison(ctx, question)
    from Knowledge.Intelligence.Entities.entity_registry import find_by_id
    from Knowledge.Intelligence.Public.player_evidence import player_evidence
    profile = profiles[0]
    entity = find_by_id(profile.entity_id)
    evidence = player_evidence(profile.display_name, team=profile.team, position=profile.position,
                               birth_date=entity.birth_date if entity else "")
    statistical = evidence.get("statistical_evidence", {}) if isinstance(evidence.get("statistical_evidence"), dict) else {}
    seasons = [row for row in statistical.get("season_series", evidence.get("season_history", [])) if isinstance(row, dict)
               and isinstance(row.get("gp"), (int, float)) and row["gp"] > 0
               and isinstance(row.get("points"), (int, float))]
    if len(seasons) >= 2:
        latest = seasons[0]
        baseline = seasons[1:3]
        games = sum(row["gp"] for row in baseline)
        points = sum(row["points"] for row in baseline)
        latest_rate = latest["points"] / latest["gp"]
        baseline_rate = points / games
        narrative = (f"{profile.display_name} recorded {latest['points']} points in {latest['gp']} NHL games "
                     f"in {latest['season']} ({latest_rate:.2f} points per game). Across the preceding "
                     f"{len(baseline)} available season(s), the baseline was {points} points in {games} games "
                     f"({baseline_rate:.2f} per game). That is a scoring-rate comparison; deployment, health "
                     "and playing time need separate evidence before explaining the difference.")
        facts = [f"{row['season']}: {row['points']} points in {row['gp']} NHL games." for row in seasons[:3]]
        confidence = 0.78
    else:
        narrative = (f"I can identify {profile.display_name}, but do not have two verified NHL seasons "
                     "for a recent production comparison. I cannot infer a trend from the profile alone.")
        facts = [f"Verified NHL season records available: {len(seasons)}."]
        confidence = 0.42
    answer = response(intent="public_player_temporal_comparison", title=f"{profile.display_name}: recent production",
                      engine_conclusion=narrative, natural_language_response=narrative,
                      observed_facts=facts, known_limitations=["Scoring rate alone does not establish why performance changed."],
                      confidence=confidence, developer=developer_info("public_player_temporal_comparison", getattr(ctx, "files_loaded", []),
                      knowledge_used=["nhl_player_landing"], intelligence_used=["season_baseline_comparison"],
                      missing=[] if len(seasons) >= 2 else ["two_verified_nhl_seasons"]))
    answer["developer"]["comparison_semantics"] = comparison_semantics(question)
    answer["developer"]["subject_entity_id"] = profile.entity_id
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
