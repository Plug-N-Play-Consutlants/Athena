"""Regression checks for the compact Studio report copy workflow."""
from pathlib import Path
from Tools import athena_studio


def test_report_copy_action_is_integrated_into_existing_dialog():
    source = Path(athena_studio.__file__).read_text(encoding="utf-8")
    dialog = source.split("    def show_fantrax_period_diagnostic(self)", 1)[1].split("    def _status_group(self", 1)[0]
    assert 'text="Copy Report", command=copy_report' in dialog
    assert 'window.clipboard_clear()' in dialog
    assert 'window.clipboard_append(content)' in dialog
    assert 'display.get("1.0", "end-1c")' in dialog
    assert 'display.bind("<Control-a>", select_report_text)' in dialog
    assert 'display.bind("<Control-A>", select_report_text)' in dialog
    assert 'ttk.Button(buttons, text="Run Probe"' in dialog
    assert 'ttk.Button(buttons, text="View Report"' in dialog


def test_copy_action_does_not_add_permanent_studio_toolbar_button():
    source = Path(athena_studio.__file__).read_text(encoding="utf-8")
    assert source.count('text="Copy Report", command=copy_report') == 1
