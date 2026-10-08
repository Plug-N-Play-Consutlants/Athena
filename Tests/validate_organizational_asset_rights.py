from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_PATCH, RELEASE_HOTFIX
from Knowledge.Assets.organizational_rights_state import attach_rights_states, transaction_eligible
from Athena.intent_planner import plan_capability
assert tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 7, 7, 3, 4), ATHENA_VERSION
rows=attach_rights_states([
 {"nhl_player_id":"1","name":"Roster Player","relationship":"current_roster","team":"TOR"},
 {"nhl_player_id":"2","name":"Junior Prospect","relationship":"prospect","team":"TOR"},
 {"nhl_player_id":"3","name":"Uncontrolled Player","relationship":"eligible_player","team":"OHL"},
],"TOR")
assert transaction_eligible(rows[0])
assert not transaction_eligible(rows[1])
assert not transaction_eligible(rows[2])
assert rows[1]["rights_state"]["control_status"]=="association_only"
assert rows[1]["rights_state"]["transaction_status"]=="requires_current_rights_evidence"
assert rows[1]["rights_state"]["transferable_object"]=="none_established"
assert rows[2]["rights_state"]["transferable_object"]=="none_established"
for q in ("Who are the Maple Leafs' organizational assets?","Which Leafs prospects could actually be traded?"):
 p=plan_capability(q,"public");assert p and p.route=="public_nhl_organizational_assets",(q,p)
source=(ROOT/'Athena/Investigation/nhl_transaction.py').read_text(encoding='utf-8')
assert 'attach_rights_states' in source and 'transaction_eligible' in source
assert 'package_evaluation' in source and 'draft_capital_status' in source
print('PASS: organizational rights/control, transaction eligibility, routing, and package evaluation contracts.')
