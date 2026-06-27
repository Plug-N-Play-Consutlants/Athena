from Reasoning.models.player_profile import PlayerProfile
from Reasoning.primitives.player_assessor import PlayerAssessor

p=PlayerProfile(entity_id="1",name="Test Player")
a=PlayerAssessor().assess(p)
assert a.summary
print("Player Assessment Models PASS")
