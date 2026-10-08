"""Response Composition Engine for Scout acceptance surfaces.

This layer is the contract between Athena reasoning outputs and Scout display.
Reasoning modules may return conclusions, evidence, limitations, cards and raw
traces, but Scout's public surface must receive one clean user-facing answer.
"""

from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Iterable, List

from Experience.renderer import attach_experience_contract

PUBLIC_TEXT_KEYS = ("natural_language_response", "public_comment", "response_text", "scout_message", "engine_conclusion")
DIAGNOSTIC_KEYS = ("engine_conclusion", "observed_facts", "known_limitations", "raw_reasoning_output", "developer", "operation_result")

_INTERNAL_PATTERNS = [
    re.compile(r"\bAthena is combining\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b[A-Z][A-Za-z ]+ Intelligence \d+[A-Z]?\.\d+\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bPIF Build \d+\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bcurrent local evidence supports\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bno longer assessed as a one-season stat line\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
]

_INTERNAL_LINE_PREFIXES = (
    "supporting evidence",
    "engine conclusion",
    "observed facts",
    "known limitations",
    "developer mode",
    "confidence:",
    "primary limitations:",
    "context impact",
    "contract context",
)

_LABEL_REPLACEMENTS = {
    "Athena Conclusion:": "Conclusion:",
    "Executive Comparison:": "Comparison:",
    "Public framing:": "Summary:",
    "nHL": "NHL",
    " are NHL franchise": " is an NHL franchise",
    "..": ".",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _first_text(answer: Dict[str, Any], keys: Iterable[str] = PUBLIC_TEXT_KEYS) -> str:
    for key in keys:
        text = _clean_text(answer.get(key))
        if text:
            return text
    return _clean_text(answer.get("title"))


def _as_list(value: Any, limit: int | None = None) -> List[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit] if limit is not None else list(value)


def _clean_public_text(text: str) -> str:
    text = unescape(_clean_text(text)).replace("\xa0", " ")
    if not text:
        return ""
    for pattern in _INTERNAL_PATTERNS:
        text = pattern.sub("", text)
    for old, new in _LABEL_REPLACEMENTS.items():
        text = text.replace(old, new)
    kept: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in _INTERNAL_LINE_PREFIXES):
            continue
        if " evidence available:" in lower:
            continue
        if "module" in lower and "execut" in lower:
            continue
        kept.append(line)
    cleaned = "\n".join(kept).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = cleaned.replace(" .", ".")
    return cleaned.strip()


def _card_map(answer: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for card in answer.get("cards") or []:
        if isinstance(card, dict):
            label = _clean_text(card.get("label"))
            value = _clean_text(card.get("value"))
            if label and value:
                result[label.lower()] = value
    return result


def _compose_player_public(answer: Dict[str, Any], candidate: str) -> str:
    title = _clean_text(answer.get("title")) or "Player analysis"
    cards = _card_map(answer)
    facts = [_clean_public_text(item) for item in _as_list(answer.get("observed_facts"), 10)]
    facts = [item for item in facts if item]
    lines: List[str] = []
    if candidate:
        first = candidate.split("\n", 1)[0].strip()
        if first and len(first) > 40:
            lines.append(first)
    if not lines:
        role = cards.get("role") or cards.get("public value") or cards.get("career tier")
        band = cards.get("production band")
        ppg = cards.get("ppg") or cards.get("3-year ppg")
        pieces = []
        if role:
            pieces.append(f"profiles as {role.lower()}")
        if band:
            pieces.append(f"with {band.lower()} production")
        if ppg:
            pieces.append(f"around {ppg} points per game in the available sample")
        if pieces:
            lines.append(f"{title} {' '.join(pieces)}.")
    for fact in facts:
        lower = fact.lower()
        if any(term in lower for term in ["identity:", "career legacy", "current value", "career baselines", "trend analysis", "organizational importance", "historical context"]):
            lines.append(fact)
        elif len(lines) < 4 and not any(bad in lower for bad in ["evidence", "build", "module"]):
            lines.append(fact)
    if candidate and len(candidate.splitlines()) > 1:
        for block in candidate.split("\n\n"):
            clean = _clean_public_text(block)
            if clean and clean not in lines and not clean.lower().startswith("executive summary"):
                lines.append(clean)
    if not lines:
        lines.append(title)
    return "\n\n".join(lines[:8])


def _compose_team_public(answer: Dict[str, Any], candidate: str) -> str:
    candidate = _clean_public_text(candidate)
    if candidate and not candidate.lower().startswith("executive summary:"):
        return candidate
    facts = [_clean_public_text(item) for item in _as_list(answer.get("observed_facts"), 10)]
    facts = [item for item in facts if item]
    title = _clean_text(answer.get("title")) or "Team analysis"
    lines = [title]
    for fact in facts[:6]:
        lines.append(fact)
    return "\n\n".join(lines)


def _compose_pre_draft_public(answer: Dict[str, Any], candidate: str) -> str:
    """Keep the casual pre-draft answer useful without exposing diagnostics."""
    candidate = _clean_public_text(candidate)
    facts = [_clean_public_text(item) for item in _as_list(answer.get("observed_facts"), 8)]
    facts = [item for item in facts if item]
    lines: List[str] = [candidate] if candidate else []
    # The route narrative carries current state and historical findings. Add only
    # material evidence that the compact narrative does not already communicate.
    for fact in facts:
        lower = fact.lower()
        if "fantrax export" in lower and fact not in lines:
            lines.append(fact)
    conclusion = _clean_public_text(answer.get("engine_conclusion"))
    if conclusion and conclusion not in lines:
        lines.append(conclusion)
    return "\n\n".join(lines) or _clean_text(answer.get("title")) or "Scout response"


def _compose_live_event_public(answer: Dict[str, Any], candidate: str) -> str:
    """Preserve the selected-event narrative as the primary normal-mode answer."""
    candidate = _clean_public_text(candidate)
    if candidate:
        return candidate
    facts = [_clean_public_text(item) for item in _as_list(answer.get("observed_facts"), 6)]
    facts = [item for item in facts if item]
    return "\n\n".join(facts) or _clean_text(answer.get("title")) or "Scout response"



def _facts(answer: Dict[str, Any], limit: int = 12) -> List[str]:
    return [x for x in (_clean_public_text(item) for item in _as_list(answer.get("observed_facts"), limit)) if x]

def _limits(answer: Dict[str, Any], limit: int = 8) -> List[str]:
    return [x for x in (_clean_public_text(item) for item in _as_list(answer.get("known_limitations"), limit)) if x]

def _compose_temporal_public(answer: Dict[str, Any], candidate: str) -> str:
    facts = _facts(answer)
    if not facts:
        return _clean_public_text(candidate) or _clean_text(answer.get("title"))
    title = _clean_text(answer.get("title")) or "Season comparison"
    lines = [f"{title}", "", "Season-by-season:"]
    lines.extend(f"• {fact}" for fact in facts)
    limits = _limits(answer, 2)
    if limits:
        lines.extend(["", "Context:", *[f"• {item}" for item in limits]])
    return "\n".join(lines)

def _construction_paths(answer: Dict[str, Any]) -> List[Dict[str, str]]:
    developer = answer.get("developer") if isinstance(answer.get("developer"), dict) else {}
    adaptive = developer.get("adaptive_execution") if isinstance(developer.get("adaptive_execution"), dict) else {}
    return [item for item in adaptive.get("paths", []) if isinstance(item, dict) and _clean_text(item.get("analysis"))]

def _compose_transaction_public(answer: Dict[str, Any], candidate: str) -> str:
    facts=_facts(answer); limits=_limits(answer)
    developer=answer.get("developer") if isinstance(answer.get("developer"),dict) else {}
    inquiry=developer.get("inquiry_state") if isinstance(developer.get("inquiry_state"),dict) else {}
    investigation=developer.get("investigation_state") if isinstance(developer.get("investigation_state"),dict) else {}
    evidence=investigation.get("evidence") if isinstance(investigation.get("evidence"),dict) else {}
    study=evidence.get("analytical_study") if isinstance(evidence.get("analytical_study"),dict) else {}
    candidates=[x for x in evidence.get("candidate_assets",[]) if isinstance(x,dict)]
    package=evidence.get("named_package") if isinstance(evidence.get("named_package"),dict) else {}
    # Public scenario assets are the package the user authorized, not the broader
    # candidate universe Athena investigated while evaluating alternatives.
    package_names={str(x).casefold() for x in package.get("assets",[]) if str(x).strip()}
    scenario_assets=[x for x in candidates if str(x.get("name") or "").casefold() in package_names] if package_names else candidates
    protected=[str(x) for x in inquiry.get("protected_assets",[]) if x]
    target=_clean_text(package.get("target")) or "the target player"
    thesis=_clean_public_text(study.get("thesis"))
    lines=["Scenario Assessment", thesis or _clean_public_text(candidate)]
    if scenario_assets:
        lines.extend(["", "Assets on the Table"] )
        for asset in scenario_assets[:5]:
            name=_clean_text(asset.get("name")); signals=[_clean_text(x) for x in asset.get("fit_signals",[]) if _clean_text(x)]
            fit=[_clean_text(x) for x in asset.get("seller_fit_considerations",[]) if _clean_text(x)]
            cost=[_clean_text(x) for x in asset.get("buyer_cost_considerations",[]) if _clean_text(x)]
            lines.append(f"• {name}" + (f" — {', '.join(signals[:3])}" if signals else ""))
            if fit: lines.append(f"  Counterparty value: {fit[0]}")
            if cost: lines.append(f"  Toronto cost: {cost[0]}")
    buyer=_clean_public_text(study.get("buyer_objective")); seller=_clean_public_text(study.get("seller_objective"))
    if buyer or seller:
        lines.extend(["", "What Needs Are We Addressing on Both Sides"] )
        if buyer: lines.append(f"• Toronto: {buyer}")
        if seller: lines.append(f"• Counterparty: {seller}")
    assets=[_clean_text(x) for x in package.get("assets",[]) if _clean_text(x)]
    if assets:
        lines.extend(["", "Proposed Construction", f"• {target} for {', '.join(assets)}"] )
        assessment=_clean_public_text(package.get("assessment"))
        if assessment: lines.append(f"• {assessment}")
    financial=[x for x in facts if "cap" in x.lower() or "charge" in x.lower()]
    if financial or study.get("financial_status"):
        lines.extend(["", "Financial Impact"] )
        lines.extend(f"• {x}" for x in financial[:3])
        if study.get("financial_status")=="waived_for_scenario": lines.append("• Salary-cap feasibility is waived for this hypothetical, but known salary information remains part of the real-world context.")
        elif limits: lines.append("• Final team cap usage remains qualified until the complete team ledger is available.")
    if limits:
        lines.extend(["", "Rules & Transaction Mechanics"] )
        lines.extend(f"• {x}" for x in limits[:3])
    dq=study.get("decision_quality") if isinstance(study.get("decision_quality"),dict) else {}
    if dq:
        costs=[_clean_public_text(x) for x in dq.get("known_costs",[]) if _clean_public_text(x)]
        alts=[x for x in dq.get("alternatives",[]) if isinstance(x,dict)]
        if costs:
            lines.extend(["", "Opportunity Cost"]); lines.extend(f"• {x}" for x in costs[:4])
        if alts:
            lines.extend(["", "Credible Alternatives"]); lines.extend(f"• {_clean_public_text(x.get('significance'))}" for x in alts[:4] if _clean_public_text(x.get('significance')))
    decision=_clean_public_text(study.get("buyer_decision"))
    if thesis or decision:
        lines.extend(["", "Athena's Verdict"])
        # Seller sufficiency/availability is a separate question from the requested
        # buyer-side decision. When a decision was requested, lead with the decision.
        if decision: lines.append(decision)
        if thesis: lines.append("Seller-side availability: " + thesis if decision else thesis)
    principle=_clean_public_text(dq.get("principle")) if dq else ""
    rawq=_clean_text(study.get("question")).lower()
    if principle and any(x in rawq for x in ("bad eventual outcome","bad outcome","good outcome","bad decision","decision today")):
        lines.extend(["", "Decision Quality vs. Outcome", principle])
    return "\n".join(x for x in lines if x is not None).strip()

def _compose_plausibility_public(answer: Dict[str, Any], candidate: str) -> str:
    facts=_facts(answer); limits=_limits(answer)
    paths=_construction_paths(answer)
    title=_clean_text(answer.get("title"))
    lead="Potentially, but Athena cannot yet defend a specific offer as realistic from the current evidence."
    if "evidence gap" in title.lower():
        lead=_clean_public_text(candidate) or lead
    lines=[lead]
    if facts:
        lines.extend(["", "What is established:", *[f"• {x}" for x in facts[:5]]])
    if paths:
        lines.extend(["", "Possible structures:"])
        for item in paths:
            lines.append(f"• {_clean_text(item.get('label'))}: {_clean_public_text(item.get('analysis'))}")
    if limits:
        lines.extend(["", "What keeps this from being a defensible named proposal:", *[f"• {x}" for x in limits[:4]]])
    return "\n".join(lines).strip()

def _compose_evidence_public(answer: Dict[str, Any], candidate: str) -> str:
    candidate=_clean_public_text(candidate)
    facts=_facts(answer, 6)
    if candidate:
        return candidate
    return "\n".join(facts) or _clean_text(answer.get("title")) or "Scout response"

def _compose_organizational_assets_public(answer: Dict[str, Any], candidate: str) -> str:
    developer=answer.get("developer") if isinstance(answer.get("developer"),dict) else {}
    assets=developer.get("organizational_assets") if isinstance(developer.get("organizational_assets"),dict) else {}
    subset=_clean_text(assets.get("query_subset"))
    selected=[x for x in assets.get("selected_players",[]) if isinstance(x,dict)]
    # Comparative significance is an analytical clause, not a vocabulary test.
    # If Athena resolved a named asset set and significance/reluctance was requested,
    # render that assessment even when the user never says the word "prospects".
    if assets.get("reluctance_requested") and selected:
        ranking=[x for x in assets.get("reluctance_ranking",[]) if isinstance(x,dict)]
        lines=["Organizational Significance", "Athena is comparing the requested Toronto-controlled assets by the significance of the evidence available for each, not merely by age or draft order."]
        for i,x in enumerate(ranking[:8],1):
            sig=x.get("organizational_significance") if isinstance(x.get("organizational_significance"),dict) else {}
            base=x.get("asset_significance") if isinstance(x.get("asset_significance"),dict) else {}
            why=[_clean_public_text(v) for v in sig.get("considerations",[]) if _clean_public_text(v)]
            if not why:
                why=[_clean_public_text(d.get("significance")) for d in base.get("dimensions",[]) if isinstance(d,dict) and d.get("state") in {"established","supported_inference"} and _clean_public_text(d.get("significance"))]
            lines.append(f"{i}. {_clean_text(x.get('name'))} — " + (" ".join(why[:3]) if why else "current evidence establishes control but does not yet differentiate this asset strongly on significance dimensions"))
        lines.extend(["", "Athena's ranking is an evidence-backed organizational-value judgment, not a claim about Toronto management's private preferences."])
        return "\n".join(lines)
    if subset=="prospects":
        lines=[f"Athena currently identifies {len(selected)} Toronto-controlled prospect/development relationships matching this inquiry. Playing location alone is not enough: each listed asset must have organizational-control evidence before it is considered for transaction analysis.", "", "Controlled Prospects Eligible for Analysis"]
        for x in selected[:20]:
            rs=x.get("rights_state") if isinstance(x.get("rights_state"),dict) else {}
            lines.append(f"• {_clean_text(x.get('name'))} — {_clean_text(rs.get('transaction_status')) or 'control/restrictions require evidence'}")
        lines.extend(["", "Rights & Restrictions", "Exact SPC versus unsigned-rights mechanisms, expiry dates and NMC/NTC or other restrictions remain evidence-dependent. A provider prospect association alone is not treated as current legal control or transaction eligibility."])
        if assets.get("reluctance_requested"):
            ranking=[x for x in assets.get("reluctance_ranking",[]) if isinstance(x,dict)]
            lines.extend(["", "Most Reluctant to Move"])
            if ranking:
                for i,x in enumerate(ranking[:5],1):
                    sig=x.get("organizational_significance") if isinstance(x.get("organizational_significance"),dict) else {}
                    base=x.get("asset_significance") if isinstance(x.get("asset_significance"),dict) else {}
                    why=[_clean_public_text(v) for v in sig.get("considerations",[]) if _clean_public_text(v)]
                    if not why:
                        why=[_clean_public_text(d.get("significance")) for d in base.get("dimensions",[]) if isinstance(d,dict) and d.get("state") in {"established","supported_inference"} and _clean_public_text(d.get("significance"))]
                    lines.append(f"{i}. {_clean_text(x.get('name'))} — " + (" ".join(why[:2]) if why else "current evidence supports keeping this asset ahead of lower-significance alternatives"))
                lines.append("Athena's reluctance ranking is an evidence-backed organizational-value judgment, not a claim about Toronto management's private preferences.")
            else:
                lines.append("Athena cannot rank reluctance until current control and significance are established for at least one eligible prospect asset.")
        return "\n".join(lines)
    return _compose_evidence_public(answer,candidate)

def _default_followups(answer: Dict[str, Any]) -> List[str]:
    intent=_clean_text(answer.get("intent")).lower()
    if intent == "public_player_temporal_comparison":
        return ["Compare the scoring rates across those seasons", "Show the player's full NHL career", "What changed most across this window?"]
    if intent == "public_nhl_organizational_plausibility":
        return ["Build the strongest named offer from current evidence", "What would the selling team actually need?", "Try a three-team construction", "Show the cap obstacles separately"]
    if intent == "public_nhl_transaction_scenario":
        return ["What would it take to make this offer stronger?", "Which asset is hardest for Toronto to give up?", "Try a three-team construction"]
    if intent == "public_nhl_organizational_assets":
        return ["Which controlled assets carry the most significance?", "Which assets are rights rather than NHL contracts?", "Use this asset pool in a trade scenario"]
    if intent in {"public_nhl_cap_reasoning", "public_nhl_team_economic_state", "public_nhl_economic_context"}:
        return ["What evidence is still missing?", "Show the relevant cap rules", "How would this affect a transaction scenario?"]
    if intent == "public_nhl_player_contract":
        return ["Show this contract as a percentage of the cap", "Compare this contract to another player", "How does the contract affect trade flexibility?"]
    if intent == "public_nhl_player_asset_state":
        return ["What drives this player's organizational value?", "Compare this asset state to another player", "What evidence is still missing?"]
    return []

PUBLIC_COMPOSERS = {
    "player_analysis": _compose_player_public,
    "public_player_profile": _compose_player_public,
    "public_player_temporal_comparison": _compose_temporal_public,
    "public_team_profile": _compose_team_public,
    "public_team_comparison": _compose_team_public,
    "public_analytical_route": _compose_team_public,
    "live_event_intelligence": _compose_live_event_public,
    "fantasy_pre_draft_context": _compose_pre_draft_public,
    "public_nhl_transaction_scenario": _compose_transaction_public,
    "public_nhl_organizational_assets": _compose_organizational_assets_public,
    "public_nhl_organizational_plausibility": _compose_plausibility_public,
    "public_nhl_economic_context": _compose_evidence_public,
    "public_nhl_team_economic_state": _compose_evidence_public,
    "public_nhl_cap_reasoning": _compose_evidence_public,
    "public_nhl_player_contract": _compose_evidence_public,
    "public_nhl_player_asset_state": _compose_evidence_public,
}

REQUIRED_PUBLIC_COMPOSITION_INTENTS = frozenset({
    "public_player_temporal_comparison",
    "public_nhl_economic_context", "public_nhl_team_economic_state",
    "public_nhl_cap_reasoning", "public_nhl_transaction_scenario", "public_nhl_organizational_assets",
    "public_nhl_organizational_plausibility", "public_nhl_player_contract",
    "public_nhl_player_asset_state",
})

def _compose_public_comment(answer: Dict[str, Any]) -> str:
    candidate = _clean_public_text(_first_text(answer))
    intent = _clean_text(answer.get("intent")).lower()
    composer = PUBLIC_COMPOSERS.get(intent)
    if composer is not None:
        return composer(answer, candidate)
    if intent in REQUIRED_PUBLIC_COMPOSITION_INTENTS:
        raise ValueError(f"Registered public intent lacks a public composition template: {intent}")
    return candidate or _clean_text(answer.get("title")) or "Scout response"


def compose_answer_payload(answer: Dict[str, Any]) -> Dict[str, Any]:
    """Return an answer with explicit public and diagnostic surfaces."""
    if not isinstance(answer, dict):
        public_text = _clean_public_text(answer)
        return attach_experience_contract({
            "title": "Scout response",
            "public_comment": public_text,
            "natural_language_response": public_text,
            "diagnostics": {},
            "display_contract": "public_comment_only",
        })

    diagnostics = {
        "engine_conclusion": _clean_text(answer.get("engine_conclusion")),
        "observed_facts": _as_list(answer.get("observed_facts"), 12),
        "known_limitations": _as_list(answer.get("known_limitations"), 12),
        "internal_narrative": _clean_text(answer.get("internal_narrative")) or _clean_text(answer.get("natural_language_response")) or _clean_text(answer.get("engine_conclusion")),
        "raw_reasoning_output": _clean_text(answer.get("raw_reasoning_output")) or _clean_text((answer.get("developer") or {}).get("raw_reasoning_output") if isinstance(answer.get("developer"), dict) else ""),
        "developer": answer.get("developer") if isinstance(answer.get("developer"), dict) else {},
        "operation_result": answer.get("operation_result") or ((answer.get("developer") or {}).get("operation_result") if isinstance(answer.get("developer"), dict) else None),
    }

    composed = dict(answer)
    public_comment = _compose_public_comment(composed)
    composed["public_comment"] = public_comment
    # Collapse legacy answer aliases onto the public surface so older consumers
    # cannot accidentally render stale diagnostic/fallback prose.
    composed["natural_language_response"] = public_comment
    composed["response_text"] = public_comment
    composed["scout_message"] = public_comment
    composed["diagnostics"] = diagnostics
    composed["display_contract"] = "public_comment_only"
    composed["diagnostic_keys"] = list(DIAGNOSTIC_KEYS)
    if not composed.get("suggested_prompts"):
        composed["suggested_prompts"] = _default_followups(composed)
    return attach_experience_contract(composed)


def public_debug_summary(answer: Dict[str, Any]) -> Dict[str, Any]:
    composed = compose_answer_payload(answer)
    diagnostics = composed.get("diagnostics") if isinstance(composed.get("diagnostics"), dict) else {}
    return {
        "title": composed.get("title", "Scout response"),
        "intent": composed.get("intent", ""),
        "public_comment": composed.get("public_comment", ""),
        "confidence": composed.get("confidence"),
        "diagnostics": {
            "engine_conclusion": diagnostics.get("engine_conclusion", ""),
            "observed_facts": _as_list(diagnostics.get("observed_facts"), 12),
            "known_limitations": _as_list(diagnostics.get("known_limitations"), 12),
        },
    }
