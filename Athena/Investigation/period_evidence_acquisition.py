"""Bounded, auditable acquisition of scoring-period player production.

This adapter does not guess Fantrax endpoints or treat a nonempty response as
verified production. It reports the actual attempt and temporal validation.
"""
from __future__ import annotations
from typing import Any
import re

_SAFE = re.compile(r"[^a-zA-Z0-9 _.,:;()/-]")

def _safe_error(payload: Any) -> dict:
    """Expose provider code/message, never response bodies, cookies or request URLs."""
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        code = error.get("code") or error.get("errorCode") or "provider_error"
        message = error.get("message") or error.get("errorMessage") or "Fantrax rejected request"
    elif isinstance(error, str):
        code, message = "provider_error", error
    else:
        # Some Fantrax error envelopes use top-level code/message fields.
        # Extract only explicit diagnostic fields, never serialize payloads.
        if isinstance(payload, dict):
            code = payload.get("errorCode") or payload.get("code") or "provider_error"
            message = payload.get("errorMessage") or payload.get("message") or "Fantrax rejected request"
        else:
            code, message = "provider_error", "Fantrax rejected request"
    def clean(value):
        value = str(value)[:160] if isinstance(value, (str, int, float)) else "unavailable"
        value = re.sub(r"https?://\S+", "[url]", value)
        value = re.sub(r"(?i)(token|cookie|session|authorization|password|secret)\s*[:=]\s*\S+", r"\1=[redacted]", value)
        return _SAFE.sub("?", value)[:160]
    return {"code": clean(code), "message": clean(message)}


# Strictly allowlisted structure metadata. No player names, IDs, league values,
# cookie/session information, raw responses, or arbitrary provider strings.
_INSPECT_KEYS = frozenset((
    "responses", "data", "statsTable", "tableHeader", "cells",
    "paginatedResultSet", "seasonOrProjections", "posOrGroupList",
    "statusOrTeamList", "players", "records", "period", "scoringPeriod",
    "season", "totalCount", "totalResults", "rows", "playerStats",
    "headers", "pagination", "error", "code", "message",
))
_STATS_LABELS = frozenset(("G", "A", "GP", "PTS", "GOALS", "ASSISTS", "G+A"))

def inspect_player_stats_schema(payload: Any) -> dict:
    """Summarize safe structure only; no response contents or dynamic keys."""
    def shape(value):
        if isinstance(value, dict):
            return "object"
        if isinstance(value, list):
            return "list"
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, str):
            return "string"
        return "other"
    def keys(value):
        return sorted(k for k in value if isinstance(k, str) and k in _INSPECT_KEYS) if isinstance(value, dict) else []
    result = {"response_type": shape(payload), "top_keys": keys(payload)}
    if not isinstance(payload, dict):
        return result
    data = payload.get("data", payload)
    if isinstance(payload.get("responses"), list):
        responses = payload["responses"]
        result["response_count"] = min(len(responses), 100000)
        if responses and isinstance(responses[0], dict):
            data = responses[0].get("data", responses[0])
    result["data_type"] = shape(data)
    result["data_keys"] = keys(data)
    if not isinstance(data, dict):
        return result
    for field in ("statsTable", "paginatedResultSet", "players", "records",
                  "seasonOrProjections", "posOrGroupList", "statusOrTeamList"):
        if field not in data:
            continue
        value = data[field]
        result[field + "_type"] = shape(value)
        if isinstance(value, list):
            result[field + "_count"] = min(len(value), 100000)
        elif isinstance(value, dict):
            result[field + "_keys"] = keys(value)
    header = data.get("tableHeader")
    if isinstance(header, dict):
        result["tableHeader_keys"] = keys(header)
        cells = header.get("cells")
        if isinstance(cells, list):
            result["header_cell_count"] = min(len(cells), 100000)
            found = set()
            for cell in cells[:500]:
                if isinstance(cell, dict):
                    for field in ("name", "label", "shortName", "title"):
                        value = cell.get(field)
                        if isinstance(value, str) and value.strip().upper() in _STATS_LABELS:
                            found.add(value.strip().upper())
            result["recognized_stat_headers"] = sorted(found)
    # Inspect nested shapes and fixed allowlisted selector metadata, never raw values.
    def item_shape(value):
        if not isinstance(value, dict):
            return {"type": shape(value)}
        allowed = frozenset(("cells", "value", "label", "name", "shortName", "title", "id", "key", "code", "selected", "default", "isSelected", "stats", "statsCells", "player", "playerId", "scoringPeriod", "season", "year", "period", "total", "totalCount", "pageNumber", "maxResultsPerPage", "currentPage", "totalPages", "results", "rows", "sort", "display", "displayName", "group", "position", "statId", "statName", "statCategory", "column", "columnId", "type", "data", "stat", "header", "filter"))
        out = {"keys": sorted(k for k in value if isinstance(k, str) and k in allowed)}
        for key in ("cells", "statsCells", "stats", "rows", "data"):
            if key in value:
                out[key + "_type"] = shape(value[key])
                if isinstance(value[key], list):
                    out[key + "_count"] = min(len(value[key]), 100000)
                    if value[key]:
                        out[key + "_first_type"] = shape(value[key][0])
                        if isinstance(value[key][0], dict):
                            out[key + "_first_keys"] = sorted(k for k in value[key][0] if isinstance(k, str) and k in allowed)
        return out
    if isinstance(header, dict) and isinstance(header.get("cells"), list):
        result["header_cell_shapes"] = [item_shape(cell) for cell in header["cells"][:15]]
    rows = data.get("statsTable")
    if isinstance(rows, list) and rows:
        result["first_stats_row_shape"] = item_shape(rows[0])
    for selector in ("seasonOrProjections", "posOrGroupList", "statusOrTeamList"):
        items = data.get(selector)
        if isinstance(items, list) and items:
            result[selector + "_first_item_shape"] = item_shape(items[0])
            # Boolean selection flags only; no IDs, option values or labels.
            result[selector + "_selection_flags"] = {
                flag: sum(1 for item in items if isinstance(item, dict) and item.get(flag) is True)
                for flag in ("selected", "isSelected", "default")
            }
    page = data.get("paginatedResultSet")
    if isinstance(page, dict):
        result["pagination_shape"] = item_shape(page)
    # Provider column names and selector codes are *schema metadata*, not player data.
    # Emit only bounded, printable, credential-safe labels for reproducible mapping.
    def safe_label(value):
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value or len(value) > 72 or any(x in value.lower() for x in ("token", "cookie", "secret", "password", "session", "authorization", "bearer", "http", "@", "private", "sensitive")):
            return None
        if not re.fullmatch(r"[A-Za-z0-9 _./:+()\-]{1,72}", value):
            return None
        return value
    if isinstance(header, dict) and isinstance(header.get("cells"), list):
        result["header_columns"] = [
            {field: label for field in ("key", "name", "shortName")
             if (label := safe_label(cell.get(field))) is not None}
            if isinstance(cell, dict) else {}
            for cell in header["cells"][:32]
        ]
    options = data.get("seasonOrProjections")
    if isinstance(options, list):
        result["season_option_metadata"] = [
            {field: label for field in ("code", "name", "shortName")
             if (label := safe_label(item.get(field))) is not None}
            for item in options[:100] if isinstance(item, dict)
        ]
    page = data.get("paginatedResultSet")
    if isinstance(page, dict):
        result["pagination_values"] = {
            field: int(page[field]) for field in ("pageNumber", "maxResultsPerPage", "totalCount", "totalResults", "totalPages")
            if isinstance(page.get(field), int) and not isinstance(page.get(field), bool) and 0 <= page[field] <= 10000000
        }
        # Pagination completeness must be demonstrated, not assumed from 500 rows.
        count = result.get("statsTable_count")
        pv = result["pagination_values"]
        if isinstance(count, int) and pv.get("maxResultsPerPage"):
            result["page_full"] = count >= pv["maxResultsPerPage"]
    return result


