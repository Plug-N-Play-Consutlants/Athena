"""Prevent transient Fantrax diagnostics from accumulating Core Workflow buttons."""
from pathlib import Path


def test_fantrax_diagnostics_reuses_existing_developer_slot():
    source = (Path(__file__).resolve().parents[1] / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    core = source.split('self._button_group(body, "Core Workflow", [', 1)[1].split('])', 1)[0]
    developer = source.split('self._button_group(right, "Developer Diagnostics", [', 1)[1].split('])', 1)[0]
    assert "Fantrax Period" not in core
    assert "Fantrax Diagnostics" in developer
    assert "Discover Draft Source" not in developer
    assert 'self.show_fantrax_diagnostics' in developer
    assert 'self.show_fantrax_period_diagnostic()' in source
    assert 'self.discover_draft_source()' in source


def test_probe_retains_verified_credit_guard():
    source = (Path(__file__).resolve().parents[1] / "Tools" / "fantrax_period_probe.py").read_text(encoding="utf-8")
    assert 'period_identity_unverified' in source
    assert 'ledger_written' in source
