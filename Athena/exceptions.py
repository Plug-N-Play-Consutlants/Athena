"""
Athena exception types.

Athena is the public orchestration surface for the deterministic Sports
Intelligence Engine. These exceptions are intentionally lightweight so Scout,
future APIs, and future plugins can catch Athena-specific failures without
knowing about internal Fetch/Build/Knowledge/Intelligence modules.
"""


class AthenaError(Exception):
    """Base exception for Athena orchestration failures."""


class AthenaConfigurationError(AthenaError):
    """Raised when Athena cannot load or validate configuration/workspace state."""


class AthenaNotImplementedError(AthenaError):
    """Raised by reserved orchestration methods that are not active in this drop."""


class AthenaPipelineError(AthenaError):
    """Raised when an Athena orchestration pipeline stage fails validation."""
