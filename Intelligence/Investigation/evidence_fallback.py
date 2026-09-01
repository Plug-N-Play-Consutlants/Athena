"""Graceful evidence fallback for current-event/update strategies.

Fallback never substitutes unrelated entities. It degrades from live/current evidence
only to the most recent trustworthy evidence for the requested entity/context, while
preserving explicit freshness metadata.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable, Tuple

EVIDENCE_FALLBACK_VERSION = "0.6.4.1.0"

@dataclass(frozen=True)
class EvidenceCandidate:
    evidence_id: str
    entity_keys: Tuple[str, ...]
    title: str
    summary: str
    observed_at: str = ""
    source: str = ""
    confidence: float = 0.0
    live: bool = False
    trusted: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class EvidenceSelection:
    status: str
    tier: str
    items: Tuple[EvidenceCandidate, ...]
    freshness_note: str
    limitations: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "version": EVIDENCE_FALLBACK_VERSION,
            "status": self.status,
            "tier": self.tier,
            "items": [item.to_dict() for item in self.items],
            "freshness_note": self.freshness_note,
            "limitations": self.limitations,
        }

def _timestamp(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0

def select_recent_relevant_evidence(
    candidates: Iterable[EvidenceCandidate], *, requested_entities: Iterable[str] = (), limit: int = 3
) -> EvidenceSelection:
    requested = {str(v).strip().lower() for v in requested_entities if str(v).strip()}
    trusted = [c for c in candidates if c.trusted]
    if requested:
        trusted = [c for c in trusted if requested.intersection({e.lower() for e in c.entity_keys})]
    if not trusted:
        return EvidenceSelection(
            "no_relevant_evidence", "none", (), "No relevant trustworthy evidence is available.",
            ("Athena did not substitute unrelated evidence.",),
        )
    live = [c for c in trusted if c.live]
    pool = live or trusted
    pool = sorted(pool, key=lambda c: (_timestamp(c.observed_at), c.confidence), reverse=True)[:max(1, limit)]
    tier = "live" if live else "recent_fallback"
    newest = pool[0].observed_at if pool else ""
    freshness = f"Most recent evidence observed: {newest}." if newest else "Source did not provide a reliable observation date."
    limitations = () if live else ("No matching live evidence was available; Athena used the most recent relevant trustworthy evidence instead.",)
    return EvidenceSelection("available", tier, tuple(pool), freshness, limitations)
