"""Fantrax provider adapter.

This adapter is the first concrete implementation of the provider contract
introduced in Patch 3E.1. It wraps the existing FantraxClient instead of
replacing it, so the validated Fantrax fetch/build pipeline remains unchanged.
"""

from __future__ import annotations

from typing import Any, Dict

from Providers.base.connection_state import ConnectionState
from Providers.base.events import provider_event
from Providers.base.provider import (
    BaseProvider,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
)
from Providers.base.session import ProviderSessionStatus
from Providers.Fantrax.fantrax_client import FantraxClient


class FantraxProvider(BaseProvider):
    """Provider-contract adapter around the existing FantraxClient."""

    provider_key = "fantrax"
    provider_name = "Fantrax"

    def __init__(self) -> None:
        self._client: FantraxClient | None = None
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._last_error: str = ""

    def _get_client(self) -> FantraxClient:
        if self._client is None:
            self._client = FantraxClient()
        return self._client

    def _safe_cookie_status(self) -> Dict[str, Any]:
        try:
            return self._get_client().cookie_status()
        except Exception as exc:  # defensive status reporting only
            return {
                "present": False,
                "source": "unknown",
                "cookie_count": 0,
                "message": f"Unable to inspect cookie status: {exc}",
            }

    def connect(self, **kwargs: Any) -> Dict[str, Any]:
        """Initialize and validate the Fantrax client/session.

        Fantrax authentication remains owned by the existing FantraxClient and
        cookie manager. Workspace/secrets persistence stays in Athena.connect
        for this drop; 3E.2 only introduces the provider adapter contract.
        """
        self._state = ConnectionState.CONNECTING
        self._last_error = ""
        try:
            client = self._get_client()
            client.validate_config()
            cookie_status = client.cookie_status()
            if not client.has_cookie_auth():
                self._state = ConnectionState.EXPIRED
                self._last_error = "Fantrax authentication cookie is missing."
                raise ProviderAuthenticationError(self._last_error)
            self._state = ConnectionState.CONNECTED
            return {
                "ok": True,
                "provider": self.provider_name,
                "state": self._state.value,
                "authenticated": True,
                "cookie_status": cookie_status,
                "event": provider_event(
                    provider=self.provider_key,
                    operation="connect",
                    status="success",
                    step="connect",
                    message="Fantrax provider connected.",
                    details={"cookie_present": bool(cookie_status.get("present"))},
                ),
            }
        except ProviderError:
            raise
        except Exception as exc:
            self._state = ConnectionState.ERROR
            self._last_error = str(exc)
            raise ProviderConfigurationError(f"Fantrax provider connection failed: {exc}") from exc

    def disconnect(self) -> Dict[str, Any]:
        """Clear the in-memory client reference.

        This intentionally does not delete local secrets. Secret persistence is
        controlled by Athena/workspace policy, not by the provider adapter.
        """
        self._client = None
        self._state = ConnectionState.DISCONNECTED
        self._last_error = ""
        return {
            "ok": True,
            "provider": self.provider_name,
            "state": self._state.value,
            "message": "Fantrax provider disconnected from active process.",
        }

    def test(self, **kwargs: Any) -> Dict[str, Any]:
        """Validate the provider by fetching league info through FantraxClient."""
        try:
            self.connect(**kwargs)
            client = self._get_client()
            payload = client.get_league()
            client.validate_payload(payload, "Fantrax league info")
            self._state = ConnectionState.CONNECTED
            return {
                "ok": True,
                "provider": self.provider_name,
                "state": self._state.value,
                "message": "Fantrax connection test succeeded.",
                "league_name": payload.get("leagueName") or payload.get("name") if isinstance(payload, dict) else None,
                "event": provider_event(
                    provider=self.provider_key,
                    operation="test",
                    status="success",
                    step="fetch_league",
                    message="Fantrax league info fetched successfully.",
                ),
            }
        except Exception as exc:
            self._state = ConnectionState.ERROR
            self._last_error = str(exc)
            return {
                "ok": False,
                "provider": self.provider_name,
                "state": self._state.value,
                "message": "Fantrax connection test failed.",
                "error": str(exc),
                "event": provider_event(
                    provider=self.provider_key,
                    operation="test",
                    status="error",
                    step="fetch_league",
                    message=str(exc),
                ),
            }

    def status(self) -> ProviderSessionStatus:
        cookie_status = self._safe_cookie_status()
        authenticated = self._state.is_healthy and bool(cookie_status.get("present"))
        return ProviderSessionStatus(
            provider=self.provider_name,
            state=self._state,
            authenticated=authenticated,
            secret_present=bool(cookie_status.get("present")),
            message=cookie_status.get("message", ""),
            last_error=self._last_error,
            metadata={
                "cookie_source": cookie_status.get("source", "unknown"),
                "cookie_count": cookie_status.get("cookie_count", 0),
            },
        )

    def fetch(self, endpoint: str, **kwargs: Any) -> Any:
        """Fetch a Fantrax payload using existing FantraxClient methods.

        endpoint may be a known semantic key such as league, player_pool,
        transactions, schedule, or player_stats. Unknown values fall back to
        FantraxClient.get(endpoint) so existing route strings remain supported.
        """
        client = self._get_client()
        selected = str(endpoint or "").strip().lower()
        if not selected:
            raise ProviderConfigurationError("Fantrax fetch endpoint is required.")

        if selected in {"league", "league_info"}:
            return client.get_league()
        if selected in {"player_pool", "players", "rosters"}:
            return client.get_player_pool_payload()
        if selected in {"transactions", "transaction_history"}:
            return client.get_transactions(**kwargs)
        if selected == "schedule":
            return client.get_schedule()
        if selected in {"player_stats", "stats"}:
            return client.get_player_stats(**kwargs)

        return client.get(endpoint, params=kwargs.get("params"), include_league_id=kwargs.get("include_league_id", True))
