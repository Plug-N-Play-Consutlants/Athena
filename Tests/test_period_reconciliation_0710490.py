from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_archive_period_reconciliation():
    src = (ROOT / "Athena/Investigation/period_execution.py").read_text()
    assert "if standings_period != selected_period:" in src
    assert "reconciled=true" in src
def test_unverified_period_selector_gate():
    src = (ROOT / "Athena/Investigation/period_evidence_acquisition.py").read_text()
    assert '"period_filter_status"] = "not_verified"' in src
    assert 'status="unverified_period"' in src
