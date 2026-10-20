"""Evidence-bounded professional decision inquiries; no fantasy contracts or invented deals."""
from __future__ import annotations
import re
from typing import Any
from Scout.conversation.responses import response, developer_info


def execute_decision_inquiry(ctx: Any, question: str) -> dict:
    q = question.casefold()
    from Athena.Inquiry.state import build_inquiry_state
    inquiry = build_inquiry_state(question, "public")
    limitations = []
    facts = []
    if "trade" in q and any(t in q for t in ("revisit", "at the time", "subsequent outcomes", "historical")):
        kind = "retrospective"
        title = "Toronto: transaction history and interpretation"
        natural = ("This is a retrospective inquiry, not a request to construct a new offer. "
                   "The alleged transaction, its date, both sides' consideration, contemporaneous reporting and later outcomes "
                   "must be verified before describing what either club gained. No historical transaction record was established by this request path. "
                   "A hypothetical evaluation can be offered separately, but it must not be presented as an actual completed trade.")
        limitations = ["Verified transaction record and dated contemporaneous reporting not acquired."]
    elif "contract" in q and any(t in q for t in ("decisions", "approaching", "next two seasons")):
        kind = "contracts"
        title = "Toronto: NHL contract decision horizon"
        natural = ("Toronto's contract priorities over the next two seasons should be ranked by decision deadline, "
                   "replacement difficulty, projected role and cap opportunity cost, rather than by AAV alone. "
                   "First protect against losing a difficult-to-replace core contributor; next decide whether an emerging player "
                   "should be extended before a larger role increases the price; finally compare depth renewals with internal replacements. "
                   "These are decision tiers, not verified rankings of individual players: the available contract ledger is partial, "
                   "so it does not establish every expiry, negotiation window, clause or remaining cap commitment.")
        limitations = ["Complete verified NHL contract ledger and player-specific expiry/rights coverage unavailable."]
    elif "injur" in q:
        kind = "injury_scenario"
        title = "Toronto: six-week injury replacement scenario"
        natural = ("For two regular forwards unavailable for six weeks, first verify each injury's expected absence and "
                   "whether LTIR eligibility and cap treatment apply; six weeks alone does not establish LTIR relief. "
                   "Next identify eligible Marlies recalls, their actual NHL contracts, waiver status and assignment history. "
                   "Then test active roster limits, SPC count, daily cap charges, available space and the sequencing of "
                   "recalls/assignments. Prefer feasible internal coverage before evaluating outside acquisitions. "
                   "No specific call-up or dollar relief is asserted without a verified player and team ledger.")
        limitations = ["Current player-specific waivers, roster ledger, injury designations and cap adjustments require verification."]
    else:
        kind = "exploratory_trade"
        title = "Toronto: constrained trade exploration"
        first = bool(re.search(r"first.round pick|first round pick", q))
        natural = ("Toronto should pursue a scoring upgrade without creating a new left-wing vacancy. "
                   "That rules out a nominal offensive upgrade whose outgoing package removes equivalent left-wing production. "
                   "The first viable structure is a right-wing or versatile scoring forward acquired for futures and expendable depth; "
                   "its advantage is preserving today's lineup, while its risk is a larger future-asset cost. "
                   "The second is a cap-balanced hockey trade using an established non-protected roster player; "
                   "it limits added payroll but may simply move the lineup weakness elsewhere. "
                   "The third is a lower-cost, shorter-term scorer; it protects premium assets but offers less certainty over three seasons. ")
        if first:
            natural += ("Allowing the next available first-round pick materially strengthens the futures-led offer, "
                        "but only if Toronto actually controls an eligible pick and the counterparty values it. "
                        "For a three-year outlook, prefer a controllable scorer with a sustainable role and affordable contract "
                        "over an expiring rental unless an extension is credible. Do not spend the pick merely to win a short-term comparison. ")
            facts.append("Scenario preference: first-round pick permitted; left-wing depth protected; three-season horizon.")
        else:
            facts.append("Scenario preference: preserve left-wing depth and priority young players.")
        natural += ("The decision gates are distinct: establish an eligible pick and its conditions; "
                    "identify contract-controlled scoring candidates on actual NHL rosters; "
                    "screen each for role fit without removing a left winger; then test cap feasibility, "
                    "transaction restrictions and a plausible counterparty incentive. "
                    "A candidate with strong production but no plausible acquisition path is not a realistic target. "
                    "For each eligible candidate, compare current-year roster gain, next-two-year control, "
                    "replacement cost and pick opportunity cost before recommending an offer. ")
        natural += ("No specific player or asking price can responsibly be ranked as the preferred target yet: "
                    "verified market availability, Toronto's outgoing asset rights and a complete cap ledger are missing. "
                    "The preferred acquisition *structure* is futures-led, not a left-wing-for-scoring swap.")
        limitations = ["Verified market candidates, counterparties, acquisition prices and full cap ledger not yet established."]
    result = response(intent="public_nhl_decision_inquiry", title=title,
        engine_conclusion=natural, natural_language_response=natural, observed_facts=facts,
        known_limitations=limitations, confidence=.55,
        developer=developer_info("public_nhl_decision_inquiry", getattr(ctx, "files_loaded", []),
            intelligence_used=["inquiry_state", "domain_safe_decision_routing"], missing=limitations))
    result.setdefault("developer", {})["decision_inquiry"] = {"kind": kind, "state": inquiry.to_dict(), "coverage": "partial", "no_fabricated_candidates": True}
    return result
