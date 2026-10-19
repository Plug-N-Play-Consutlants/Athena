"""Conservative Cap Freeze observations from operator-supplied text snapshots.

No crawler, automated website fetch, permission inference or canonical completeness
certification. This is a publisher observation, not a verified CBA ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Mapping

MAX_TEXT = 1_000_000
MONEY = re.compile(r'^\$(-?[\d,]+)$')
ROW = re.compile(r'^(.+?)\s*\|\s*([A-Z]{0,3})\s*\|\s*(\d{1,2})\s*\|\s*(\$[\d,]+|UFA|RFA|—)\s*\|')
SECTIONS = {
    'Forwards': 'active_roster_observation',
    'Defense': 'active_roster_observation',
    'Goalies': 'active_roster_observation',
    'Dead Cap': 'dead_cap_observation',
    'Unsigned RFAs': 'unsigned_rights_observation',
    'Non-Roster / Minors': 'non_roster_observation',
}

@dataclass(frozen=True)
class ContractObservation:
    player: str
    position: str
    category: str
    season_cap_hit: int | None
    source_url: str

@dataclass(frozen=True)
class CapFreezeObservation:
    team_id: str
    season: str
    source_url: str
    source_as_of: str
    retrieved_at: str
    published_total: int
    published_space: int
    cap_ceiling: int
    ltir_pool: int | None
    potential_bonuses: int | None
    contracts: tuple[ContractObservation, ...]
    category_totals: Mapping[str, int]
    warnings: tuple[str, ...]
    complete_cba_ledger: bool = False

    def observed_cap_total(self) -> int:
        return sum(row.season_cap_hit or 0 for row in self.contracts
                   if row.category in ('active_roster_observation', 'dead_cap_observation'))


def _money(text: str) -> int:
    match = MONEY.fullmatch(text.strip())
    if not match:
        raise ValueError('Expected an exact dollar amount')
    return int(match.group(1).replace(',', ''))


def parse_capfreeze_team_text(team_id: str, text: str, *, source_url: str,
                              retrieved_at: str) -> CapFreezeObservation:
    """Parse a *supplied* plain-text team page, not arbitrary HTML or live URLs.

    Requires the page's explicit data-as-of date. Distinguishes stale source
    observations from retrieval time and never treats minors as active charges.
    """
    team_id = team_id.upper()
    if not re.fullmatch(r'[A-Z]{3}', team_id):
        raise ValueError('Invalid NHL team code')
    if not re.fullmatch(r'https://(?:www\.)?capfreeze\.com/teams/[a-z0-9-]+\.html', source_url):
        raise ValueError('Unexpected Cap Freeze source URL')
    datetime.fromisoformat(retrieved_at.replace('Z', '+00:00'))
    if not text or len(text.encode('utf-8')) > MAX_TEXT:
        raise ValueError('Empty or oversized source snapshot')
    lines = [re.sub(r'^L\d+:\s*', '', line).strip() for line in text.splitlines()]
    header = next((line for line in lines if re.search(r'^#\s+' + team_id + r'\s', line)), None)
    if not header:
        raise ValueError('Team identity not established in source')
    season_match = re.search(r'\b(20\d\d-\d\d)\b', '\n'.join(lines[:20]))
    as_of_match = re.search(r'Data as of\s+([A-Z][a-z]+ \d{1,2}, 20\d\d)', text)
    if not season_match or not as_of_match:
        raise ValueError('Missing season or source data-as-of date')
    season = season_match.group(1)
    source_as_of = date.fromisoformat(datetime.strptime(as_of_match.group(1), '%B %d, %Y').date().isoformat()).isoformat()
    if source_as_of > datetime.fromisoformat(retrieved_at.replace('Z', '+00:00')).date().isoformat():
        raise ValueError('Source date cannot follow retrieval date')
    def field(label: str, required=True) -> int | None:
        for i, line in enumerate(lines):
            if line.casefold() == label.casefold():
                for nxt in lines[i+1:i+4]:
                    if MONEY.fullmatch(nxt):
                        return _money(nxt)
                break
        if required:
            raise ValueError(f'Missing {label}')
        return None
    total = field('Projected Cap Hit')
    space = field('Projected Cap Space')
    ltir = field('LTIR Pool', False)
    bonuses = field('Potential Bonuses', False)
    ceiling_match = re.search(r'Upper Limit\s+\$([\d,]+)', text)
    if not ceiling_match:
        raise ValueError('Missing source cap ceiling')
    ceiling = int(ceiling_match.group(1).replace(',', ''))
    if total + space != ceiling:
        raise ValueError('Published total/space/ceiling mismatch')
    category = None
    rows = []
    totals = {}
    warnings = []
    for line in lines:
        if line.startswith('## '):
            category = None
            for prefix, value in SECTIONS.items():
                if line[3:].startswith(prefix + ' '):
                    category = value
                    group_total = re.search(r'\$[\d,]+\s*$', line)
                    if group_total:
                        totals[prefix] = _money(group_total.group())
                    break
            continue
        if category is None:
            continue
        # Web text snapshots may contain Markdown link annotations.
        cleaned = re.sub(r'【\d+†([^】]+)】', r'\1', line)
        match = ROW.match(cleaned)
        if not match:
            continue
        name, position, _age, value = match.groups()
        amount = _money(value) if value.startswith('$') else None
        rows.append(ContractObservation(name.strip(), position, category, amount, source_url))
    if not rows:
        raise ValueError('No itemized contracts found')
    observed = sum(x.season_cap_hit or 0 for x in rows if x.category in
                   ('active_roster_observation', 'dead_cap_observation'))
    if observed != total:
        warnings.append(f'Observed roster/dead-cap sum {observed} differs from published total {total}')
    if ltir:
        warnings.append('Published LTIR pool is not a verified CBA relief calculation')
    warnings.append('Contract rows are publisher estimates; independently verify identities, roster status and CBA adjustments')
    return CapFreezeObservation(team_id, season, source_url, source_as_of, retrieved_at,
                                total, space, ceiling, ltir, bonuses, tuple(rows), totals,
                                tuple(warnings))
