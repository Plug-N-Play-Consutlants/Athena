"""Diagnostics package for Athena and Scout observability."""

from Diagnostics.diagnostics import DiagnosticsRecorder, start_trace
from Diagnostics.events import DiagnosticEvent
from Diagnostics.trace import new_trace_id

__all__ = [
    "DiagnosticEvent",
    "DiagnosticsRecorder",
    "new_trace_id",
    "start_trace",
]
