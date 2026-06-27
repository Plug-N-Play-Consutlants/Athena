"""Provider event primitives.

Provider events are lightweight, serializable records that can be surfaced in
Scout, diagnostics, logs, or API responses. They are intentionally generic so
future providers can emit the same event shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProviderEvent:
    """Serializable provider operation event."""

    provider: str
    operation: str
    status: str
    message: str
    trace_id: str = ""
    step: str = ""
    timestamp: str = field(default_factory=utc_now_iso)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe event dictionary."""
        return {
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "provider": self.provider,
            "operation": self.operation,
            "step": self.step,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details or {}),
        }


def provider_event(
    *,
    provider: str,
    operation: str,
    status: str,
    message: str,
    trace_id: str = "",
    step: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience function for producing a provider event dictionary."""
    return ProviderEvent(
        provider=provider,
        operation=operation,
        status=status,
        message=message,
        trace_id=trace_id,
        step=step,
        details=details or {},
    ).to_dict()
