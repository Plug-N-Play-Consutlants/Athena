"""Provider session metadata.

This module does not implement network transport. It standardizes the safe
metadata Athena may expose about a provider session without leaking secrets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from Providers.base.connection_state import ConnectionState


@dataclass
class ProviderSessionStatus:
    """Safe provider session status for Athena/Scout diagnostics."""

    provider: str
    state: ConnectionState = ConnectionState.DISCONNECTED
    authenticated: bool = False
    secret_present: bool = False
    message: str = ""
    last_error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe status dictionary."""
        return {
            "provider": self.provider,
            "state": self.state.value if isinstance(self.state, ConnectionState) else str(self.state),
            "authenticated": bool(self.authenticated),
            "secret_present": bool(self.secret_present),
            "message": self.message,
            "last_error": self.last_error,
            "metadata": dict(self.metadata or {}),
        }
