"""
Athena Engine public API.

Athena is the deterministic orchestration surface for the Sports Intelligence
Engine. Scout and future consumers should call Athena rather than importing
provider, build, knowledge, or intelligence modules directly.
"""

from Athena.connect import connect_fantrax, connect_provider, infer_fantrax_context, infer_provider_context
from Athena.exceptions import AthenaConfigurationError, AthenaError, AthenaNotImplementedError
from Athena.orchestrator import AthenaOrchestrator, ask, connect, status, sync, workspace

__version__ = "0.5.0-drop4d2b"

__all__ = [
    "AthenaOrchestrator",
    "AthenaError",
    "AthenaConfigurationError",
    "AthenaNotImplementedError",
    "ask",
    "connect",
    "connect_provider",
    "connect_fantrax",
    "infer_fantrax_context",
    "infer_provider_context",
    "status",
    "sync",
    "workspace",
]
