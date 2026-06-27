"""
Fantrax cookie management.

Provider-layer responsibility:
- Read local-only browser-session cookies through Core configuration helpers.
- Mirror raw Cookie header values into requests.Session.cookies when possible.
- Never print or persist cookie values.
"""

from __future__ import annotations

from dataclasses import dataclass
from http.cookies import SimpleCookie
import os
from typing import Any, Dict

from Core.config import get_config_value, get_secret_value


@dataclass(frozen=True)
class CookieStatus:
    present: bool
    source: str
    cookie_count: int
    message: str


class FantraxCookieManager:
    """Load and apply Fantrax browser-session cookies."""

    CONFIG_SOURCES = (
        ("secrets.local:fantrax.cookie", lambda: get_secret_value("fantrax.cookie", "")),
        ("environment:FANTRAX_COOKIE", lambda: os.getenv("FANTRAX_COOKIE", "")),
        ("provider.auth.cookie", lambda: get_config_value("provider.auth.cookie", "")),
        ("provider.cookie", lambda: get_config_value("provider.cookie", "")),
        ("provider.headers.Cookie", lambda: get_config_value("provider.headers.Cookie", "")),
        ("provider.headers.cookie", lambda: get_config_value("provider.headers.cookie", "")),
    )

    def load_cookie_header(self) -> tuple[str, str]:
        """Return the configured raw Cookie header and its source label."""
        for source, loader in self.CONFIG_SOURCES:
            value = loader()
            if isinstance(value, str) and value.strip():
                return value.strip(), source
        return "", ""

    def parse_cookie_header(self, cookie_header: str) -> Dict[str, str]:
        """Parse a raw Cookie header into a simple name/value mapping."""
        if not cookie_header:
            return {}

        parsed = SimpleCookie()
        try:
            parsed.load(cookie_header)
        except Exception:
            return {}

        return {key: morsel.value for key, morsel in parsed.items() if key and morsel.value}

    def apply_cookie_header_to_session(self, session: Any, cookie_header: str) -> int:
        """Mirror a raw Cookie header into requests.Session.cookies."""
        cookies = self.parse_cookie_header(cookie_header)
        for key, value in cookies.items():
            session.cookies.set(key, value, domain=".fantrax.com")
        return len(cookies)

    def get_status(self) -> CookieStatus:
        cookie_header, source = self.load_cookie_header()
        cookies = self.parse_cookie_header(cookie_header)
        if not cookie_header:
            return CookieStatus(
                present=False,
                source="",
                cookie_count=0,
                message="No Fantrax browser-session cookie configured.",
            )

        if not cookies:
            return CookieStatus(
                present=True,
                source=source,
                cookie_count=0,
                message="Cookie header is present but could not be parsed.",
            )

        return CookieStatus(
            present=True,
            source=source,
            cookie_count=len(cookies),
            message="Fantrax browser-session cookie is configured.",
        )
