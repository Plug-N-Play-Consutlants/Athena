"""
Fantrax provider client.

Responsible only for provider communication and raw payload persistence.
This module does not normalize, classify, score, or interpret data.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import requests

from Core.config import get_config_value, get_workspace_value
from Core.json_utils import write_json
from Core.logger import log
from Core.project_paths import RAW_DIR
from Providers.Fantrax.auth import (
    FantraxAuthValidator,
    FantraxCookieManager,
    build_fantrax_session,
)
from Providers.Fantrax.endpoints import FantraxEndpoints


class FantraxClient:
    """
    Fantrax provider transport client.

    Configuration source:
    - Configuration/config.json for provider settings.
    - Configuration/workspace.json for active workspace context.
    """

    def __init__(self) -> None:
        self.provider_name = get_config_value("provider.name", "Fantrax")
        self.base_url = get_config_value("provider.base_url", "https://www.fantrax.com/fxea")
        self.user_agent = get_config_value("provider.user_agent", "Sports Intelligence Engine 2.0")
        self.cookies = get_config_value("provider.cookies", {})
        self.headers = get_config_value("provider.headers", {})

        self.workspace_name = get_workspace_value("workspace.name", "")
        self.league_id = get_workspace_value(
            "workspace.league_id",
            get_config_value("provider.league_id", ""),
        )
        self.sport = get_workspace_value("workspace.sport", get_config_value("provider.sport", "NHL"))
        self.season = get_workspace_value("workspace.season", "")

        if not isinstance(self.cookies, dict):
            self.cookies = {}
        if not isinstance(self.headers, dict):
            self.headers = {}

        self.cookie_manager = FantraxCookieManager()
        self.auth_validator = FantraxAuthValidator()
        self.session = build_fantrax_session(
            user_agent=self.user_agent,
            headers=self.headers,
            cookies=self.cookies,
            cookie_manager=self.cookie_manager,
        )

    def has_cookie_auth(self) -> bool:
        return self.cookie_manager.get_status().present or bool(self.session.cookies)

    def cookie_status(self) -> dict[str, Any]:
        status = self.cookie_manager.get_status()
        return {
            "present": status.present,
            "source": status.source,
            "cookie_count": status.cookie_count,
            "message": status.message,
        }

    def validate_provider_config(self) -> None:
        if not self.base_url:
            raise ValueError("Missing provider.base_url in Configuration/config.json")

    def validate_workspace_config(self) -> None:
        if not self.league_id:
            raise ValueError(
                "Missing workspace.league_id in Configuration/workspace.json "
                "or provider.league_id in Configuration/config.json"
            )

    def validate_config(self) -> None:
        self.validate_provider_config()
        self.validate_workspace_config()

    def build_url(self, endpoint: str) -> str:
        if endpoint.lower().startswith(("http://", "https://")):
            return endpoint
        base = self.base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base}/{endpoint}"

    def with_league_params(self, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        merged = dict(params or {})
        if "leagueId" not in merged and "league_id" not in merged:
            merged["leagueId"] = self.league_id
        return merged

    def get_response(
        self,
        endpoint: str,
        params: Dict[str, Any] | None = None,
        include_league_id: bool = True,
    ) -> requests.Response:
        self.validate_config()
        url = self.build_url(endpoint)
        request_params = self.with_league_params(params) if include_league_id else (params or {})
        response = self.session.get(url, params=request_params, timeout=30)
        response.raise_for_status()
        return response

    def post_response(
        self,
        endpoint: str,
        payload: Dict[str, Any] | None = None,
        include_league_id: bool = True,
    ) -> requests.Response:
        self.validate_config()
        url = self.build_url(endpoint)
        request_payload = dict(payload or {})
        if include_league_id and "leagueId" not in request_payload and "league_id" not in request_payload:
            request_payload["leagueId"] = self.league_id
        response = self.session.post(url, json=request_payload, timeout=30)
        response.raise_for_status()
        return response

    def get(
        self,
        endpoint: str,
        params: Dict[str, Any] | None = None,
        include_league_id: bool = True,
    ) -> Any:
        response = self.get_response(endpoint, params=params, include_league_id=include_league_id)
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError(f"Fantrax response was not valid JSON for {response.url}") from exc

    def post(
        self,
        endpoint: str,
        payload: Dict[str, Any] | None = None,
        include_league_id: bool = True,
    ) -> Any:
        response = self.post_response(endpoint, payload=payload, include_league_id=include_league_id)
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError(f"Fantrax response was not valid JSON for {response.url}") from exc

    def fxpa_request(self, methods: Iterable[Dict[str, Any]] | Dict[str, Any]) -> Any:
        """
        Call Fantrax's fxpa/req web-message endpoint.

        Each method dict must be shaped as:
            {"method": "methodName", "data": {...}}
        """
        self.validate_workspace_config()

        if isinstance(methods, dict):
            method_list = [methods]
        else:
            method_list = list(methods)

        msgs = []
        for method in method_list:
            method_name = method.get("method")
            if not method_name:
                raise ValueError("Fantrax fxpa method is missing 'method'.")

            data = dict(method.get("data") or {})
            if "leagueId" not in data and "league_id" not in data:
                data["leagueId"] = self.league_id

            msgs.append(
                {
                    "method": method_name,
                    "data": {key: str(value) for key, value in data.items() if value is not None},
                }
            )

        response = self.session.post(
            FantraxEndpoints.FXPA_REQUEST_URL,
            params={"leagueId": self.league_id},
            json={"msgs": msgs},
            timeout=30,
        )
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("Fantrax fxpa/req response was not valid JSON.") from exc

        diagnostic = self.auth_validator.diagnose_payload(payload)
        if not diagnostic.authenticated:
            return payload

        responses = payload.get("responses") if isinstance(payload, dict) else None
        if isinstance(responses, list):
            if len(responses) == 1:
                first = responses[0]
                if isinstance(first, dict):
                    return first.get("data", first)
            return [item.get("data", item) if isinstance(item, dict) else item for item in responses]

        return payload

    def validate_payload(self, payload: Any, label: str = "Fantrax payload") -> None:
        if self.is_error_payload(payload):
            raise ValueError(f"{label} returned an error payload: {payload.get('error')}")
        diagnostic = self.auth_validator.diagnose_payload(payload)
        if not diagnostic.authenticated:
            raise PermissionError(f"{label}: {diagnostic.message}")

    def save_raw_json(self, filename: str, payload: Any) -> None:
        path = RAW_DIR / filename
        write_json(path, payload)
        log(f"Saved raw payload: {path}")

    def get_endpoint(self, endpoint_name: str) -> str:
        endpoint = FantraxEndpoints.get(endpoint_name, "")
        if not endpoint:
            raise ValueError(f"Missing provider.endpoints.{endpoint_name} in Configuration/config.json")
        return endpoint

    def get_optional_endpoint(self, endpoint_name: str, default: str = "") -> str:
        value = get_config_value(f"provider.endpoints.{endpoint_name}", default)
        return value if isinstance(value, str) else default

    @staticmethod
    def is_error_payload(payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        error = payload.get("error")
        if isinstance(error, dict):
            return bool(error.get("code") or error.get("message"))
        return bool(error)

    def get_league(self) -> Any:
        return self.get(self.get_endpoint("league"))

    def get_player_pool_payload(self) -> Any:
        """Return the active live Fantrax roster/player-pool payload."""
        return self.get(self.get_endpoint("player_pool"))

    def get_player_stats(self, endpoint: str | None = None, params: Dict[str, Any] | None = None) -> Any:
        selected_endpoint = endpoint or self.get_endpoint("player_stats")
        return self.get(selected_endpoint, params=params)

    def get_transactions(self, max_results_per_page: int = 1000) -> Any:
        return self.fxpa_request(
            {
                "method": FantraxEndpoints.TRANSACTIONS_METHOD,
                "data": {
                    "maxResultsPerPage": max_results_per_page,
                },
            }
        )

    def get_schedule(self) -> Any:
        return self.get(self.get_endpoint("schedule"))
