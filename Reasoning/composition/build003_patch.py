"""Scout Build 003 patch: career identity, legacy, and baselines."""
from __future__ import annotations

from Reasoning.composition.executive_brief import ExecutiveBriefComposer
from Reasoning.composition.career_identity_enricher import CareerIdentityEnricher

_original_build003 = ExecutiveBriefComposer.build_player_brief
_enricher = CareerIdentityEnricher()


def patched_build003(self, assessment, evaluation=None, question="", mode="fantasy"):
    brief = _original_build003(self, assessment, evaluation, question, mode)
    return _enricher.enrich_player_brief(brief, assessment, evaluation or {})


ExecutiveBriefComposer.build_player_brief = patched_build003
