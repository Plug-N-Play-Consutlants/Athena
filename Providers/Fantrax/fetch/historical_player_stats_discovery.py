"""Discover historical Fantrax player-stat sources from Fantrax's own web application.

This module does not maintain a guessed endpoint list. It inspects the authenticated
Fantrax application shell and referenced JavaScript assets, records player/stat
service strings exposed by that application, and conservatively tests only discovered
GET-style service paths. Cookies, headers, and response bodies are never exported.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse
from typing import Any

from Knowledge.LeagueHistory.context import extract_player_season_stats

_SCRIPT_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
_SERVICE_RE = re.compile(r'(?:https?://[^"\'\\\s]+)?/(?:fxea|fxpa)/[A-Za-z0-9_./?=&%-]+', re.I)
_METHOD_RE = re.compile(r'["\']((?:get|load|fetch)[A-Za-z0-9_]*(?:Player|Stat)[A-Za-z0-9_]*)["\']')


def _redact_url(value: str) -> str:
    parsed = urlparse(value)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else parsed.path


def discover_historical_player_stats(client: Any, *, season: int, max_assets: int = 30) -> dict[str, Any]:
    root = "https://www.fantrax.com/"
    entry_urls = [
        root,
        f"{root}newui/fantasy/players.go?leagueId={client.league_id}",
    ]
    texts: list[tuple[str, str]] = []
    errors: list[str] = []
    assets: list[str] = []

    for url in entry_urls:
        try:
            response = client.session.get(url, timeout=30)
            response.raise_for_status()
            text = response.text
            texts.append((_redact_url(response.url), text))
            for src in _SCRIPT_RE.findall(text):
                absolute = urljoin(response.url, src)
                if urlparse(absolute).netloc.endswith("fantrax.com") and absolute not in assets:
                    assets.append(absolute)
        except Exception as exc:
            errors.append(f"application shell unavailable at {_redact_url(url)}: {exc}")

    for asset in assets[:max_assets]:
        try:
            response = client.session.get(asset, timeout=30)
            response.raise_for_status()
            texts.append((_redact_url(response.url), response.text))
        except Exception as exc:
            errors.append(f"asset unavailable at {_redact_url(asset)}: {exc}")

    service_candidates: set[str] = set()
    method_candidates: set[str] = set()
    for _, text in texts:
        for raw in _SERVICE_RE.findall(text):
            path = urlparse(raw).path if raw.startswith("http") else raw.split("?", 1)[0]
            lowered = path.lower()
            if "player" in lowered and ("stat" in lowered or "score" in lowered):
                service_candidates.add(path)
        for method in _METHOD_RE.findall(text):
            method_candidates.add(method)

    tested: list[dict[str, Any]] = []
    selected_payload: Any = None
    selected_source = ""
    configured = str(client.get_endpoint("player_stats") or "")
    configured_path = urlparse(configured).path if configured.startswith("http") else "/" + configured.lstrip("/")

    for path in sorted(service_candidates):
        if path.rstrip("/") == configured_path.rstrip("/"):
            continue
        try:
            payload = client.get(path, params={"season": season})
            client.validate_payload(payload, f"Discovered historical {season} player stats candidate")
            rows = extract_player_season_stats(payload)
            tested.append({"source": path, "status": "usable" if rows else "no_stat_rows", "stat_rows": len(rows)})
            if rows and selected_payload is None:
                selected_payload = payload
                selected_source = path
        except Exception as exc:
            tested.append({"source": path, "status": "rejected", "reason": str(exc)[:500]})

    return {
        "schema": "athena.fantrax_historical_player_stats_discovery.v1",
        "league_id": str(client.league_id),
        "season": int(season),
        "provider": "Fantrax",
        "strategy": "authenticated_application_source_discovery",
        "application_documents_inspected": len(texts),
        "javascript_assets_discovered": len(assets),
        "service_candidates": sorted(service_candidates),
        "fxpa_method_candidates": sorted(method_candidates),
        "tested_get_candidates": tested,
        "selected_source": selected_source,
        "selected_payload": selected_payload,
        "errors": errors,
        "secrets_exported": False,
    }
