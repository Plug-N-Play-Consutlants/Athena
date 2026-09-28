"""
Athena Orchestrator.

Patch 3E.3 routes provider connection through the provider registry. Scout and
future consumers should call Athena's public surface only.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from Athena.connect import connect_provider
from Athena.exceptions import AthenaConfigurationError
from Athena.status import get_status
from Athena.sync import sync as run_sync
from Athena.workspace import load_workspace


class AthenaOrchestrator:
    """Public Athena orchestration facade."""

    def workspace(self) -> Dict[str, Any]:
        """Return the active Athena workspace."""
        return load_workspace()

    def status(self) -> Dict[str, Any]:
        """Return a read-only Athena status snapshot."""
        return get_status()

    def connect(
        self,
        *,
        provider: str,
        league_id: Optional[str] = None,
        auth_cookie: str = "",
        cookie: str = "",
        mode: str = "fantasy_league",
        validate: bool = True,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Connect Athena to a provider context through the provider registry."""
        selected_provider = str(provider or "").strip()
        if not selected_provider:
            raise AthenaConfigurationError("provider is required.")
        return connect_provider(
            provider=selected_provider,
            league_id=league_id,
            auth_cookie=auth_cookie or cookie,
            cookie=cookie or auth_cookie,
            mode=mode,
            validate=validate,
            **extra,
        )

    def sync(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Synchronize the active Athena workspace."""
        return run_sync(*args, **kwargs)

    def ask(self, question: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Execute a Scout-directed request through Athena's request boundary.

        Specialist migration is incremental. The active router is isolated in
        the compatibility adapter until its handlers have Athena-owned ports.
        """
        from Athena.request_execution import AthenaRequest, execute_request

        mode = kwargs.pop("mode", "fantasy")
        context = kwargs.pop("context", None)
        sections = kwargs.pop("sections", ())
        continuation = kwargs.pop("continuation", None)
        if args or kwargs:
            raise TypeError("ask accepts question, mode, context, sections, and continuation only")
        request = AthenaRequest(question=question, mode=mode, context=context, sections=sections, continuation=continuation)
        return execute_request(request)


_default_orchestrator = AthenaOrchestrator()


def workspace() -> Dict[str, Any]:
    return _default_orchestrator.workspace()


def status() -> Dict[str, Any]:
    return _default_orchestrator.status()


def connect(**kwargs: Any) -> Dict[str, Any]:
    return _default_orchestrator.connect(**kwargs)


def sync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _default_orchestrator.sync(*args, **kwargs)


def ask(question: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _default_orchestrator.ask(question, *args, **kwargs)
