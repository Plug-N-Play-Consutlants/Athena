"""Athena diagnostics recorder.

Diagnostics are structured, in-memory events that can also be written to JSON
reports by callers. This module intentionally does not replace Core.logger; it
adds machine-readable operation traces for Scout and Athena.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, List, Optional

from Diagnostics.events import DiagnosticEvent
from Diagnostics.trace import new_trace_id


@dataclass
class DiagnosticsRecorder:
    """Record structured diagnostic events for one Athena operation."""

    operation: str
    trace_id: str = field(default_factory=new_trace_id)
    events: List[Dict[str, Any]] = field(default_factory=list)
    started_at_perf: float = field(default_factory=perf_counter)

    def emit(
        self,
        *,
        component: str,
        status: str,
        message: str,
        step: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event = DiagnosticEvent(
            trace_id=self.trace_id,
            component=component,
            operation=self.operation,
            step=step,
            status=status,
            message=message,
            details=details or {},
        ).to_dict()
        self.events.append(event)
        return event

    def summary(self) -> Dict[str, Any]:
        duration = perf_counter() - self.started_at_perf
        return {
            "trace_id": self.trace_id,
            "operation": self.operation,
            "duration_seconds": round(duration, 4),
            "event_count": len(self.events),
            "events": list(self.events),
        }


def start_trace(operation: str, prefix: str = "athena") -> DiagnosticsRecorder:
    return DiagnosticsRecorder(operation=operation, trace_id=new_trace_id(prefix))
