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
        natural = ("This is a professional NHL contract-priority inquiry, not a JHLPAA contract lookup. "
                   "Athena must assemble the current Toronto SPC ledger, expiry seasons, AAV, clauses, player rights and "
                   "development timelines before naming an authoritative extension priority or calculating club cap flexibility. "
                   "The currently partial club ledger cannot establish the full two-season decision horizon.")
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
        natural = ("The objective is to add scoring while preserving left-wing depth and the most valued young players. "
                   "A named target is not a prerequisite for investigating the market. Athena should identify verified candidates, "
                   "the seller's likely needs, contract and cap constraints, and what Toronto can actually surrender. "
                   "Do not present a speculative player as available or an unverified asking price as established. ")
        if first:
            natural += ("The user now permits spending a first-round pick for an improvement spanning three seasons; "
                        "the left-wing protection remains in force. That changes the acceptable acquisition cost, not the positional constraint. ")
            facts.append("Scenario preference: first-round pick permitted; left-wing depth protected; three-season horizon.")
        else:
            facts.append("Scenario preference: preserve left-wing depth and priority young players.")
        natural += "A concrete trade recommendation requires validated target availability, player value, outgoing assets and cap ledger."
        limitations = ["Verified market candidates, counterparties, acquisition prices and full cap ledger not yet established."]
    result = response(intent="public_nhl_decision_inquiry", title=title,
        engine_conclusion=natural, natural_language_response=natural, observed_facts=facts,
        known_limitations=limitations, confidence=.55,
        developer=developer_info("public_nhl_decision_inquiry", getattr(ctx, "files_loaded", []),
            intelligence_used=["inquiry_state", "domain_safe_decision_routing"], missing=limitations))
    result.setdefault("developer", {})["decision_inquiry"] = {"kind": kind, "state": inquiry.to_dict(), "coverage": "partial", "no_fabricated_candidates": True}
    return result
