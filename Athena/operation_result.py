"""Structured operation diagnostics for Athena alpha workflows.

OperationResult is intentionally lightweight and serializable. It gives Scout a
single contract for reporting success, failure, stage, recommendation, and
Developer Mode traces without changing Athena business logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OperationResult:
    """Serializable result envelope for high-level Athena operations."""

    success: bool
    operation: str
    stage: str = "not_started"
    provider: Optional[str] = None
    confidence: float = 0.0
    summary: str = ""
    reason: str = ""
    recommendation: str = ""
    facts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    developer_trace: List[Dict[str, Any]] = field(default_factory=list)
    elapsed_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dictionary."""
        return asdict(self)


def trace_event(stage: str, status: str, message: str = "", **details: Any) -> Dict[str, Any]:
    """Create a compact developer trace event."""
    event: Dict[str, Any] = {
        "stage": stage,
        "status": status,
    }
    if message:
        event["message"] = message
    if details:
        event["details"] = details
    return event


def recommendation_for_failure(reason: str, stage: str = "") -> str:
    """Map known alpha failure patterns to practical recovery steps."""
    text = f"{stage} {reason}".lower()
    if "not logged" in text or "not_logged" in text or "auth" in text or "cookie" in text or "session" in text:
        return "Reconnect Fantrax with a fresh authenticated session, then run Sync League again."
    if "placeholder" in text or "league_id" in text or "league id" in text:
        return "Use Test & Save Connection with the correct Fantrax league ID to refresh the active workspace."
    if "pipeline script not found" in text or "no such file" in text or "missing" in text:
        return "Confirm the latest Athena patch was applied to the repository root and launch through launch.py."
    if "zero" in text or "0" in text:
        return "Check Developer Mode for the failed output and confirm the provider returned usable data."
    return "Review Developer Mode for the failing stage. If the provider connection is valid, report the stage, reason, and exception text."
