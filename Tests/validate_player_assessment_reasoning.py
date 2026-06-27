"""
Athena Sports Intelligence Platform
Epic 4E.2 - Player Assessment Reasoning Validation
"""

from Reasoning.models.player_profile import PlayerProfile
from Reasoning.primitives.player_assessor import PlayerAssessor


class MockEvidence:
    def __init__(self, source_type, summary, confidence):
        self.source_type = source_type
        self.summary = summary
        self.confidence = confidence


def main():
    print("Player Assessment Reasoning Validation")
    print("======================================")

    profile = PlayerProfile(
        entity_id="34",
        name="Auston Matthews",
        position="C",
        team="Toronto Maple Leafs",
    )

    evidence = [
        MockEvidence(
            "historical",
            "Multiple seasons of elite goal production.",
            0.95,
        ),
        MockEvidence(
            "temporal",
            "Recent production remains among league leaders.",
            0.90,
        ),
        MockEvidence(
            "graph",
            "Identified as a franchise cornerstone within the knowledge graph.",
            0.92,
        ),
    ]

    assessor = PlayerAssessor()
    assessment = assessor.assess(profile, evidence)

    assert assessment is not None
    assert assessment.summary
    assert assessment.confidence > 0.0

    print("[PASS] Assessment created")
    print(f"[PASS] Summary: {assessment.summary}")
    print(f"[PASS] Confidence: {assessment.confidence:.2f}")
    print()
    print("Player Assessment Reasoning PASS")


if __name__ == "__main__":
    main()