def acquire_player_period_production(*, league_id: str | None, season: Any,
                                     period: int | None, client_factory=None) -> dict:
    result = {"status": "not_attempted", "attempted": False, "verified": False,
              "period": period, "records": [], "reason": "", "diagnostic": {}}
    if not league_id or not season or period is None:
        result["reason"] = "League, season and scoring period are required"
        return result
    if client_factory is None:
        from Providers.Fantrax.fantrax_client import FantraxClient
        client_factory = FantraxClient
    try:
        client = client_factory(league_id=league_id, season=season)
        # The documented public fxea surface has no player-statistics URL.
        # The established authenticated fxpa/req transport owns this method.
        if not client.has_cookie_auth():
            result["reason"] = "Authenticated Fantrax access unavailable"
            return result
        result["attempted"] = True
        # A period parameter is a request, not proof of period-specific response.
        # Only the season selector is now independently evidenced by Fantrax.
        # A BY_PERIOD selection without a verified period argument does NOT
        # establish an individual scoring week; retain the verification gate.
        requested_season = str(season).strip()
        selector = "SEASON_31n_BY_PERIOD" if requested_season in ("2026", "2026-27", "2026/27") else None
        request_params = {"seasonOrProjection": selector} if selector else {}
        payload = client.get_player_stats(params=request_params)
        if selector:
            result["diagnostic"]["requested_season_selector"] = selector
            result["diagnostic"]["period_filter_status"] = "not_verified"
        if client.is_error_payload(payload):
            result.update(status="source_error", reason="Fantrax rejected the configured player-stats request",
                              diagnostic=_safe_error(payload))
            return result
        # Inspect shape before period verification; never log private raw payload.
        result["schema_inspection"] = inspect_player_stats_schema(payload)
        # Only accept an explicit period- and season-attributed collection.
        # Ambiguous payloads are retained as unverified, never interpreted as G+A.
        if not isinstance(payload, dict):
            result.update(status="unverified_source", reason="Internal player-stats response lacks independently validated period attribution")
            return result
        observed_period = payload.get("period", payload.get("scoringPeriod"))
        observed_season = payload.get("season")
        try:
            matches = int(observed_period) == int(period) and str(observed_season) == str(season)
        except (ValueError, TypeError):
            matches = False
        if not matches:
            result.update(status="unverified_period", reason="Internal player-stats response did not explicitly confirm requested season and scoring period")
            return result
        records = payload.get("players", payload.get("records"))
        if not isinstance(records, list) or not records:
            result.update(status="invalid_schema", reason="No period-attributed player records")
            return result
        valid = [item for item in records if isinstance(item, dict)
                 and (item.get("player_id") or item.get("playerId"))
                 and isinstance(item.get("goals"), (int, float))
                 and isinstance(item.get("assists"), (int, float))]
        if len(valid) != len(records):
            result.update(status="invalid_schema", reason="Some records lack player identity or numeric G+A")
            return result
        result.update(status="verified", verified=True, records=valid,
                      reason=f"{len(valid)} season/period-attributed player production records")
    except Exception as exc:
        # Never serialize exception messages: requests exceptions may include
        # authenticated URLs or other credentials in their string form.
        result.update(status="failed" if result["attempted"] else "not_attempted",
                      reason=f"{type(exc).__name__} during player-stat acquisition",
                      diagnostic={"exception_type": type(exc).__name__})
    return result
