"""Canonical Experience Layer response models for Athena Scout.

The Experience Layer is intentionally data-agnostic. It receives normalized
Athena response payloads and produces structured sections that any Scout client
can render without knowing provider, graph, reasoning, or sport internals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

EXPERIENCE_LAYER_VERSION = "0.6.2.1.0"
ATHENA_RESPONSE_SCHEMA_VERSION = "athena_response_v1"


@dataclass
class ExperienceMetadata:
    """Stable metadata for all rendered Athena responses."""

    schema_version: str = ATHENA_RESPONSE_SCHEMA_VERSION
    experience_layer_version: str = EXPERIENCE_LAYER_VERSION
    response_mode: str = "public"
    source_intent: str = ""
    display_contract: str = "athena_response"


@dataclass
class ConfidenceSummary:
    """User-facing confidence summary with optional support detail."""

    label: str = "Unknown"
    score: Optional[float] = None
    rationale: str = ""


@dataclass
class EvidenceItem:
    """Normalized evidence item for expandable evidence panels."""

    label: str
    value: str
    source: str = "athena"
    confidence: Optional[float] = None


@dataclass
class PlayerIdentity:
    """Top-card player identity contract.

    Jersey/player number is first-class, not a cosmetic string embedded in the
    name. Later clients can render it in headers, cards, comparison matrices,
    profile popups, or fantasy roster views without parsing prose.
    """

    full_name: str
    jersey_number: str = ""
    team: str = ""
    position: str = ""
    photo_url: str = ""
    status: str = ""
    assessment_badges: List[str] = field(default_factory=list)


@dataclass
class StatBox:
    """Small current-season or summary metric for profile headers."""

    label: str
    value: str
    context: str = ""


@dataclass
class UISection:
    """Generic renderable section.

    Section types should remain client-agnostic. Scout may render these as
    cards, panels, tabs, lists, popups, or future native UI surfaces.
    """

    section_id: str
    section_type: str
    title: str
    summary: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    children: List["UISection"] = field(default_factory=list)
    default_open: bool = True


@dataclass
class AthenaResponse:
    """Canonical response model consumed by the Experience Layer."""

    metadata: ExperienceMetadata
    intent: str
    title: str
    executive_summary: str
    key_findings: List[str] = field(default_factory=list)
    evidence: List[EvidenceItem] = field(default_factory=list)
    confidence: ConfidenceSummary = field(default_factory=ConfidenceSummary)
    limitations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    ui_sections: List[UISection] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
