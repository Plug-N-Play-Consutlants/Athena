"""
Fantrax authentication diagnostics.

Provider-layer responsibility:
- Detect provider auth failures in raw Fantrax payloads.
- Produce deterministic diagnostics without interpreting league data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


NOT_LOGGED_IN_CODES = {
    "WARNING_NOT_LOGGED_IN",
    "ERROR_NOT_LOGGED_IN",
    "NOT_LOGGED_IN",
}


@dataclass(frozen=True)
class AuthDiagnostic:
    authenticated: bool
    code: str
    message: str


class FantraxAuthValidator:
    """Inspect Fantrax payloads for authentication failures."""

    @staticmethod
    def _extract_page_error(payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {}

        page_error = payload.get("pageError")
        if isinstance(page_error, dict):
            return page_error

        responses = payload.get("responses")
        if isinstance(responses, list):
            for response in responses:
                if isinstance(response, dict):
                    nested = response.get("pageError")
                    if isinstance(nested, dict):
                        return nested
        return {}

    def diagnose_payload(self, payload: Any) -> AuthDiagnostic:
        page_error = self._extract_page_error(payload)
        code = str(page_error.get("code", "")) if page_error else ""
        if code in NOT_LOGGED_IN_CODES:
            return AuthDiagnostic(
                authenticated=False,
                code=code,
                message=(
                    "Fantrax authentication failed. The configured browser-session "
                    "cookie may be missing, expired, incomplete, or from the wrong domain."
                ),
            )

        return AuthDiagnostic(
            authenticated=True,
            code=code,
            message="No Fantrax authentication failure detected in payload.",
        )

    def raise_for_auth_failure(self, payload: Any) -> None:
        diagnostic = self.diagnose_payload(payload)
        if not diagnostic.authenticated:
            raise PermissionError(diagnostic.message)
