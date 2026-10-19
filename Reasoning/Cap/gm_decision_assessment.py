"""Evidence-bounded GM choice comparison for cap inquiries.

This ranks only supplied, provenance-backed comparable metrics. A stated GM
constraint changes admissible choices, never underlying player evidence.
No ranking implies trade consent, NHL registration or daily cap compliance.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

ALLOWED_METRICS = ("offense", "defense", "roster_fit", "development", "future_flexibility", "asset_cost")

@dataclass(frozen=True)
class GMOption:
    name: str
    eligible: bool
    score: float | None
    gains: tuple[str, ...]
    costs: tuple[str, ...]
    unknowns: tuple[str, ...]

@dataclass(frozen=True)
class GMDecisionAssessment:
    options: tuple[GMOption, ...]
    preferred: str | None
    priorities: tuple[str, ...]
    def scout_summary(self) -> str:
        intro = 'GM decision comparison (supplied evidence and user priorities, not an executable trade recommendation). '
        intro += 'Priorities: ' + (', '.join(self.priorities) if self.priorities else 'none specified') + '. '
        for option in self.options:
            intro += (f'{option.name}: ' + ('excluded by GM constraint' if not option.eligible else
                     'not rankable from supplied comparable evidence' if option.score is None else
                     f'weighted evidence score {option.score:.2f}') + '. ')
            if option.gains: intro += 'Potential gains: ' + '; '.join(option.gains) + '. '
            if option.costs: intro += 'Potential costs: ' + '; '.join(option.costs) + '. '
            if option.unknowns: intro += 'Unknowns: ' + '; '.join(option.unknowns) + '. '
        intro += ('Highest supported score under supplied priorities: ' + self.preferred + '. ' if self.preferred else
                  'No supported preferred option can be established. ')
        return intro + 'Independent market consent, roster/CBA compliance and real-world outcomes are not established.'

def assess_gm_decision(scenario: Mapping[str, Any]) -> GMDecisionAssessment:
    """Compare explicit options using user-provided priorities and sourced measures.

    Each measure is a normalized comparable value in [-1, 1], with a cited
    provenance string; absent/unsourced measures cannot contribute a score.
    `asset_cost` is negative-weighted because higher cost is worse.
    """
    options = scenario.get('options')
    if not isinstance(options, list) or not options:
        raise ValueError('Nonempty GM options list required')
    priorities = scenario.get('priorities', {})
    if not isinstance(priorities, dict) or any(k not in ALLOWED_METRICS or type(v) not in (int,float) or v < 0 or v > 10 for k,v in priorities.items()):
        raise ValueError('Priorities must be nonnegative metric weights <= 10')
    protected = scenario.get('protected_players', [])
    if not isinstance(protected, list) or any(not isinstance(x,str) or not x.strip() for x in protected):
        raise ValueError('Protected players must be named')
    protected_ids = set(protected)
    results=[]; names=set()
    for item in options:
        if not isinstance(item, dict) or not isinstance(item.get('name'),str) or not item['name'].strip():
            raise ValueError('Every option requires a name')
        name=item['name'].strip()
        if name in names: raise ValueError('Duplicate option name')
        names.add(name)
        outgoing=item.get('outgoing_players', [])
        if not isinstance(outgoing,list) or any(not isinstance(x,str) for x in outgoing):
            raise ValueError('Outgoing players must be identifiers')
        eligible=not bool(protected_ids.intersection(outgoing))
        measures=item.get('measures', {})
        if not isinstance(measures,dict) or any(k not in ALLOWED_METRICS for k in measures):
            raise ValueError('Unsupported metric')
        score=0.0; weight=0.0; missing=[]
        for metric, importance in priorities.items():
            if importance == 0: continue
            evidence=measures.get(metric)
            if (not isinstance(evidence,dict) or type(evidence.get('value')) not in (int,float)
                or not -1 <= evidence['value'] <= 1 or not isinstance(evidence.get('source'),str)
                or not evidence['source'].strip()):
                missing.append('Comparable sourced ' + metric + ' estimate unavailable')
                continue
            score += importance * evidence['value'] * (-1 if metric=='asset_cost' else 1)
            weight += importance
        if not priorities or weight == 0 or missing: score_value=None
        else: score_value=round(score/weight, 4)
        def notes(key):
            val=item.get(key,[])
            if not isinstance(val,list) or any(not isinstance(x,str) for x in val):
                raise ValueError(key + ' must be a list of statements')
            return tuple(val)
        unknowns=list(notes('unknowns')) + missing
        if not eligible: unknowns.append('Option violates protected-player restriction')
        unknowns.append('Counterparty consent, CBA legality, daily cap state and transaction execution unverified')
        results.append(GMOption(name,eligible,score_value,notes('gains'),notes('costs'),tuple(unknowns)))
    ranked=[r for r in results if r.eligible and r.score is not None]
    ranked.sort(key=lambda r:(-r.score,r.name))
    preferred=ranked[0].name if ranked and (len(ranked)==1 or ranked[0].score>ranked[1].score) else None
    return GMDecisionAssessment(tuple(results), preferred, tuple(f'{k} weight {v}' for k,v in priorities.items()))
