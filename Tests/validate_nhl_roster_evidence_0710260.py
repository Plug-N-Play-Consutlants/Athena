from __future__ import annotations
import json
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Knowledge.Contracts.nhl_roster_evidence import acquire_nhl_roster, reconcile_contract_roster


def run():
    roster_json = {'forwards':[{'id':1,'firstName':{'default':'Test'},'lastName':{'default':'Forward'}}],
                   'defensemen':[{'id':2,'firstName':{'default':'Test'},'lastName':{'default':'Defense'}}],
                   'goalies':[{'id':3,'firstName':{'default':'Test'},'lastName':{'default':'Goalie'}}]}
    def transport(url, **kwargs):
        assert url == 'https://api-web.nhle.com/v1/roster/TOR/current'
        assert kwargs['allow_redirects'] is False
        return SimpleNamespace(status_code=200, content=json.dumps(roster_json).encode())
    roster = acquire_nhl_roster('TOR', transport=transport, acquired_at='2026-10-16T12:00:00Z')
    assert len(roster.players) == 3
    comparison = reconcile_contract_roster({'team_id':'TOR', 'obligations':[
        {'status':'active_roster_spc','nhl_player_id':1,'subject_id':'1'}]}, roster)
    assert comparison['matched_count'] == 1
    assert len(comparison['roster_without_active_spc']) == 2
    assert comparison['cap_ledger_complete'] is False
    for bad in ('TOR/current','tor','127.0.0.1'):
        try: acquire_nhl_roster(bad, transport=transport)
        except ValueError: pass
        else: raise AssertionError('Unsafe team input accepted')
    try: reconcile_contract_roster({'team_id':'EDM','obligations':[]}, roster)
    except ValueError: pass
    else: raise AssertionError('Cross-team reconciliation accepted')
    print('PASS NHL roster acquisition and cap evidence reconciliation')

if __name__ == '__main__': run()
