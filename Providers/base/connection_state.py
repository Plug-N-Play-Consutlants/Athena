"""Provider connection state primitives.

This module is provider-neutral. It defines the common connection lifecycle used
by Athena, Scout, and future providers. Providers may use any authentication
mechanism internally, but they should report state using these values.
"""

from __future__ import annotations

from enum import Enum


class ConnectionState(str, Enum):
    """Standard provider connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    REFRESHING = "refreshing_authentication"
    SYNCING = "syncing"
    ERROR = "error"
    EXPIRED = "expired"

    @property
    def is_healthy(self) -> bool:
        """Return True when the state represents a usable provider connection."""
        return self in {self.CONNECTED, self.SYNCING}
