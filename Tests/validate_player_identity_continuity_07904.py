"""Regression: missing current roster cannot erase verified identity or invent rights."""
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from Knowledge.Organizations import nhl_roster_evidence as ev
from Athena.player_development import _named_player
from Knowledge.Assets.organizational_rights_state import attach_rights_states

class FakeClient:
    def get_roster_seasons(self, team): return [20252026]
    def get_roster(self, team, season):
        return {"forwards": [{"id": 1234567, "firstName":{"default":"Sample"}, "lastName":{"default":"Player"}}]}

with TemporaryDirectory() as tmp:
    with patch.object(ev, '_identity_snapshot_path', lambda team: Path(tmp) / 'TOR.json'):
        ev._write_identity_snapshot('TOR', [{'name':'Prior Prospect','nhl_player_id':'7777777'}])
        cached=ev.acquire_historical_player_identities('TOR', FakeClient(), max_seasons=0)
        assert _named_player('How has Prior Prospect developed?',cached)['nhl_player_id']=='7777777'
        all_candidates=ev.acquire_historical_player_identities('TOR',FakeClient())
        assert _named_player('Sample Player development',all_candidates)['nhl_player_id']=='1234567'
        rights=attach_rights_states(all_candidates,'TOR')
        assert all(p['rights_state']['control_status'] != 'controlled' for p in rights)
        assert all(p['rights_state']['transaction_status'] == 'not_eligible_without_control_evidence' for p in rights)
print('PASS: snapshot continuity, historical NHL identity fallback, no fabricated current control')
