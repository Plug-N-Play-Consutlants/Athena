from Reasoning.models.player_profile import PlayerProfile
from Reasoning.primitives.player_assessment_builder import PlayerAssessmentBuilder

profile=PlayerProfile(entity_id="34",name="Auston Matthews")
findings=[{"statement":"Elite scoring","confidence":0.95}]
assessment=PlayerAssessmentBuilder().build(profile,findings)
assert "Auston Matthews" in assessment.summary
print("Player Narrative PASS")
