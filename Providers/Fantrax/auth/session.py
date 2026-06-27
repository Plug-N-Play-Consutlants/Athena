"""
Fantrax session factory.

Provider-layer responsibility:
- Create a requests.Session configured for Fantrax API and web-message endpoints.
- Apply browser-compatible headers.
- Attach local-only cookies without exposing them.
"""

from __future__ import annotations

from typing import Any, Dict

import requests

from .cookie_manager import FantraxCookieManager


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def default_browser_headers(user_agent: str | None = None) -> Dict[str, str]:
    """Return conservative browser-style headers for Fantrax requests."""
    ua = user_agent or DEFAULT_USER_AGENT
    return {
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.fantrax.com",
        "Referer": "https://www.fantrax.com/",
    }


def build_fantrax_session(
    user_agent: str | None = None,
    headers: Dict[str, Any] | None = None,
    cookies: Dict[str, Any] | None = None,
    cookie_manager: FantraxCookieManager | None = None,
) -> requests.Session:
    """Build a configured Fantrax session."""
    manager = cookie_manager or FantraxCookieManager()
    session = requests.Session()
    session.headers.update(default_browser_headers(user_agent))

    if isinstance(headers, dict):
        session.headers.update(headers)

    cookie_header, _source = manager.load_cookie_header()
    if cookie_header:
        session.headers.update({"Cookie": cookie_header})
        manager.apply_cookie_header_to_session(session, cookie_header)

    if isinstance(cookies, dict) and cookies:
        session.cookies.update(cookies)

    return session
