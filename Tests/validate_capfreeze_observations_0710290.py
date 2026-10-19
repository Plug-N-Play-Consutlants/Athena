from datetime import datetime
from Knowledge.Contracts.capfreeze_observations import parse_capfreeze_team_text

SAMPLE = '''# TOR Toronto Maple Leafs
Eastern Conference • Atlantic Division • 2026-27
Projected Cap Hit
$16,000,000
Projected Cap Space
$88,000,000
LTIR Pool
$2,000,000
Potential Bonuses
$300,000
## Forwards 1 $13,000,000
Player | Pos | Age | 2026-27 | 2027-28 | % of Cap
Auston Example | C | 29 | $13,000,000 | UFA | 12.5%
## Dead Cap — Buyouts, Retained, Buried & Overages 1 $3,000,000
Player | Pos | Age | 2026-27 | 2027-28 | % of Cap
Other Example | LW | 31 | $3,000,000 | UFA | 2.9%
## Non-Roster / Minors 1 $900,000
Player | Pos | Age | 2026-27 | 2027-28 | % of Cap
Minor Example | C | 21 | $900,000 | RFA | 0.9%
Data as of October 8, 2026 • 2026-27 Upper Limit $104,000,000 / Lower Limit $76,900,000
'''
URL = 'https://capfreeze.com/teams/toronto-maple-leafs.html'
def main():
    parsed = parse_capfreeze_team_text('TOR', SAMPLE, source_url=URL, retrieved_at='2026-10-17T00:00:00Z')
    assert len(parsed.contracts) == 3
    assert parsed.observed_cap_total() == 16000000
    assert parsed.complete_cba_ledger is False
    assert parsed.ltir_pool == 2000000
    assert parsed.source_as_of == '2026-10-08'
    for kwargs in [dict(team_id='MTL'), dict(source_url='https://example.com/x'),
                   dict(retrieved_at='2026-10-01T00:00:00Z')]:
        params = dict(team_id='TOR', text=SAMPLE, source_url=URL, retrieved_at='2026-10-17T00:00:00Z')
        params.update(kwargs)
        try: parse_capfreeze_team_text(**params)
        except ValueError: pass
        else: raise AssertionError('Invalid input accepted: ' + str(kwargs))
    try: parse_capfreeze_team_text('TOR', SAMPLE.replace('$88,000,000', '$80,000,000'), source_url=URL, retrieved_at='2026-10-17T00:00:00Z')
    except ValueError: pass
    else: raise AssertionError('Inconsistent totals accepted')
    print('PASS Cap Freeze observation extraction (offline source fixture)')
if __name__ == '__main__': main()
