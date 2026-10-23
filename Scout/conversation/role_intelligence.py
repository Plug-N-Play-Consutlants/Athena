"""Scout role selection: assignment-aware voice, never a change to Athena evidence.

A role is a presentation contract, not a claim about confidence or an alternative
intelligence source. The user's actual task overrides the selected UI mode.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class ScoutRole:
    role: str
    rationale: str
    style: str
    evidence_policy: str = "athena_evidence_first"

    def to_dict(self) -> dict:
        return asdict(self)


def _has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def select_scout_role(question: str, *, intent: str = "", route: str = "", mode: str = "") -> ScoutRole:
    """Select presentation voice; preserve audit/diagnostic requests even in fantasy mode.

    An explicit role request may choose a voice, but it cannot suppress the
    evidence gaps, caveats or an explicitly requested audit.
    """
    q = (question or "").strip().casefold()
    label = f"{intent} {route}".casefold()
    explicit_audit = _has(q, r"\b(reconcil(?:e|iation)|audits?|debug|diagnos(?:e|tics)|verify scoring|scoring integrity|identity gaps?)\b")
    if explicit_audit or _has(label, r"(?:runtime|scoring|identity)_diagnostic|audit|scoring_period_boundary"):
        return ScoutRole("auditor", "explicit verification or diagnostic assignment", "precise; exceptions and provenance first")
    # User-specified rhetorical assignment has priority below integrity inquiries.
    if _has(q, r"\b(as (?:a |an )?(?:sports )?journalist|write (?:a |the )?column|sportswriter|make (?:it|this) fun)\b"):
        return ScoutRole("journalist", "explicit editorial assignment", "lively; observational; grounded humour")
    if _has(q, r"\b(as (?:a |an )?(?:nhl )?(?:general manager|gm|executive)|from (?:a |the )?(?:front.office|gm|executive) perspective)\b"):
        return ScoutRole("executive", "explicit front-office assignment", "decisive; options, cost and tradeoffs")
    if _has(q, r"\b(as (?:a |an )?(?:nhl )?scout|scouting report|scout (?:this|him|her|them))\b"):
        return ScoutRole("analyst", "explicit scouting assignment", "evaluative; mechanisms, fit and development")
    league_context = _has(q, r"\b(jhlpaa|fantrax|league|fantasy|weekly|week|managers?)\b") or "league_recap" in label
    editorial_request = _has(q, r"\b(weekly (?:league )?(?:report|recap|roundup)|league (?:report|recap|roundup|news)|around the league|around the jhlpaa|what(?:'s| is) happening|what happened|who(?:'s| is) making moves|movers and shakers|sports column|editorial|recap|headlines|week(?:ly)? highlights?)\b")
    if "league_recap" in label or (league_context and editorial_request) or (intent == "analyze_league" and not _has(q, r"\b(team weaknesses|draft prep|roster improve)\b")):
        return ScoutRole("journalist", "league news and recap assignment", "lively; observant; news-led, not a score dump")
    # A front-office decision is different from general player or roster assessment.
    decision = _has(q, r"\b(should (?:we|i|they|the \w+)|would you|recommend|best (?:move|deal)|trade|trading|acquir(?:e|ing)|sign(?:ing)?|salary.cap|ltir|buyout|retention|contract|cap space|keeper strategy|draft capital|organizational strategy|rebuild|contend|gm|management)\b")
    if decision and _has(q, r"\b(trade|acquir|sign|cap|contract|keeper|pick|strateg|management|organiz|rebuild|asset|cost|deal|retain|buyout|waiver)\b"):
        return ScoutRole("executive", "roster-construction or asset decision", "decision-led; constraints, alternatives and uncertainties")
    if _has(q, r"\b(improv(?:e|ement|ements)|weakness(?:es)?|roster fit|lineup fit|scout|prospect|compare|vs\.?|versus|evaluate|strengths?|deployment|development|player|performance|top.six|bottom.six)\b") or _has(label, r"player|team_investigation|comparison|scouting"):
        return ScoutRole("analyst", "evaluation and improvement assignment", "specific; performance, role, fit and evidence")
    return ScoutRole("analyst", "general analytical inquiry", "clear; useful; evidence-bounded")


def attach_role_metadata(answer: dict, *, question: str, route: str = "", mode: str = "") -> dict:
    """Add inspectable role provenance without altering confidence or reasoning."""
    if not isinstance(answer, dict):
        return answer
    role = select_scout_role(question, intent=str(answer.get("intent") or ""), route=route, mode=mode)
    answer.setdefault("developer", {})["scout_role"] = role.to_dict()
    return answer


def compose_consultative_answer(answer: dict, *, question: str, role: ScoutRole) -> dict:
    """Give evaluation/decision inquiries a role-specific, bounded structure.

    Do not change the answer to bare profiles, already structured reports,
    period audits or weak-evidence gaps. No additional facts are inferred here.
    """
    if not isinstance(answer, dict) or role.role not in {"analyst", "executive"}:
        return answer
    q = (question or "").casefold()
    intent = str(answer.get("intent") or "")
    if not (
        (role.role == "executive" and any(word in q for word in
            ("should", "trade", "acquire", "contract", "keeper", "cap ", "improve", "strategy", "recommend")))
        or (role.role == "analyst" and any(word in q for word in
            ("compare", "versus", " vs ", "evaluate", "weakness", "improve", "scout", "roster fit")))
    ):
        return answer
    if intent in {"clarify_or_help", "analyze_league", "public_player_profile", "public_team_profile"} or "audit" in intent:
        return answer
    original = str(answer.get("natural_language_response") or answer.get("engine_conclusion") or "").strip()
    if not original or len(original) > 5200 or original.startswith(("Scouting assessment", "Executive decision brief")):
        return answer
    # A specialist's explicit evidence gap should stay a gap, not become a fake recommendation.
    if intent.endswith("_gap") or (answer.get("confidence") is not None and answer["confidence"] < .4):
        return answer
    title = "Executive decision brief" if role.role == "executive" else "Scouting assessment"
    caveats = [str(x).strip() for x in answer.get("known_limitations") or [] if str(x).strip()]
    # Avoid exposing raw diagnostic labels. These are sourced limits, not recommendations.
    if caveats and not any(c in original for c in caveats):
        original += "\n\nWhat still needs verification\n" + "\n".join(f"• {c}" for c in caveats[:3])
    result = f"{title}\n\n{original}"
    # Scout UI renders public_comment and its already-built AthenaResponse,
    # not the legacy natural-language alias. Keep every presentation surface
    # consistent; leave engine_conclusion and diagnostics unchanged.
    for key in ("public_comment", "natural_language_response", "response_text", "scout_message"):
        answer[key] = result
    answer["internal_narrative"] = result
    answer.setdefault("developer", {})["scout_role_composition"] = "bounded_consultative_framing"
    from Experience.renderer import attach_experience_contract
    return attach_experience_contract(answer)
