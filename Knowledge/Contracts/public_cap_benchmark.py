"""Conservative public Sportsnet cap benchmark, NOT contract acquisition.

Requires operator authorization for fetching. Published aggregates are comparison
observations only: never promote them to canonical charges, LTIR relief or coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import re
from typing import Callable

from Reasoning.Cap.canonical_ledger import LedgerReconciliation

BASE = 'https://www.sportsnet.ca/hockey/nhl/teams/'
# Explicit known team-page slugs. No guessed URL or vendor private API.
TEAM_SLUGS = {
    'TOR': 'toronto-maple-leafs', 'BUF': 'buffalo-sabres',
    'OTT': 'ottawa-senators', 'MTL': 'montreal-canadiens',
    'BOS': 'boston-bruins', 'DET': 'detroit-red-wings',
    'FLA': 'florida-panthers', 'TBL': 'tampa-bay-lightning',
    'NYR': 'new-york-rangers', 'NYI': 'new-york-islanders',
    'NJD': 'new-jersey-devils', 'PHI': 'philadelphia-flyers',
    'PIT': 'pittsburgh-penguins', 'WSH': 'washington-capitals',
    'CAR': 'carolina-hurricanes', 'CBJ': 'columbus-blue-jackets',
    'CHI': 'chicago-blackhawks', 'COL': 'colorado-avalanche',
    'DAL': 'dallas-stars', 'MIN': 'minnesota-wild',
    'NSH': 'nashville-predators', 'STL': 'st-louis-blues',
    'WPG': 'winnipeg-jets', 'UTA': 'utah-mammoth',
    'ANA': 'anaheim-ducks', 'CGY': 'calgary-flames',
    'EDM': 'edmonton-oilers', 'LAK': 'los-angeles-kings',
    'SJS': 'san-jose-sharks', 'SEA': 'seattle-kraken',
    'VAN': 'vancouver-canucks', 'VGK': 'vegas-golden-knights',
}
MAX_HTML = 3_000_000

class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.depth += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self.depth:
            self.depth -= 1
    def handle_data(self, data):
        if not self.depth and data.strip():
            self.parts.append(data.strip())

@dataclass(frozen=True)
class PublishedCapBenchmark:
    team_id: str
    source_url: str
    retrieved_at: str
    projected_total: int
    projected_space: int
    cap_ceiling: int | None
    cap_space_today: int | None
    source_definition: str = 'Sportsnet published projected total cap hit; not an itemized CBA ledger'

    def compare(self, ledger: LedgerReconciliation) -> int | None:
        if ledger.team_id.upper() != self.team_id:
            raise ValueError('Benchmark and ledger team mismatch')
        return ledger.reconcile(self.projected_total)


def _money(value: str) -> int:
    return int(value.replace(',', '').replace('$', '').strip())


def parse_sportsnet_cap_page(team_id: str, html: str, *, retrieved_at: str) -> PublishedCapBenchmark:
    team_id = team_id.upper()
    if team_id not in TEAM_SLUGS:
        raise ValueError('Unsupported team identifier')
    datetime.fromisoformat(retrieved_at.replace('Z', '+00:00'))
    if not html or len(html.encode('utf-8')) > MAX_HTML:
        raise ValueError('Empty or oversized published cap page')
    parser = _VisibleText()
    parser.feed(html)
    text = ' '.join(parser.parts)
    text = re.sub(r'\s+', ' ', unescape(text))
    # Limit to the salary section, not unrelated figures in news or adverts.
    start = text.find('TEAM SALARY')
    if start < 0:
        raise ValueError('Sportsnet salary section not found')
    text = text[start:start + 2500]
    def extract(label: str, *, required: bool = True) -> int | None:
        match = re.search(r'\b' + re.escape(label) + r'\s*(-?\$[\d,]+)', text, re.I)
        if not match:
            if required:
                raise ValueError(f'Missing published field: {label}')
            return None
        return int(match.group(1).replace('$', '').replace(',', ''))
    total = extract('PROJECTED TOTAL CAP HIT')
    space = extract('PROJECTED CAP SPACE')
    today = extract('CAP SPACE TODAY', required=False)
    ceiling_match = re.search(r'SALARY CAP:\s*\$([\d.]+)\s*(M|B)', text, re.I)
    ceiling = None
    if ceiling_match:
        ceiling = round(float(ceiling_match.group(1)) * (1_000_000 if ceiling_match.group(2).upper() == 'M' else 1_000_000_000))
    # Published projected space and total must reconcile with the page's ceiling
    # where one is present. Do not silently accept a changed page structure.
    if ceiling is not None and abs(total + space - ceiling) > 2:
        raise ValueError('Published total and space do not reconcile to ceiling')
    return PublishedCapBenchmark(team_id, BASE + TEAM_SLUGS[team_id] + '/', retrieved_at,
                                 total, space, ceiling, today)


def acquire_sportsnet_cap_benchmark(team_id: str, *, authorized: bool = False,
                                     transport: Callable | None = None,
                                     retrieved_at: str | None = None) -> PublishedCapBenchmark:
    """One explicitly requested read; no background crawl, scheduling or bypass.

    Operator must verify publisher terms/robots before setting authorized=True.
    Test transport is injectable. Redirects are refused; no login/cookies.
    """
    team_id = team_id.upper()
    if not authorized:
        raise PermissionError('Verify source access permission before fetching')
    if team_id not in TEAM_SLUGS:
        raise ValueError('Unsupported team identifier')
    if transport is None:
        import requests
        transport = requests.get
    url = BASE + TEAM_SLUGS[team_id] + '/'
    response = transport(url, timeout=15, allow_redirects=False,
                         headers={'Accept': 'text/html', 'User-Agent': 'AthenaEngine-cap-reconciliation/1'})
    if response.status_code != 200:
        raise ValueError(f'Benchmark source returned HTTP {response.status_code}')
    if len(response.content) > MAX_HTML:
        raise ValueError('Benchmark response exceeds size limit')
    html = response.content.decode('utf-8', errors='strict')
    return parse_sportsnet_cap_page(team_id, html, retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat())
