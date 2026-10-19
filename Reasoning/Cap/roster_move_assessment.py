"""Evidence-bounded roster move arithmetic; not a waiver or LTIR eligibility oracle.

Two-way salary terms are deliberately independent of AAV and waiver status.
Unknown eligibility is a blocking unknown, never interpreted as permission.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any

@dataclass(frozen=True)
class RosterMoveAssessment:
    action: str
    annual_cap_delta: int | None
    permissible: bool | None
    findings: tuple[str, ...]
    unresolved: tuple[str, ...]

    def scout_summary(self) -> str:
        change = ('unknown' if self.annual_cap_delta is None else
                  f'${self.annual_cap_delta:+,} annualized cap-charge change')
        verdict = ('not established' if self.permissible is None else
                   'supported by supplied eligibility evidence' if self.permissible else
                   'blocked by supplied eligibility evidence')
        return (f'{self.action}: {change}; eligibility {verdict}. '
                + ' '.join(self.findings)
                + (' Unresolved: ' + '; '.join(self.unresolved) + '.' if self.unresolved else ''))

def assess_roster_move(move: Mapping[str, Any], *, minor_league_exemption: int) -> RosterMoveAssessment:
    """Evaluate a proposed assignment or recall using explicitly verified inputs.

    Inputs are annualized cap-charge effects, not daily cap-space projections.
    This cannot establish roster-limit compliance, LTIR treatment or whether
    the actual move has been registered with the NHL.
    """
    if type(minor_league_exemption) is not int or minor_league_exemption < 0:
        raise ValueError('A sourced nonnegative burial exemption is required')
    action = move.get('action')
    if action not in ('assign_to_minors', 'recall_to_nhl'):
        raise ValueError('Unsupported roster action')
    if not isinstance(move.get('player_id'), str) or not move['player_id'].strip():
        raise ValueError('Stable player identity required')
    unresolved=[]; findings=[]
    aav=move.get('verified_aav')
    if type(aav) is not int or aav < 0 or not move.get('aav_source'):
        delta=None
        unresolved.append('Verified NHL contract AAV and provenance required')
    else:
        buried=max(0,aav-minor_league_exemption)
        delta=(buried-aav) if action=='assign_to_minors' else (aav-buried)
        findings.append('Annualized charge only; actual daily impact depends on transaction date and cap state.')
    if 'nhl_salary' in move or 'minor_salary' in move:
        findings.append('Two-way salary rates do not independently determine cap AAV or waiver eligibility.')
    if move.get('eligibility_verified') is not True:
        permissible=None
        unresolved.append('Move eligibility has not been independently verified')
    else:
        flags=('waiver_clearance_or_exemption', 'roster_limit_compliance',
               'contract_assignment_or_recall_permitted')
        missing=[f for f in flags if type(move.get(f)) is not bool]
        if missing:
            permissible=None
            unresolved.append('Missing verified eligibility flags: ' + ', '.join(missing))
        else:
            permissible=all(move[f] for f in flags)
            if not permissible:
                findings.append('At least one required eligibility condition is not met.')
    if move.get('ltir_applicable'):
        unresolved.append('LTIR relief and pool impact require separate dated CBA accounting')
    return RosterMoveAssessment(action,delta,permissible,tuple(findings),tuple(unresolved))


@dataclass(frozen=True)
class SequencedRosterAssessment:
    steps: tuple[RosterMoveAssessment, ...]
    annual_cap_delta: int | None
    executable: bool | None
    unresolved: tuple[str, ...]

    def scout_summary(self) -> str:
        total = ('unknown' if self.annual_cap_delta is None else
                 f'${self.annual_cap_delta:+,} annualized')
        return (f'Sequenced roster actions: {total} combined cap-charge change. '
                + ' '.join(f'Step {i}: {step.scout_summary()}' for i, step in enumerate(self.steps, 1))
                + (' Sequence unresolved: ' + '; '.join(self.unresolved) + '.' if self.unresolved else ''))


def assess_roster_sequence(moves: list[Mapping[str, Any]], *, minor_league_exemption: int) -> SequencedRosterAssessment:
    """Combine independently evaluated moves without implying daily cap feasibility.

    Each step must be lawful *at its execution time*; the annualized sum alone
    cannot certify intermediate cap space, roster limits or transaction order.
    """
    if not moves:
        raise ValueError('At least one proposed move required')
    steps = tuple(assess_roster_move(m, minor_league_exemption=minor_league_exemption) for m in moves)
    total = (sum(s.annual_cap_delta for s in steps)
             if all(s.annual_cap_delta is not None for s in steps) else None)
    executable = (False if any(s.permissible is False for s in steps) else
                  True if all(s.permissible is True for s in steps) else None)
    unresolved = ['Intermediate daily cap position and transaction timing not verified',
                  'Sequence-level roster and CBA compliance not independently established']
    for index, step in enumerate(steps, 1):
        unresolved.extend(f'Step {index}: {issue}' for issue in step.unresolved)
    return SequencedRosterAssessment(steps, total, executable, tuple(dict.fromkeys(unresolved)))
