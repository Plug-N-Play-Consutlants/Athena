from Reasoning.reasoning_engine import ReasoningEngine
from Reasoning.reasoning_request import ReasoningRequest
from Reasoning.models.player_profile import PlayerProfile

profile=PlayerProfile(entity_id="34",name="Auston Matthews")
req=ReasoningRequest(reasoning_type="player_assessment",subject=profile,evidence_bundle=[])
result=ReasoningEngine().reason(req)
assert hasattr(result,"summary")
print("Player Reasoning Engine PASS")
