"""
Fetch Fantrax live player pool / team roster data.

Fetch layer responsibility:
- Call Fantrax or a configured Fantrax export URL.
- Save raw provider payload.
- Do not normalize, score, or analyze.

Preferred live routes tested by this module:
- general/getTeamRosters
- general/getLeagueInfo

These are tried with leagueId automatically included by FantraxClient. If a
private league requires authentication, add a local Cookie header via the
FANTRAX_COOKIE environment variable or local config only.

Output:
    Raw/fantrax_player_pool.json
    Logs/fantrax_player_pool_fetch.json
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from Core.config import get_config_value, get_workspace_value
from Core.json_utils import write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import LOGS_DIR, RAW_DIR
from Providers.Fantrax.fantrax_client import FantraxClient


OUTPUT_JSON = RAW_DIR / "fantrax_player_pool.json"
LOG_JSON = LOGS_DIR / "fantrax_player_pool_fetch.json"


CONFIGURED_SOURCE_KEYS = [
    "provider.endpoints.player_pool",
    "provider.endpoints.team_rosters",
    "provider.endpoints.rosters",
    "provider.endpoints.player_pool_export",
    "provider.player_pool_export_url",
    "provider.player_export_url",
]

LIVE_CANDIDATES = [
    {
        "endpoint": "general/getTeamRosters",
        "method": "get",
        "params": {},
        "source_type": "fantrax_live_team_rosters",
    },
    {
        "endpoint": "general/getTeamRosters",
        "method": "post",
        "params": {},
        "source_type": "fantrax_live_team_rosters",
    },
    {
        "endpoint": "general/getLeagueInfo",
        "method": "get",
        "params": {},
        "source_type": "fantrax_live_league_info_rosters",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_full_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def _looks_like_csv(text: str, content_type: str = "") -> bool:
    lowered_type = content_type.lower()
    if "csv" in lowered_type or "text/plain" in lowered_type:
        return True
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return "," in first_line and any(token in first_line for token in ["Player", "ID", "Contract", "Status"])


def _parse_csv_text(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(StringIO(text))
    return [dict(row) for row in reader]


def _load_local_fantrax_export() -> tuple[list[dict[str, Any]], Path | None]:
    candidates = sorted(RAW_DIR.glob("Fantrax-Players*.csv")) + sorted(RAW_DIR.glob("fantrax-players*.csv"))
    for path in candidates:
        try:
            with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                rows = [dict(row) for row in csv.DictReader(csv_file)]
                if rows:
                    return rows, path
        except UnicodeDecodeError:
            with path.open("r", newline="", encoding="latin-1") as csv_file:
                rows = [dict(row) for row in csv.DictReader(csv_file)]
                if rows:
                    return rows, path
    return [], None


def _context_value(context: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = context.get(key)
        if value not in (None, ""):
            return value
    return ""


def _team_context_from_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "fantasy_team_id": _context_value(row, "teamId", "team_id", "id", "teamID"),
        "fantasy_team": _context_value(row, "teamName", "team_name", "name", "displayName"),
        "manager": _context_value(row, "owner", "ownerName", "manager", "managerName", "userName"),
    }


def _flatten_roster_item(item: dict[str, Any], team_context: dict[str, Any], source_path: str) -> dict[str, Any]:
    row = dict(item)

    # Fantrax sometimes nests player facts under player/playerInfo/scorer.
    for nested_key in ("player", "playerInfo", "scorer", "proPlayer", "playerData"):
        nested = item.get(nested_key)
        if isinstance(nested, dict):
            for key, value in nested.items():
                row.setdefault(key, value)
                row.setdefault(f"{nested_key}_{key}", value)

    for key, value in team_context.items():
        if value not in (None, ""):
            row.setdefault(key, value)

    row.setdefault("source_path", source_path)
    return row


def _looks_like_player_row(row: dict[str, Any]) -> bool:
    keys = {str(key).lower() for key in row.keys()}
    player_keys = {
        "player",
        "playername",
        "player_name",
        "name",
        "id",
        "playerid",
        "player_id",
        "fantraxid",
        "fantrax_player_id",
        "contract",
        "status",
        "position",
        "pos",
    }
    return bool(keys.intersection(player_keys)) and (
        any("player" in key for key in keys) or "contract" in keys or "status" in keys or "position" in keys or "pos" in keys
    )


def _extract_records_from_json(payload: Any) -> list[dict[str, Any]]:
    """Extract likely player rows, including nested team rosterItems."""
    records: list[dict[str, Any]] = []
    seen: set[int] = set()

    def add_record(row: dict[str, Any], team_context: dict[str, Any], source_path: str) -> None:
        flat = _flatten_roster_item(row, team_context, source_path)
        marker = id(row)
        if marker not in seen and _looks_like_player_row(flat):
            records.append(flat)
            seen.add(marker)

    def walk(node: Any, team_context: dict[str, Any] | None = None, path: str = "root") -> None:
        context = dict(team_context or {})
        if isinstance(node, dict):
            local_team = _team_context_from_dict(node)
            for key, value in local_team.items():
                if value not in (None, ""):
                    context[key] = value

            for roster_key in ("rosterItems", "roster_items", "players", "playerList", "items"):
                value = node.get(roster_key)
                if isinstance(value, list):
                    for index, item in enumerate(value):
                        if isinstance(item, dict):
                            add_record(item, context, f"{path}.{roster_key}[{index}]")

            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, context, f"{path}.{key}")

        elif isinstance(node, list):
            # A top-level list can itself be a player list.
            dict_items = [item for item in node if isinstance(item, dict)]
            if dict_items and sum(1 for item in dict_items if _looks_like_player_row(item)) >= max(1, len(dict_items) // 2):
                for index, item in enumerate(dict_items):
                    add_record(item, context, f"{path}[{index}]")
            else:
                for index, item in enumerate(node):
                    walk(item, context, f"{path}[{index}]")

    walk(payload)
    return records


def _wrap_payload(
    *,
    records: list[dict[str, Any]],
    source_type: str,
    source_reference: str,
    is_live: bool,
    raw_payload: Any | None = None,
) -> dict[str, Any]:
    return {
        "source": "fantrax",
        "source_type": source_type,
        "source_reference": source_reference,
        "is_live": is_live,
        "fetched_at": _utc_now(),
        "record_count": len(records),
        "records": records,
        "raw_payload": raw_payload,
        "notes": [
            "Fantrax player pool should be treated as source of truth for fantasy ownership/status/contracts when is_live is true.",
            "Local CSV fallback is a snapshot only and can become stale when waivers, free agents, claims, drops, or contracts change.",
        ],
    }


def _attempt_payload(client: FantraxClient, endpoint_or_url: str, method: str, params: dict[str, Any], source_type: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    attempt = {
        "strategy": "live_fantrax_payload",
        "endpoint_or_url": endpoint_or_url,
        "method": method,
        "params": params,
        "success": False,
        "record_count": 0,
        "error": "",
        "http_status": None,
        "used_cookie_auth": client.has_cookie_auth(),
    }

    try:
        if _is_full_url(endpoint_or_url):
            response = client.session.get(endpoint_or_url, timeout=30)
            attempt["http_status"] = response.status_code
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            text = response.text
            if _looks_like_csv(text, content_type):
                records = _parse_csv_text(text)
                attempt.update({"success": bool(records), "record_count": len(records), "content_type": content_type})
                if records:
                    return _wrap_payload(
                        records=records,
                        source_type="fantrax_live_player_pool_csv_export",
                        source_reference=endpoint_or_url,
                        is_live=True,
                        raw_payload=None,
                    ), attempt
            payload = response.json()
        else:
            if method == "post":
                response = client.post_response(endpoint_or_url, payload=params, include_league_id=True)
            else:
                response = client.get_response(endpoint_or_url, params=params, include_league_id=True)
            attempt["http_status"] = response.status_code
            payload = response.json()

        if client.is_error_payload(payload):
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            attempt["error"] = f"Fantrax error payload: {error}"
            return None, attempt

        records = _extract_records_from_json(payload)
        attempt.update({"success": bool(records), "record_count": len(records)})
        if records:
            return _wrap_payload(
                records=records,
                source_type=source_type,
                source_reference=endpoint_or_url,
                is_live=True,
                raw_payload=payload,
            ), attempt

        attempt["error"] = "Payload returned but no roster/player rows were detected."
    except Exception as exc:  # noqa: BLE001 - diagnostics should capture any fetch failure
        attempt["error"] = str(exc)

    return None, attempt


def _configured_sources() -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    for key in CONFIGURED_SOURCE_KEYS:
        value = _safe_str(get_config_value(key, ""))
        if value:
            sources.append((key, value))
    return sources


def _period_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = [{}]
    period = _safe_str(get_workspace_value("workspace.period", "") or get_config_value("provider.period", ""))
    if period:
        candidates.append({"period": period})
    return candidates


def main() -> None:
    log_header("FETCH FANTRAX PLAYER POOL")

    client = FantraxClient()
    attempts: list[dict[str, Any]] = []
    wrapped_payload: dict[str, Any] | None = None

    configured = _configured_sources()
    if configured:
        log_section("Configured Live Sources")
        for key, endpoint_or_url in configured:
            safe_value = endpoint_or_url if "cookie" not in key.lower() else "[hidden]"
            log(f"  - {key}: {safe_value}")
            wrapped_payload, attempt = _attempt_payload(
                client,
                endpoint_or_url=endpoint_or_url,
                method="get",
                params={},
                source_type="fantrax_configured_player_pool",
            )
            attempt["config_key"] = key
            attempts.append(attempt)
            if wrapped_payload:
                break

    if not wrapped_payload:
        log_section("Built-in Live Candidate Routes")
        for candidate in LIVE_CANDIDATES:
            for params in _period_candidates():
                endpoint = candidate["endpoint"]
                method = candidate["method"]
                log(f"Trying {method.upper()} {endpoint} params={params}")
                wrapped_payload, attempt = _attempt_payload(
                    client,
                    endpoint_or_url=endpoint,
                    method=method,
                    params=params,
                    source_type=candidate["source_type"],
                )
                attempts.append(attempt)
                if wrapped_payload:
                    break
            if wrapped_payload:
                break

    if not wrapped_payload:
        rows, path = _load_local_fantrax_export()
        if rows and path:
            wrapped_payload = _wrap_payload(
                records=rows,
                source_type="fantrax_player_export_snapshot",
                source_reference=str(path),
                is_live=False,
                raw_payload=None,
            )
            attempts.append(
                {
                    "strategy": "local_csv_snapshot_fallback",
                    "source_path": str(path),
                    "success": True,
                    "record_count": len(rows),
                    "is_live": False,
                    "warning": "Snapshot fallback is not live. Configure cookie auth or a working live endpoint/export URL for live state.",
                }
            )
        else:
            attempts.append(
                {
                    "strategy": "local_csv_snapshot_fallback",
                    "success": False,
                    "record_count": 0,
                    "error": "No Raw/Fantrax-Players*.csv fallback snapshot found.",
                }
            )

    diagnostic = {
        "fetched_at": _utc_now(),
        "output_file": str(OUTPUT_JSON),
        "success": wrapped_payload is not None,
        "is_live": bool(wrapped_payload and wrapped_payload.get("is_live")),
        "record_count": int(wrapped_payload.get("record_count", 0)) if wrapped_payload else 0,
        "used_cookie_auth": client.has_cookie_auth(),
        "attempts": attempts,
    }
    write_json(LOG_JSON, diagnostic)

    if not wrapped_payload:
        log_section("No Player Pool Source Found")
        log(f"Discovery/fetch log: {LOG_JSON}")
        log("No Raw/fantrax_player_pool.json file was overwritten.")
        raise RuntimeError("Could not fetch a live Fantrax player pool and no local CSV fallback was found.")

    write_json(OUTPUT_JSON, wrapped_payload)

    log_section("Fetch Summary")
    log(f"Source Type: {wrapped_payload.get('source_type')}")
    log(f"Live Source: {wrapped_payload.get('is_live')}")
    log(f"Rows: {wrapped_payload.get('record_count')}")
    log(f"Output: {OUTPUT_JSON}")
    log(f"Fetch Log: {LOG_JSON}")

    if not wrapped_payload.get("is_live"):
        log("")
        log("Important: this run used a local Fantrax CSV snapshot fallback, not live Fantrax state.")
        log("If the built-in general/getTeamRosters attempt failed, add FANTRAX_COOKIE locally and rerun.")

    log("Completed successfully.")


if __name__ == "__main__":
    main()
