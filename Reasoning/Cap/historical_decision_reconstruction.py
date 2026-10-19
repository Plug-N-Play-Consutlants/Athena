"""Evidence-bounded reconstruction of past management decisions.

Never infer a GM's private intent from outcomes or contemporary commentary.
Keep contemporaneous knowledge separate from subsequent observations.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

@dataclass(frozen=True)
class HistoricalDecisionAssessment:
    decision: str
    decision_date: str
    contemporaneous: tuple[str, ...]
    confirmed_intent: tuple[str, ...]
    plausible_rationales: tuple[str, ...]
    later_outcomes: tuple[str, ...]
    unknowns: tuple[str, ...]
    def scout_summary(self) -> str:
        sections = [f'Historical decision: {self.decision} ({self.decision_date}).']
        for title, items in [('Evidence available at the time',self.contemporaneous),
                             ('Documented management rationale',self.confirmed_intent),
                             ('Possible interpretations, not established motives',self.plausible_rationales),
                             ('Subsequent observations, not evidence of original intent',self.later_outcomes),
                             ('Unresolved questions',self.unknowns)]:
            sections.append(title + ': ' + ('; '.join(items) if items else 'not established') + '.')
        return ' '.join(sections) + ' Outcomes do not by themselves establish whether the original decision was reasonable.'

def reconstruct_historical_decision(payload: Mapping[str, Any]) -> HistoricalDecisionAssessment:
    if not isinstance(payload, Mapping): raise ValueError('Decision must be a mapping')
    name = payload.get('decision')
    if not isinstance(name,str) or not name.strip(): raise ValueError('Named decision required')
    try: decision_date = date.fromisoformat(payload['decision_date'])
    except (KeyError,TypeError,ValueError) as exc: raise ValueError('Valid decision_date YYYY-MM-DD required') from exc
    contemporary=[]; intent=[]; interpretations=[]; outcomes=[]
    records=payload.get('evidence',[])
    if not isinstance(records,list): raise ValueError('Evidence must be a list')
    for entry in records:
        if not isinstance(entry,Mapping): raise ValueError('Evidence entries must be mappings')
        kind=entry.get('kind'); statement=entry.get('statement'); source=entry.get('source')
        if kind not in ('contemporary','management_statement','observer_interpretation','subsequent_outcome'):
            raise ValueError('Unsupported evidence kind')
        if any(not isinstance(v,str) or not v.strip() for v in (statement,source)):
            raise ValueError('Each evidence item needs a statement and source')
        try: published=date.fromisoformat(entry['published_date'])
        except (KeyError,TypeError,ValueError) as exc: raise ValueError('Evidence needs published_date YYYY-MM-DD') from exc
        if kind in ('contemporary','management_statement') and published > decision_date:
            raise ValueError('Post-decision evidence cannot be classified as known at decision time')
        if kind == 'subsequent_outcome' and published < decision_date:
            raise ValueError('Outcome cannot precede decision')
        note=f'{statement.strip()} [source: {source.strip()}, {published.isoformat()}]'
        if kind=='contemporary': contemporary.append(note)
        elif kind=='management_statement':
            if entry.get('direct_evidence_of_intent') is True: intent.append(note)
            else: interpretations.append('Management statement without verified direct intent: '+note)
        elif kind=='observer_interpretation': interpretations.append(note)
        else: outcomes.append(note)
    unknowns=payload.get('unknowns',[])
    if not isinstance(unknowns,list) or any(not isinstance(x,str) or not x.strip() for x in unknowns):
        raise ValueError('Unknowns must be nonempty strings')
    if not intent: unknowns=[*unknowns,'Management objectives and private deliberations are not established']
    if not contemporary: unknowns=[*unknowns,'Contemporaneous evidence is insufficient to reconstruct the original decision context']
    return HistoricalDecisionAssessment(name.strip(),decision_date.isoformat(),tuple(contemporary),tuple(intent),tuple(interpretations),tuple(outcomes),tuple(dict.fromkeys(unknowns)))
