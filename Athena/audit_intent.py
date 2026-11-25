"""Shared affirmative scoring-audit intent for Athena routing and Scout voice.

Mentions of an excluded capability are not requests to perform it. This
classifier is deliberately conservative: ambiguous language stays in ordinary
league analysis; an explicit scoring investigation remains available.
"""
from __future__ import annotations
import re

_AUDIT = re.compile(r"\b(reconcil(?:e|iation)|audits?|verify|verification|debug|diagnos(?:e|tics)|scoring\s+(?:discrepanc(?:y|ies)|integrity)|identity\s+gaps?)\b", re.I)
_NEGATED = re.compile(r"\b(?:do\s+not|don't|does\s+not|doesn't|without|avoid|exclude|no\s+need\s+to|not\s+required\s+to|rather\s+than|instead\s+of|should\s+not|must\s+not)\b", re.I)


def affirmative_audit_request(question: str) -> bool:
    text = (question or "").casefold()
    # Negated clauses terminate at sentence/semicolon breaks; "unless the
    # user requests" is not itself a request. Inspect each actual audit verb.
    for match in _AUDIT.finditer(text):
        prefix = text[:match.start()]
        clause = re.split(r"[.;!?\n]", prefix)[-1]
        negatives = list(_NEGATED.finditer(clause))
        if negatives:
            # A nearby prohibition governs a listed diagnostic even with
            # intervening explanations (e.g., "do not independently recalculate
            # ... or introduce scoring-reconciliation diagnostics").
            continue
        # Treat descriptions of an unrequested investigation as context.
        if re.search(r"\bunless\b[^.;!?\n]*$", clause):
            continue
        return True
    return False
