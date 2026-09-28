"""Discover the authoritative Fantrax Draft Results data source for a league season.

The known application surface is:
    /fantasy/league/{league_id}/draft-results

Discovery is evidence-led. Fantrax Beta API documentation supplied in April 2025
and independently implemented by the go-fantrax bindings identifies
/general/getDraftResults as the draft-results endpoint. Athena tests that documented
read-only endpoint first, then falls back to authenticated application-surface
discovery if necessary. Credential values are excluded from reports.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

_SCRIPT_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
_SERVICE_RE = re.compile(r'(?:https?://[^"\'\\\s]+)?/(?:fxea|fxpa)/[A-Za-z0-9_./?=&%-]+', re.I)
# Fantrax bundles commonly expose transport method names as quoted strings. Restrict
# candidates to read-like names containing both draft and result/history semantics.
_METHOD_RE = re.compile(r'["\']((?:get|load|fetch|query)[A-Za-z0-9_]*(?:Draft)[A-Za-z0-9_]*(?:Result|History)[A-Za-z0-9_]*)["\']', re.I)
_METHOD_RE_REVERSED = re.compile(r'["\']((?:get|load|fetch|query)[A-Za-z0-9_]*(?:Result|History)[A-Za-z0-9_]*(?:Draft)[A-Za-z0-9_]*)["\']', re.I)


def _redact_url(value: str) -> str:
    parsed = urlparse(value)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else parsed.path


def _safe_keys(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    blocked = ("cookie", "secret", "token", "authorization", "password", "credential", "session")
    return [str(k) for k in value.keys() if not any(term in str(k).lower() for term in blocked)][:40]


def _find_lists(value: Any, path: str = "root", depth: int = 0) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if depth > 6:
        return found
    if isinstance(value, list):
        keys = _safe_keys(value[0]) if value and isinstance(value[0], dict) else []
        found.append({"path": path, "count": len(value), "sample_keys": keys})
        for index, item in enumerate(value[:2]):
            found.extend(_find_lists(item, f"{path}[{index}]", depth + 1))
    elif isinstance(value, dict):
        for key, item in value.items():
            if str(key) in _safe_keys(value):
                found.extend(_find_lists(item, f"{path}.{key}", depth + 1))
    return found


def _draft_result_score(payload: Any) -> int:
    """Score structural evidence only; do not infer or normalize selections."""
    score = 0
    for item in _find_lists(payload):
        keys = {key.lower() for key in item.get("sample_keys", [])}
        if item.get("count", 0) <= 0:
            continue
        if keys & {"playerid", "player_id", "playername", "player_name", "scorerid"}:
            score += 4
        if keys & {"round", "roundnumber", "roundnum"}:
            score += 2
        if keys & {"pick", "picknumber", "overallpick", "overallpicknumber"}:
            score += 2
        if keys & {"teamid", "fantasyteamid", "ownerteamid"}:
            score += 2
    return score


def discover_historical_draft_results(client: Any, *, season: int, max_assets: int = 40) -> dict[str, Any]:
    page_url = f"https://www.fantrax.com/fantasy/league/{client.league_id}/draft-results"
    documents: list[tuple[str, str]] = []
    assets: list[str] = []
    errors: list[str] = []

    try:
        response = client.session.get(page_url, timeout=30)
        response.raise_for_status()
        documents.append((_redact_url(response.url), response.text))
        for src in _SCRIPT_RE.findall(response.text):
            absolute = urljoin(response.url, src)
            if urlparse(absolute).netloc.endswith("fantrax.com") and absolute not in assets:
                assets.append(absolute)
    except Exception as exc:
        errors.append(f"draft-results page unavailable at {_redact_url(page_url)}: {exc}")

    for asset in assets[:max_assets]:
        try:
            response = client.session.get(asset, timeout=30)
            response.raise_for_status()
            documents.append((_redact_url(response.url), response.text))
        except Exception as exc:
            errors.append(f"asset unavailable at {_redact_url(asset)}: {exc}")

    service_candidates: set[str] = set()
    method_candidates: set[str] = set()
    for _, text in documents:
        for raw in _SERVICE_RE.findall(text):
            path = urlparse(raw).path if raw.startswith("http") else raw.split("?", 1)[0]
            lowered = path.lower()
            if "draft" in lowered and ("result" in lowered or "history" in lowered):
                service_candidates.add(path)
        method_candidates.update(_METHOD_RE.findall(text))
        method_candidates.update(_METHOD_RE_REVERSED.findall(text))

    tested_get: list[dict[str, Any]] = []
    tested_fxpa: list[dict[str, Any]] = []
    selected_payload: Any = None
    selected_source = ""
    selected_transport = ""

    # Fantrax Beta API documentation (April 2025) exposes this read-only endpoint.
    # leagueId is injected by FantraxClient.get(), so no season inference is needed.
    documented_endpoint = "general/getDraftResults"
    try:
        payload = client.get(documented_endpoint)
        client.validate_payload(payload, f"Historical {season} documented draft results")
        score = _draft_result_score(payload)
        tested_get.append({
            "source": documented_endpoint,
            "status": "usable" if score >= 4 else "insufficient_structure",
            "draft_result_score": score,
            "list_candidates": _find_lists(payload),
            "source_basis": "Fantrax Beta API documentation (April 2025)",
        })
        if score >= 4:
            selected_payload = payload
            selected_source = documented_endpoint
            selected_transport = "documented_fantrax_beta_api"
    except Exception as exc:
        tested_get.append({
            "source": documented_endpoint,
            "status": "rejected",
            "reason": str(exc)[:500],
            "source_basis": "Fantrax Beta API documentation (April 2025)",
        })

    for path in sorted(service_candidates):
        if path.lstrip("/") == documented_endpoint:
            continue
        try:
            payload = client.get(path, params={"season": season})
            client.validate_payload(payload, f"Historical {season} draft-results candidate")
            score = _draft_result_score(payload)
            tested_get.append({
                "source": path,
                "status": "usable" if score >= 4 else "insufficient_structure",
                "draft_result_score": score,
                "list_candidates": _find_lists(payload),
            })
            if score >= 4 and selected_payload is None:
                selected_payload = payload
                selected_source = path
                selected_transport = "get"
        except Exception as exc:
            tested_get.append({"source": path, "status": "rejected", "reason": str(exc)[:500]})

    # Only invoke read-style method names found in the authenticated Draft Results
    # application documents. This avoids speculative endpoint/method probing.
    for method in sorted(method_candidates):
        try:
            payload = client.fxpa_request({"method": method, "data": {"season": season}})
            client.validate_payload(payload, f"Historical {season} draft-results FXPA candidate")
            score = _draft_result_score(payload)
            tested_fxpa.append({
                "method": method,
                "status": "usable" if score >= 4 else "insufficient_structure",
                "draft_result_score": score,
                "list_candidates": _find_lists(payload),
            })
            if score >= 4 and selected_payload is None:
                selected_payload = payload
                selected_source = method
                selected_transport = "fxpa"
        except Exception as exc:
            tested_fxpa.append({"method": method, "status": "rejected", "reason": str(exc)[:500]})

    return {
        "schema": "athena.fantrax_historical_draft_results_discovery.v1",
        "league_id": str(client.league_id),
        "season": int(season),
        "provider": "Fantrax",
        "strategy": "documented_beta_api_then_authenticated_surface_discovery",
        "documented_endpoint": "general/getDraftResults",
        "application_surface": _redact_url(page_url),
        "application_documents_inspected": len(documents),
        "javascript_assets_discovered": len(assets),
        "service_candidates": sorted(service_candidates),
        "fxpa_method_candidates": sorted(method_candidates),
        "tested_get_candidates": tested_get,
        "tested_fxpa_candidates": tested_fxpa,
        "selected_source": selected_source,
        "selected_transport": selected_transport,
        "selected_payload": selected_payload,
        "errors": errors,
        "secrets_exported": False,
    }
