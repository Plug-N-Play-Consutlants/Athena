"""Athena-owned capability planning and public player subject resolution.

Scout may describe intent and present results, while Athena selects registered
capabilities from the public identity graph and the current request. Existing
Scout callers use a thin compatibility wrapper around this planner.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class AthenaIntentPlan:
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

def _public_player_subjects_for(question: str) -> List[Dict[str, Any]]:
    """Resolve comparison subjects from mature profiles or lifecycle evidence."""
    try:
        from Knowledge.Intelligence.Entities.entity_extractor import split_entity_phrases, resolve_entity
        from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
        from Knowledge.Intelligence.Public.player_lifecycle import resolve_player_lifecycle
    except Exception:
        return [{"kind": "profile", "name": getattr(p, "display_name", ""), "profile": p} for p in _public_player_profiles_for(question)]
    subjects, seen = [], set()
    # Preserve explicit two-sided comparison subjects even when a legacy entity
    # splitter consumes only the mature-profile side. This is syntax-level
    # recovery, not a player-specific exception.
    explicit_phrases = []
    parts = re.split(r"\s+(?:vs\.?|versus)\s+", question or "", maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        explicit_phrases = [re.sub(r"^(?:compare\s+)?", "", part, flags=re.IGNORECASE).strip(" ?.,") for part in parts]
    # Preserve mature profile discovery across natural-language clauses, then
    # enrich unresolved comparison phrases through lifecycle evidence.
    for profile in _public_player_profiles_for(question):
        name = str(getattr(profile, "display_name", "") or "known player")
        key = name.lower()
        if key not in seen:
            seen.add(key); subjects.append({"kind":"profile","name":name,"profile":profile})
    phrases = list(explicit_phrases) + list(split_entity_phrases(question))
    for phrase in phrases:
        cleaned = phrase.strip()
        if not cleaned:
            continue
        # A natural-language question is not a person identity. Discovery may
        # find a headline containing the whole query, but headline coincidence
        # cannot establish that the query itself names a player.
        lowered_cleaned = cleaned.casefold()
        question_starters = ("what ", "what's ", "who ", "who's ", "why ", "how ", "when ", "where ", "which ", "explain ", "define ", "tell me ")
        if lowered_cleaned.startswith(question_starters) or cleaned.endswith("?"):
            continue
        profile = None
        try:
            match = resolve_entity(cleaned, preferred_type="player")
            if getattr(match, "confidence", 0.0) >= 0.9 and getattr(match, "entity", None) is not None:
                profile = profile_for_entity(match.entity)
        except Exception:
            pass
        if profile is not None:
            name = str(getattr(profile, "display_name", cleaned)); key = name.lower()
            if key not in seen:
                seen.add(key); subjects.append({"kind":"profile","name":name,"profile":profile})
            continue
        try:
            lifecycle = resolve_player_lifecycle(cleaned, allow_network=False)
        except Exception:
            lifecycle = {}
        assumed_from = ""
        # A short surname/alias should not force clarification when current local
        # identity evidence yields one unambiguous player. This is generic local
        # identity resolution, not a player-specific alias table.
        if lifecycle.get("status") != "available" and len(cleaned.split()) == 1:
            try:
                from Knowledge.Intelligence.Public.player_lifecycle import contextual_local_player_candidate
                candidate = contextual_local_player_candidate(cleaned)
            except Exception:
                candidate = ""
            if candidate:
                assumed_from = cleaned
                try:
                    lifecycle = resolve_player_lifecycle(candidate, allow_network=False)
                except Exception:
                    lifecycle = {}
        if lifecycle.get("status") == "available":
            name = str(lifecycle.get("name") or cleaned); key = name.lower()
            if key not in seen:
                seen.add(key); subjects.append({"kind":"lifecycle","name":name,"lifecycle":lifecycle,"assumed_from":assumed_from})
    return subjects


def comparison_semantics(question: str) -> Dict[str, object]:
    """Classify comparison shape without embedding sport-specific relationship logic.

    Relationship evidence is a general entity-to-entity concern. NHL is the first
    domain expected to populate it, while the contract remains reusable by other
    sports and entity types.
    """
    q = _text(question)
    subjects = _public_player_subjects_for(question)
    if not subjects:
        subjects = [{"kind":"profile","name":getattr(p,"display_name", ""),"profile":p} for p in _public_player_profiles_for(question)]
    entity_count = len(subjects)
    temporal = entity_count == 1 and _has_any(q, [
        "career baseline", "recent baseline", "historical baseline", "current production",
        "recent career", "compared with his", "compared with her", "compare with his", "compare with her",
        "over the last", "over the past", "last 2 seasons", "last 3 seasons", "last two seasons", "last three seasons",
        "past 2 seasons", "past 3 seasons", "past two seasons", "past three seasons", "changed over", "change over",
    ])
    relationship = entity_count >= 2 and _has_any(q, [
        "against one another", "against each other", "head to head", "head-to-head",
        "played together", "play together", "teammates", "train together", "relationship",
    ])
    kind = "temporal" if temporal else ("relationship" if relationship else ("entity" if entity_count >= 2 else "unresolved"))
    return {
        "class": kind,
        "entity_count": entity_count,
        "relationship_contract": {
            "sport_neutral": True,
            "evidence_classes": ["opponents", "teammates", "shared_events", "organizational_overlap", "head_to_head_performance", "career_intersections", "documented_connections", "cultural_media_intersections"],
            "first_domain": "NHL",
            "implementation_status": "foundation_only",
        },
    }


def plan_capability(question: str, mode: str = "public") -> Optional[AthenaIntentPlan]:
    """Return a high-priority orchestration plan when legacy routing is risky."""
    q = _text(question)
    selected_mode = (mode or "public").strip().lower()
    if _has_public_sports_context(q):
        selected_mode = "public"
    if not q:
        return None

    # Inquiry State is the canonical semantic interpretation. The planner may
    # still use raw text for specialist-specific modifiers, but must not
    # maintain a competing transaction grammar.
    try:
        from Athena.Inquiry.state import build_inquiry_state
        inquiry = build_inquiry_state(question, selected_mode)
    except Exception:
        inquiry = None

    # Entity ambiguity must win before fantasy player lookup.
    if "sebastian aho" in q and not _has_any(q, ["finnish", "carolina", "hurricanes", "swedish", "islanders", "penguins"]):
        return AthenaIntentPlan("ambiguous_public_entity", 0.95, "Ambiguous public entity name requires disambiguation.", 98)

    # Comparison semantics are intentionally split. A single player's current
    # production vs a career/recent baseline is temporal comparison, not a
    # request to resolve a second player. Entity-vs-entity comparison requires
    # two resolved/mentioned player identities. Relationship investigation is
    # reserved as a sport-neutral future evidence contract.
    comparison_players = _public_player_subjects_for(question) or [{"kind":"profile","profile":p} for p in _public_player_profiles_for(question)]
    comparison_shape = comparison_semantics(question)
    temporal_comparison = comparison_shape["class"] == "temporal"
    if temporal_comparison:
        return AthenaIntentPlan("public_player_temporal_comparison", 0.95, "Single-player baseline comparison is temporal, not entity-vs-entity.", 97)
    if len(comparison_players) >= 2 and _has_any(q, ["compare", " vs ", " versus ", "which player", "build a franchise around"]):
        return AthenaIntentPlan("public_player_comparison", 0.94, "Two-player comparison intent outranks live-event terms.", 96)

    if selected_mode == "public":
        # Development/projection is an analytical inquiry even when it mentions
        # college, the current season, or roster opportunity. News is supplementary.
        development_terms = ("development pathway", "development ahead", "late-develop",
                             "late developing", "late compared", "nhl debut",
                             "made the nhl at", "reach the nhl", "never reach the nhl",
                             "development trajectory", "development projection")
        analytical_terms = ("compared with relevant prospects", "project about him",
                            "prospect attainment", "drafted players who never",
                            "college pathway", "ahl pathway")
        if (_has_any(q, development_terms) or _has_any(q, analytical_terms)) and _has_any(
            q, ("nhl", "prospect", "player", "ahl", "ncaa", "college")
        ):
            return AthenaIntentPlan(
                "public_player_development", 0.997,
                "Player development requires pathway, attainment baselines and opportunity reasoning; current news may supplement but cannot replace the player analysis.", 103
            )
        # Comparative reluctance/significance questions about multiple organizational
        # assets are asset-analysis inquiries, even when phrased with "trade" or
        # "why would". They do not require a transaction target/counterparty.
        if _has_any(q,["reluctant","reluctance","hardest to move","least willing","most protect","differently significant","significant to toronto"]) and _has_any(q,["maple leafs","leafs","toronto"]):
            return AthenaIntentPlan("public_nhl_organizational_assets",0.998,"Comparative organizational-asset significance/reluctance requires controlled-asset analysis, not transaction plausibility.",104)
        if _has_any(q,["organizational assets","organization assets","leafs prospects","which leafs prospects","prospects could actually be traded","prospects can be traded","tradeable prospects","tradable prospects"]):
            return AthenaIntentPlan("public_nhl_organizational_assets",0.996,"Organizational asset inquiry requires current provider acquisition plus explicit control/rights and transaction-eligibility classification.",102)
        # Transaction routing consumes normalized Inquiry State. Do not reparse
        # transaction verbs here: phrasing such as get/acquire/trade for must
        # converge once Inquiry State has classified the operation.
        is_transaction = bool(inquiry and inquiry.operation == "transaction")
        is_current_event_investigation = _has_any(q, ["news", "story", "reported", "investigate"])
        if is_transaction and not is_current_event_investigation:
            if "salary_cap" in inquiry.constraints_waived:
                return AthenaIntentPlan("public_nhl_transaction_scenario", 0.999, "Normalized transaction inquiry includes an explicit salary-cap waiver; execute the hypothetical scenario without re-imposing that constraint.", 103)
            if inquiry.plausibility_requested:
                return AthenaIntentPlan("public_nhl_organizational_plausibility", 0.997, "Normalized transaction inquiry explicitly requests organizational plausibility and fit analysis.", 101)
            if inquiry.organizations and inquiry.subjects:
                return AthenaIntentPlan("public_nhl_transaction_scenario", 0.995, "Normalized transaction inquiry requires scenario-state reasoning over the resolved organization, subjects and protected assets.", 100)
        if comparison_players and _has_any(q, ["organizational asset", "asset to", "asset state", "player asset", "organizational value", "what kind of asset"]) and not _has_any(q, ["news", "story", "reported", "investigate"]):
            return AthenaIntentPlan("public_nhl_player_asset_state", 0.985, "Player organizational-asset question requires composed identity, production and professional contract/control evidence without an opaque trade-value score.", 99)
        if _has_any(q, ["contract", "aav", "cap hit", "signed through", "signed until", "free agent", "ufa", "rfa"]) and comparison_players and not _has_any(q, ["news", "story", "reported", "investigate"]):
            return AthenaIntentPlan("public_nhl_player_contract", 0.97, "Named-player contract question requires canonical professional contract evidence, not fantasy contract knowledge.", 98)
        if _has_any(q, ["salary cap", "salary-cap", "cap usage", "cap space", "payroll", "payroll range", "cap ceiling", "upper limit", "lower limit"]) and not _has_any(q, ["news", "story", "reported", "investigate"]):
            if _has_any(q, ["maple leafs", "leafs", "toronto"]):
                return AthenaIntentPlan("public_nhl_cap_reasoning", 0.99, "Team-specific NHL cap question requires executable cap/CBA reasoning over canonical team state with completeness gating.", 99)
            return AthenaIntentPlan("public_nhl_economic_context", 0.96, "NHL economic question requires effective-dated league context before team or contract calculation.", 97)
        mckenna_scenario = _has_any(q, ["mckenna first overall", "first overall in the 2026 nhl draft"]) or (
            "gavin mckenna" in q and _has_any(q, ["toronto", "maple leafs", "leafs", "selected", "select", "draft", "organization", "outlook", "five years", "5 years"])
        )
        if mckenna_scenario:
            return AthenaIntentPlan("public_organization_impact", 0.9, "Explicit public NHL draft/organization scenario must not route to fantasy league analysis.", 95)
        if _has_any(q, ["investigate", "reported acquisition", "acquisition story", "reported interest"]) and _has_any(q, ["story", "report", "acquisition", "interested", "news"]):
            return AthenaIntentPlan("live_event_intelligence", 0.93, "Investigation of a reported current event stays on live Event Intelligence.", 95)
        # Named player-event questions retain the player as their subject.
        # A broad news search cannot establish that articles concern this player.
        if len(comparison_players) == 1 and _has_any(q, ["camp", "preseason", "pre-season", "deployment", "early-season", "early season", "injury", "latest evidence", "recent form"]):
            return AthenaIntentPlan("public_player_investigation", 0.92, "Current player-event question retains the resolved player subject.", 95)
        if _has_any(q, ["biggest nhl story", "biggest story", "story right now", "why it matters"]):
            return AthenaIntentPlan("live_event_intelligence", 0.9, "Current-news prompt should route to Event Intelligence.", 94)
        if _has_any(q, ["best positioned to improve", "improve over the next", "next three seasons"]):
            if _has_any(q, ["teams", "nhl", "league"]):
                return AthenaIntentPlan("public_team_projection", 0.86, "Bounded future-team projection should not hard-refuse.", 88)
        if _has_any(q, ["will determine", "contenders over the next", "over the next three seasons"]):
            if _has_any(q, ["maple leafs", "leafs", "toronto"]):
                return AthenaIntentPlan("public_team_window", 0.88, "Team-window prompt needs organizational implication framing.", 86)
        if q.startswith("why do you believe") or q.startswith("why will") or "will become an elite" in q:
            if _has_any(q, ["bedard", "mcdavid", "matthews", "mackinnon", "celebrini"]):
                return AthenaIntentPlan("public_player_explainability", 0.86, "Why-question requires evidence/reasoning, not stat summary.", 84)

    if selected_mode == "fantasy":
        longitudinal_terms = ["changed over", "change over", "over the last", "over the past", "historically", "history of", "across seasons", "season to season", "season-to-season"]
        draft_terms = ["draft", "drafting", "drafts"]
        league_terms = ["league", "jhlpaa", "fantrax"]
        if _has_any(q, longitudinal_terms) and _has_any(q, draft_terms) and _has_any(q, league_terms):
            return AthenaIntentPlan("fantasy_longitudinal_draft", 0.93, "Multi-season league draft question requires historical evidence discovery.", 94)
        pre_draft_explicit = _has_any(q, ["pre-draft", "pre draft", "draft readiness", "draft context", "going into the draft", "draft look like", "analyze my draft", "analyse my draft", "analyze the draft", "analyse the draft"])
        near_term_draft = _has_any(q, draft_terms) and _has_any(q, ["tomorrow", "tonight", "upcoming", "coming up", "before the draft", "going into", "prepare", "preparing", "prep", "what should i know", "what do i need to know"])
        # Executable investigative branches emitted by pre-draft context. These
        # routes are semantic, not exact-button-string handlers, so typed
        # paraphrases resolve to the same underlying evidence.
        if _has_any(q, ["keeper state", "keepers imply", "keeper pool", "available player pool", "available pool", "player pool"]) and _has_any(q, ["keeper", "available", "pool"]):
            return AthenaIntentPlan("fantasy_keeper_pool_context", 0.94, "Keeper-state question requires current rostered keepers plus bounded available-pool evidence.", 95)
        if _has_any(q, ["draft capital", "current draft capital", "uneven", "pick ownership", "slot ownership"]):
            return AthenaIntentPlan("fantasy_draft_capital_context", 0.93, "Draft-capital question requires current ownership distribution.", 94)
        if _has_any(q, ["change character by round", "by round", "round depth", "historically change", "historical draft patterns", "historically relevant", "patterns are most relevant"]):
            return AthenaIntentPlan("fantasy_historical_draft_context", 0.93, "Historical draft branch requires canonical round-depth intelligence.", 94)
        if pre_draft_explicit or near_term_draft:
            return AthenaIntentPlan("fantasy_pre_draft_context", 0.94, "Current draft-preparation question requires present league state plus historical context.", 93)
        if _has_any(q, ["analyze my roster", "my roster"]) and _has_any(q, ["strength", "weakness", "organizational"]):
            return AthenaIntentPlan("fantasy_roster_diagnostic", 0.9, "Roster prompt should analyze team construction, not only league settings.", 92)
        if _has_any(q, ["trade direction", "trade directions", "realistic trade", "benefits both managers", "target in a trade", "type of player should i target", "player should i target"]):
            return AthenaIntentPlan("fantasy_trade_directions", 0.88, "Trade-direction prompt requires two-sided recommendation framing.", 90)
        if _has_any(q, ["8th overall", "eighth overall", "draft for upside", "organizational need"]):
            return AthenaIntentPlan("fantasy_draft_strategy", 0.86, "Draft-strategy prompt should route to bounded draft advice.", 88)
        if _has_any(q, ["entering a rebuild", "entering rebuild", "rebuild"]):
            return AthenaIntentPlan("fantasy_rebuild_detection", 0.86, "Manager rebuild prompt should use roster/contract/transaction evidence.", 86)
        if _has_any(q, ["trade for a player", "contract expires", "expires in 2027", "2027"]):
            if "contract" in q:
                return AthenaIntentPlan("fantasy_contract_rule", 0.9, "Contract-rule prompt should explain league rule implications.", 90)

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
