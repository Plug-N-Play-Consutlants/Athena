"""Diagnostics event primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DiagnosticEvent:
    """Serializable Athena diagnostic event."""

    trace_id: str
    component: str
    operation: str
    status: str
    message: str
    step: str = ""
    timestamp: str = field(default_factory=utc_now_iso)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "component": self.component,
            "operation": self.operation,
            "step": self.step,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details or {}),
        }
