from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION
from Providers.NHL.capabilities import supports
from Knowledge.Organizations.nhl_roster_evidence import normalize_team_player_evidence
from Athena.Investigation.state import InvestigationState
assert tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 7, 7, 3, 4), ATHENA_VERSION
for cap in ("current_roster","historical_roster","prospects","club_stats_current","goalie_summary"):assert supports(cap),cap
roster={"forwards":[{"id":1,"firstName":{"default":"Test"},"lastName":{"default":"Center"},"positionCode":"C","shootsCatches":"L","birthDate":"2003-01-01"}],"defensemen":[],"goalies":[]}
prospects={"prospects":[{"id":2,"firstName":{"default":"Young"},"lastName":{"default":"Prospect"},"positionCode":"D","shootsCatches":"R","birthDate":"2007-01-01"}]}
stats={"skaters":[{"playerId":1,"gamesPlayed":10,"goals":5,"assists":7,"points":12,"avgTimeOnIcePerGame":1200}]}
org=normalize_team_player_evidence("TOR",roster,prospects,stats)
assert org["counts"]["roster"]==1 and org["counts"]["prospects"]==1,org
assert org["roster"][0]["points"]==12 and org["roster"][0]["shoots_catches"]=="L",org
inv=InvestigationState(inquiry={});inv.require("current_roster");inv.mark("current_roster","acquisition_required",provider="NHL.com");inv.mark("current_roster","acquired_from_provider",provider="NHL.com",evidence="roster")
assert inv.requirements["current_roster"].status=="acquired_from_provider"
app=(ROOT/'Scout/app.py').read_text(encoding='utf-8')
assert 'Scout responses appear here. The newest response appears just above the prompt.' not in app
handler=(ROOT/'Athena/capability_handlers.py').read_text(encoding='utf-8')
assert 'investigate_nhl_transaction' in handler and 'investigation_state' in handler
print('PASS: whole-picture investigation contract, NHL provider expansion, normalization, and UI cleanup.')

# Investigation completion must not stop at candidate discovery.
import Athena.Investigation.nhl_transaction as tx
sample=[
 {"name":"Recent First","nhl_player_id":"10","age":18,"relationship":"prospect","draft":{"overall_pick":1},"position":"C"},
 {"name":"Young Scorer","nhl_player_id":"11","age":21,"relationship":"current_roster","points":55,"games_played":70,"position":"R"},
 {"name":"Depth Asset","nhl_player_id":"12","age":26,"relationship":"current_roster","points":20,"games_played":70,"position":"D"},
]
for x in sample:x["fit_signals"]=tx._candidate_signals(x)
package=tx._construct_package(sample,"Target Star")
assert package["status"]=="constructed_from_current_evidence" and package["assets"][0]=="Recent First",package
assert "first-overall draft pedigree" in sample[0]["fit_signals"],sample[0]
composition=(ROOT/'Scout/conversation/composition.py').read_text(encoding='utf-8')
for phrase in ('Scenario Assessment','Assets on the Table','Proposed Construction',"Athena's Verdict"):
    assert phrase in composition, phrase
assert 'Strongest named construction from current evidence:' not in composition
assert 'Build the strongest named package from current evidence' not in composition
print('PASS: significance escalation and named-package completion contract.')
