"""Safe, read-only diagnostic of Fantrax's player-period scoring contract.

This deliberately DOES NOT treat a BY_PERIOD selector as proof of an
individual fantasy scoring week or write a credited scoring ledger.
Usage (from repository root):
    python Tools/fantrax_period_probe.py --season 2026 --period 8
The report excludes player rows, names, IDs, cookies, raw values, and raw payloads.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
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


# Only these representation labels may be reported. Never emit cell values or
# arbitrary provider keys (which may contain names, credentials or user text).
_SAFE_CELL_FIELDS = frozenset(("value", "text", "display", "displayValue",
                               "formatted", "formattedValue", "rawValue",
                               "content", "stat", "statValue", "data", "score",
                               "points", "fpts", "html", "children", "valueText"))
_NUMERIC_FIELDS = ("value", "rawValue", "statValue", "displayValue", "formattedValue",
                   "text", "display", "formatted", "content", "stat", "data",
                   "score", "points", "fpts", "valueText")


def _decode_number(value, depth=0):
    """Parse *only* unambiguous numbers, never markup, identifiers or booleans.

    A nested field may contain a provider presentation object. Multiple distinct
    numbers in one cell are ambiguous, and must not become scoring evidence.
    """
    if depth > 3 or value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        result = Decimal(str(value))
        return result if result.is_finite() else None
    if isinstance(value, str):
        item = value.strip().replace('\u2212', '-')
        if not re.fullmatch(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,4})?', item):
            return None
        try:
            result = Decimal(item.replace(',', ''))
            return result if result.is_finite() else None
        except InvalidOperation:
            return None
    if isinstance(value, dict):
        candidates = []
        for key in _NUMERIC_FIELDS:
            if key in value:
                num = _decode_number(value[key], depth + 1)
                if num is not None:
                    candidates.append(num)
        # Do not pick a random number when presentation and raw fields disagree.
        return candidates[0] if candidates and all(c == candidates[0] for c in candidates) else None
    return None


def _fpts_cell_diagnostic(payload: dict) -> dict:
    """Describe FPts representation, returning counts and allowlisted labels only.

    No raw cell, player identity, player-level value, or API secret is exported.
    """
    data = payload.get('data', payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return {'status': 'no_data_object'}
    header = data.get('tableHeader', {})
    headers = header.get('cells', []) if isinstance(header, dict) else []
    indices = [i for i, cell in enumerate(headers)
               if isinstance(cell, dict) and cell.get('key') == 'fpts']
    if len(indices) != 1:
        return {'status': 'fpts_column_unresolved'}
    rows = data.get('statsTable')
    if not isinstance(rows, list):
        return {'status': 'no_stats_table'}
    types, fields = Counter(), Counter()
    missing = decoded = 0
    for row in rows[:2000]:
        cells = row.get('cells') if isinstance(row, dict) else None
        if not isinstance(cells, list) or len(cells) <= indices[0]:
            missing += 1
            continue
        cell = cells[indices[0]]
        types[type(cell).__name__] += 1
        if isinstance(cell, dict):
            fields.update(k for k in cell if k in _SAFE_CELL_FIELDS)
        if _decode_number(cell) is not None:
            decoded += 1
    return {'status': 'inspected', 'rows_examined': min(len(rows), 2000),
            'missing_cells': missing, 'decoded_cells': decoded,
            'cell_types': dict(sorted(types.items())),
            'allowlisted_cell_field_counts': dict(sorted(fields.items()))}


def _anonymous_fpts_signature(payload: dict) -> dict:
    """Hash sorted, decoded FPts only; never validate period identity or credit.

    The hash covers values only; no player identities, records, or values are
    emitted. Missing/unparseable cells never become zero.
    """
    data = payload.get('data', payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return {'usable': False, 'reason': 'no_data_object'}
    header = data.get('tableHeader', {})
    cells = header.get('cells', []) if isinstance(header, dict) else []
    indices = [i for i, cell in enumerate(cells)
               if isinstance(cell, dict) and cell.get('key') == 'fpts']
    if len(indices) != 1:
        return {'usable': False, 'reason': 'fpts_column_unresolved'}
    rows = data.get('statsTable', [])
    if not isinstance(rows, list):
        return {'usable': False, 'reason': 'no_stats_table'}
    values = []
    for row in rows:
        item = row.get('cells') if isinstance(row, dict) else None
        if not isinstance(item, list) or len(item) <= indices[0]:
            continue
        value = _decode_number(item[indices[0]])
        if value is not None:
            values.append(format(value.normalize(), 'f'))
    canonical = json.dumps(sorted(values), separators=(',', ':'))
    return {'usable': bool(values), 'rows_with_fpts': len(values),
            'fingerprint': hashlib.sha256(canonical.encode()).hexdigest()[:16] if values else None}


# Explicit provider identifiers only. Names, table positions and display HTML
# are never safe substitutes for stable player identity.
_ID_FIELDS = ("playerId", "player_id", "fantasyPlayerId", "fantasy_player_id")


def _stable_player_id(row):
    if not isinstance(row, dict):
        return None
    if isinstance(row.get('scorer'), dict) and row['scorer'].get('team') is True:
        return None
    found = []
    sources = [row]
    for field in ("player", "playerInfo", "playerData", "scorer"):
        if isinstance(row.get(field), dict):
            sources.append(row[field])
    for source in sources:
        for field in (_ID_FIELDS + (("scorerId",) if source is not row and source is row.get("scorer") else ())) :
            value = source.get(field)
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                candidate = str(value).strip()
                if re.fullmatch(r"[A-Za-z0-9_-]{2,64}", candidate):
                    found.append(candidate)
    if not found or len(set(found)) != 1:
        return None
    return found[0]


def _scorer_identity_shape(payload):
    """Inspect provider's documented `statsTable[].scorer.scorerId` shape.

    Report only aggregate metadata. The `scorer` object can also denote a team,
    so a team scorer is never accepted as an individual player.
    """
    data = payload.get('data', payload) if isinstance(payload, dict) else {}
    rows = data.get('statsTable') if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return {'status': 'no_stats_table'}
    counts = Counter()
    for row in rows[:2000]:
        scorer = row.get('scorer') if isinstance(row, dict) else None
        if not isinstance(scorer, dict):
            counts['missing_scorer_object'] += 1
            continue
        counts['scorer_object_present'] += 1
        if scorer.get('team') is True:
            counts['team_scorer_excluded'] += 1
            continue
        if _stable_player_id(row) is not None:
            counts['stable_player_id_recognized'] += 1
        elif 'scorerId' in scorer:
            counts['scorer_id_present_but_unusable'] += 1
        else:
            counts['scorer_id_absent'] += 1
    return {'status': 'inspected', 'rows_examined': min(len(rows), 2000),
            'counts': dict(sorted(counts.items()))}


def _active_team_credit_shape(payload):
    """Read-only structure check of documented getLiveScoringStats ACTIVE.statsMap.

    No request is made by this function. Its purpose is to distinguish the
    *potential* active-team credit source from the general player-pool stats.
    No player IDs, fantasy-team IDs, point values, or source payload are exported.
    """
    data = payload.get('data', payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return {'status': 'no_data_object', 'credit_eligible': False}
    per_team = data.get('statsPerTeam')
    teams = per_team.get('allTeamsStats') if isinstance(per_team, dict) else None
    if not isinstance(teams, dict):
        return {'status': 'active_team_stats_not_present', 'credit_eligible': False}
    counts = Counter()
    for _, team_data in list(teams.items())[:100]:
        counts['teams_examined'] += 1
        active = team_data.get('ACTIVE') if isinstance(team_data, dict) else None
        stats = active.get('statsMap') if isinstance(active, dict) else None
        if not isinstance(stats, dict):
            counts['teams_without_active_map'] += 1
            continue
        counts['teams_with_active_map'] += 1
        for scorer_id, statistic in list(stats.items())[:300]:
            if not isinstance(scorer_id, str) or scorer_id.startswith('_'):
                counts['non_player_entries_excluded'] += 1
                continue
            counts['active_scorer_entries'] += 1
            # object1 is documented in the independent NHL implementation,
            # but its semantics are not yet JHLPAA-verified.
            if isinstance(statistic, dict) and _decode_number(statistic.get('object1')) is not None:
                counts['entries_with_numeric_object1'] += 1
    return {'status': 'structure_only', 'counts': dict(sorted(counts.items())),
            'date_identity_verified': False, 'roster_credit_verified': False,
            'credit_eligible': False}


def _player_fpts_alignment(payload):
    """Private in-memory ID→FPts map plus metadata; map is never exported."""
    data = payload.get('data', payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return {}, {'status': 'no_data_object'}
    headers = data.get('tableHeader', {}).get('cells', []) if isinstance(data.get('tableHeader'), dict) else []
    indices = [i for i, item in enumerate(headers)
               if isinstance(item, dict) and item.get('key') == 'fpts']
    rows = data.get('statsTable')
    if len(indices) != 1 or not isinstance(rows, list):
        return {}, {'status': 'fpts_column_or_rows_unresolved'}
    matched = {}
    no_id = duplicate = no_fpts = 0
    duplicates = set()
    for row in rows[:2000]:
        identity = _stable_player_id(row)
        if identity is None:
            no_id += 1
            continue
        cells = row.get('cells') if isinstance(row, dict) else None
        number = _decode_number(cells[indices[0]]) if isinstance(cells, list) and len(cells) > indices[0] else None
        if number is None:
            no_fpts += 1
            continue
        if identity in matched:
            duplicate += 1
            duplicates.add(identity)
        else:
            matched[identity] = number
    for identity in duplicates:
        matched.pop(identity, None)
    return matched, {'status': 'inspected', 'rows_examined': min(len(rows), 2000),
                     'rows_missing_stable_id': no_id,
                     'rows_missing_decodable_fpts': no_fpts,
                     'duplicate_player_ids': duplicate,
                     'unambiguous_player_rows': len(matched),
                     'full_page_possible': len(rows) >= 500}


def _aligned_fpts_comparison(left, right):
    """Compare common stable IDs without exporting IDs, values or row-level data."""
    a, a_info = _player_fpts_alignment(left)
    b, b_info = _player_fpts_alignment(right)
    common = sorted(a.keys() & b.keys())
    changes = sum(a[k] != b[k] for k in common)
    # Hash a stable sorted pairing, not the provider's sort order.
    def digest(records):
        canonical = json.dumps([(k, format(records[k].normalize(), 'f')) for k in common],
                               separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16] if common else None
    return {'requested_response_identity': a_info,
            'control_response_identity': b_info,
            'matched_player_count': len(common),
            'changed_matched_player_count': changes,
            'matched_player_fpts_differ': bool(changes),
            'requested_matched_fingerprint': digest(a),
            'control_matched_fingerprint': digest(b),
            'identity_alignment_usable': bool(common),
            'interpretation': ('matched_player_values_differ_period_identity_unverified' if changes
                               else 'matched_values_identical_or_no_stable_identity'),
            'credit_eligible': False}


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
        report['selected_fpts_cell_diagnostic'] = _fpts_cell_diagnostic(selected)
        report['selected_player_identity_diagnostic'] = _scorer_identity_shape(selected)
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
        candidate_payloads = []
        for requested in (period, other_period):
            params = _period_candidate_params(code, requested)
            try:
                response = client.get_player_stats(params=params)
                if client.is_error_payload(response):
                    candidates.append({'period': requested, 'status': 'provider_error'})
                    candidate_payloads.append(None)
                    continue
                candidate_payloads.append(response)
                candidates.append({'period': requested, 'status': 'response_received',
                                   'rows': inspect_player_stats_schema(response).get('statsTable_count'),
                                   'fpts_signature': _anonymous_fpts_signature(response),
                                   'fpts_cell_diagnostic': _fpts_cell_diagnostic(response),
                                   'scorer_identity_diagnostic': _scorer_identity_shape(response)})
            except Exception as candidate_exc:
                candidate_payloads.append(None)
                candidates.append({'period': requested, 'status': 'request_failed',
                                   'exception_type': type(candidate_exc).__name__})
        signatures = [item.get('fpts_signature', {}) for item in candidates]
        comparable = (len(signatures) == 2 and all(item.get('usable') for item in signatures))
        differing = comparable and signatures[0]['fingerprint'] != signatures[1]['fingerprint']
        alignment = (_aligned_fpts_comparison(*candidate_payloads)
                     if len(candidate_payloads) == 2 and all(isinstance(p, dict) for p in candidate_payloads)
                     else {'status': 'candidate_response_unavailable', 'credit_eligible': False})
        report['candidate_contract'] = {
            'source': 'observed_downloadPlayerStats_query_not_verified_fxpa_getPlayerStats',
            'candidate_field_names': ['seasonOrProjection', 'timeframeTypeCode',
                                      'transactionPeriod', 'timeStartType'],
            'requested_period': period, 'control_period': other_period,
            'comparisons': candidates,
            'player_alignment': alignment,
            'different_anonymous_fpts_distributions': bool(differing),
            'signature_comparable': bool(comparable),
            'inference': ('responses_differ_contract_still_unverified' if differing
                          else 'no_demonstrated_period_specific_difference'),
            'credit_eligible': False,
        }
        report['status'] = 'period_identity_unverified' 
        report['reason'] = ('A BY_PERIOD season selector alone does not identify the requested '
                            'scoring period or establish roster-credited player FPts. '
                            'A bounded differential probe using fields observed on the Fantrax '
                            'stats export is diagnostic only. Verify stable player IDs, the fxpa request/response '
                            'contract and scoring-period identity before ledger writes. Provider research points to '
                            'getLiveScoringStats ACTIVE.statsMap for credited lineup totals; its date and NHL '
                            'contract must be verified independently.')
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
