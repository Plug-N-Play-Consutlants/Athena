"""v67.15: export NHL source traces through Studio without exposing raw source data."""
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tools.athena_studio import _export_nhl_source_traces


def test_nhl_source_trace_export_contains_sanitized_period_metadata(tmp_path):
    root = tmp_path / 'Output'
    folder = root / 'PeriodScoringAudit' / 'nhl_source_traces' / 'league' / '2026'
    folder.mkdir(parents=True)
    for period in (6, 7, 8):
        (folder / f'period_{period:03}.json').write_text(json.dumps({
            'schema': 'athena.nhl_source_trace.v1', 'period': period,
            'season': '2026', 'status': 'acquisition_failed',
            'error_type': 'ValueError', 'error': 'cookie=SECRET',
            'requests': [{
                'request': 'page', 'offset': 100, 'page': 2,
                'requested_limit': 500, 'returned_rows': 100,
                'declared_total': 850, 'schema_valid': True,
                'playerId': 'SECRET', 'url': 'https://private.example/?token=SECRET',
            }]
        }), encoding='utf-8')
    included, errors = [], []
    output = tmp_path / 'diag.zip'
    with zipfile.ZipFile(output, 'w') as archive:
        count = _export_nhl_source_traces(archive, root, included, errors)
        archive.writestr('diagnostics_manifest.json', json.dumps({'files': included, 'nhl_source_trace_count': count}))
    assert count == 3
    assert not errors
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 4
        for period in (6, 7, 8):
            name = f'Output/PeriodScoringAudit/nhl_source_traces/league/2026/period_{period:03}.json'
            data = archive.read(name).decode()
            assert 'SECRET' not in data
            assert 'playerId' not in data
            record = json.loads(data)
            assert record['period'] == period
            assert record['requests'][0]['offset'] == 100
            assert record['requests'][0]['returned_rows'] == 100


def test_malformed_source_trace_is_not_copied(tmp_path):
    folder = tmp_path / 'PeriodScoringAudit' / 'nhl_source_traces' / 'league' / '2026'
    folder.mkdir(parents=True)
    (folder / 'period_006.json').write_text('{"schema":"unknown", "secret":"PASSWORD"}')
    included, errors = [], []
    output = tmp_path / 'diag.zip'
    with zipfile.ZipFile(output, 'w') as archive:
        count = _export_nhl_source_traces(archive, tmp_path, included, errors)
    assert count == 0
    assert errors and 'unexpected trace schema' in errors[0]
    with zipfile.ZipFile(output) as archive:
        assert not archive.namelist()


def test_missing_traces_are_not_treated_as_export_failure(tmp_path):
    included, errors = [], []
    with zipfile.ZipFile(tmp_path / 'diag.zip', 'w') as archive:
        count = _export_nhl_source_traces(archive, tmp_path, included, errors)
    assert count == 0 and not errors and not included
