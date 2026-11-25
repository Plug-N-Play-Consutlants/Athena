"""Safe, read-only diagnostic of Fantrax's player-period scoring contract.

This deliberately DOES NOT treat a BY_PERIOD selector as proof of an
individual fantasy scoring week or write a credited scoring ledger.
Usage (from repository root):
    python Tools/fantrax_period_probe.py --season 2026 --period 8
The report excludes player rows, names, IDs, cookies, and raw payloads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Athena.Investigation.period_evidence_acquisition import inspect_player_stats_schema


def _season_label(season: str) -> str:
    start = str(season).strip()
    if start.isdecimal() and len(start) == 4:
        year = int(start)
        return f'{year}-{(year + 1) % 100:02}'
    return start


def _select_code(metadata: list, season: str) -> str | None:
    label = _season_label(season)
    matches = [item.get('code') for item in metadata
               if isinstance(item, dict) and item.get('name', '').startswith(label + ' ')
               and str(item.get('code', '')).endswith('_BY_PERIOD')]
    return matches[0] if len(matches) == 1 else None


def _anonymous_fpts_signature(payload: dict) -> dict:
    """Compare provider FPts cells without emitting player-level or roster data.

    A different hash is *evidence of a changed response*, NOT verified period
    identity or credited team scoring. Hashes exclude identities entirely.
    """
    data = payload.get('data', payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return {'usable': False, 'reason': 'no_data_object'}
    header = data.get('tableHeader', {})
    cells = header.get('cells', []) if isinstance(header, dict) else []
    fpts = [i for i, cell in enumerate(cells) if isinstance(cell, dict)
            and cell.get('key') == 'fpts']
    if len(fpts) != 1:
        return {'usable': False, 'reason': 'fpts_column_unresolved'}
    rows = data.get('statsTable', [])
    if not isinstance(rows, list):
        return {'usable': False, 'reason': 'no_stats_table'}
    values = []
    for row in rows:
        item = row.get('cells') if isinstance(row, dict) else None
        if not isinstance(item, list) or len(item) <= fpts[0]:
            continue
        cell = item[fpts[0]]
        # The provider's FPts cell can contain nested presentation metadata.
        # Hash only the cell's scalar value; never emit the cell or player.
        if isinstance(cell, dict):
            cell = cell.get('value')
        if isinstance(cell, (int, float)) and not isinstance(cell, bool):
            values.append(str(cell))
        elif isinstance(cell, str) and len(cell) <= 24 and cell.replace('.', '', 1).replace('-', '', 1).isdigit():
            values.append(cell)
    canonical = json.dumps(sorted(values), separators=(',', ':'))
    return {'usable': bool(values), 'rows_with_fpts': len(values),
            'fingerprint': hashlib.sha256(canonical.encode()).hexdigest()[:16] if values else None}


def _period_candidate_params(code: str, period: int) -> dict:
    """Read-only *candidate*, based on Fantrax's published export query.

    This is not yet a verified `getPlayerStats` request contract. Do not
    interpret response differences as certification of a scoring period.
    """
    return {'seasonOrProjection': code, 'timeframeTypeCode': 'BY_PERIOD',
            'transactionPeriod': period, 'timeStartType': 'PERIOD_ONLY'}


def probe(*, league: str, season: str, period: int, client_factory=None) -> dict:
    if not league or not str(season).strip() or type(period) is not int or period < 1:
        raise ValueError('League, season, and positive period are required')
    if client_factory is None:
        from Providers.Fantrax.fantrax_client import FantraxClient
        client_factory = FantraxClient
    report = {'schema': 'athena.fantrax_period_probe.v1',
              'requested_season': str(season), 'requested_period': period,
              'status': 'not_attempted', 'verified_period_credit': False,
              'ledger_written': False}
    try:
        client = client_factory(league_id=league, season=season)
        if not client.has_cookie_auth():
            report['status'] = 'authentication_unavailable'
            return report
        initial = client.get_player_stats(params={})
        if client.is_error_payload(initial):
            report['status'] = 'provider_error'
            return report
        initial_schema = inspect_player_stats_schema(initial)
        code = _select_code(initial_schema.get('season_option_metadata', []), season)
        report['discovered_period_selector'] = code
        report['initial_schema'] = initial_schema
        if not code:
            report['status'] = 'period_selector_unresolved'
            return report
        selected = client.get_player_stats(params={'seasonOrProjection': code})
        if client.is_error_payload(selected):
            report['status'] = 'provider_error'
            return report
        report['selected_schema'] = inspect_player_stats_schema(selected)
        report['contract_comparison'] = {
            'selector_sent': code,
            'requested_period_transmitted': False,
            'initial_rows': initial_schema.get('statsTable_count'),
            'selected_rows': report['selected_schema'].get('statsTable_count'),
            'response_period_identity_present': False,
            'selection_flags_present': any(
                report['selected_schema'].get('seasonOrProjections_selection_flags', {}).values()
            ),
            'validation': 'unverified',
        }
        # Differential probe based on independently observed downloadPlayerStats
        # request fields; the fxpa request method may ignore these fields.
        # A second period is a negative control, not a second scoring claim.
        other_period = period - 1 if period > 1 else period + 1
        candidates = []
        for requested in (period, other_period):
            params = _period_candidate_params(code, requested)
            try:
                response = client.get_player_stats(params=params)
                if client.is_error_payload(response):
                    candidates.append({'period': requested, 'status': 'provider_error'})
                    continue
                candidates.append({'period': requested, 'status': 'response_received',
                                   'rows': inspect_player_stats_schema(response).get('statsTable_count'),
                                   'fpts_signature': _anonymous_fpts_signature(response)})
            except Exception as candidate_exc:
                candidates.append({'period': requested, 'status': 'request_failed',
                                   'exception_type': type(candidate_exc).__name__})
        signatures = [item.get('fpts_signature', {}) for item in candidates]
        comparable = (len(signatures) == 2 and all(item.get('usable') for item in signatures))
        differing = comparable and signatures[0]['fingerprint'] != signatures[1]['fingerprint']
        report['candidate_contract'] = {
            'source': 'observed_downloadPlayerStats_query_not_verified_fxpa_getPlayerStats',
            'candidate_field_names': ['seasonOrProjection', 'timeframeTypeCode',
                                      'transactionPeriod', 'timeStartType'],
            'requested_period': period, 'control_period': other_period,
            'comparisons': candidates,
            'different_anonymous_fpts_distributions': bool(differing),
            'inference': ('responses_differ_contract_still_unverified' if differing
                          else 'no_demonstrated_period_specific_difference'),
            'credit_eligible': False,
        }
        report['status'] = 'period_identity_unverified' 
        report['reason'] = ('A BY_PERIOD season selector alone does not identify the requested '
                            'scoring period or establish roster-credited player FPts. '
                            'A bounded differential probe using fields observed on the Fantrax '
                            'stats export is diagnostic only. Verify the fxpa request/response '
                            'contract and scoring-period identity before ledger writes.')
    except Exception as exc:
        # Never print exception text: HTTP failures can include authenticated URLs.
        report['status'] = 'probe_failed'
        report['exception_type'] = type(exc).__name__
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--league', help='League ID (defaults to configured workspace)')
    parser.add_argument('--season', required=True, help='Start year (e.g. 2026)')
    parser.add_argument('--period', required=True, type=int)
    parser.add_argument('--output', type=Path, help='Write SAFE schema diagnostic JSON')
    args = parser.parse_args(argv)
    if args.league:
        league = args.league
    else:
        from Core.config import get_workspace_value
        league = str(get_workspace_value('workspace.league_id', '') or '')
    report = probe(league=league, season=args.season, period=args.period)
    output = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + '\n', encoding='utf-8')
        print(f'Safe diagnostic written: {args.output}')
    else:
        print(output)
    return 0 if report['status'] == 'period_identity_unverified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
