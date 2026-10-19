"""Bounded accounting tests: no fake team cap total and no silent LTIR assumptions."""
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from Reasoning.Cap.canonical_ledger import CapCharge, LedgerReconciliation, REQUIRED_RECONCILIATION
from Reasoning.Cap.cap_reasoning import evaluate_team_cap_state
from Knowledge.Economics.league_season_context import resolve_league_season_context

def main():
    entry=CapCharge('spc1','player1','standard_player_contract',10_000_000,'2026-07-01','2027-06-30','fixture:spc1','cba:spc')
    team=SimpleNamespace(team_id='nhl.team.test',team_name='Test Club',as_of='2026-10-16',aggregate_permitted=False)
    econ=resolve_league_season_context(league_year='2026-27')
    partial=LedgerReconciliation(team.team_id,team.as_of,(entry,),('registered_contracts',),False,'fixture:2026-10-16')
    assert partial.verified_cap_charge_total is None
    d=evaluate_team_cap_state(team,econ,canonical_ledger=partial)
    assert d.headroom is None and 'roster_reconciliation' in d.unresolved_inputs
    complete=LedgerReconciliation(team.team_id,team.as_of,(entry,),REQUIRED_RECONCILIATION,True,'fixture:2026-10-16',0)
    assert complete.verified_cap_charge_total==10_000_000
    assert complete.reconcile(11_000_000)==-1_000_000
    result=evaluate_team_cap_state(team,econ,canonical_ledger=complete)
    assert result.known_payroll==10_000_000 and result.status=='below_lower_limit'
    try:
        evaluate_team_cap_state(team,econ,canonical_ledger=LedgerReconciliation('other',team.as_of,(entry,),REQUIRED_RECONCILIATION,True,'fixture',0))
    except ValueError:pass
    else:raise AssertionError('Team mismatch must fail')
    print('PASS: canonical cap ledger completeness, provenance, reconciliation and integration')
if __name__=='__main__':main()
