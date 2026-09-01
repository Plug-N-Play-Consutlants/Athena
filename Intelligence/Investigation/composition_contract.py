"""Composition instructions emitted by investigation strategy.

The contract shapes presentation but contains no reasoning or evidence generation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class CompositionContract:
    profile: str
    depth: str
    preserve_rich_output: bool
    preferred_sections: Tuple[str, ...]
    discovery_mode: str

    @classmethod
    def from_strategy(cls, strategy) -> "CompositionContract":
        sections = {
            "brief_update": ("result", "quick_context", "discovery"),
            "news_update": ("headline", "what_changed", "freshness", "why_it_matters", "sources", "discovery"),
            "entity_profile": ("profile_header", "analysis", "stats", "history", "evidence", "confidence", "discovery"),
            "comparison_experience": ("executive_comparison", "framework", "strengths", "tradeoffs", "historical_context", "evidence", "confidence", "discovery"),
            "investigation_experience": ("executive_summary", "key_findings", "context", "supporting_evidence", "contradictory_evidence", "confidence", "limitations", "open_questions", "discovery"),
            "advisory_experience": ("assessment", "options", "tradeoffs", "evidence", "confidence", "limitations", "discovery"),
        }.get(strategy.composition_profile, ("summary", "evidence", "confidence", "discovery"))
        return cls(strategy.composition_profile, strategy.depth, strategy.preserve_rich_output, sections, strategy.discovery_mode)
