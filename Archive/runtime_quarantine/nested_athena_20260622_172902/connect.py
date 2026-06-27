"""
Athena connection services.

Patch 3E.3 routes provider connection and validation through the provider
registry. Scout and future consumers call Athena only; Athena resolves the
active provider through Providers.base.registry and does not import concrete
provider clients directly.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from Core.config import reload_configuration
from Core.json_utils import write_json
from Core.project_paths import RAW_DIR

from Athena.exceptions import AthenaConfigurationError
from Athena.workspace import update_workspace, utc_now_iso
from Core.credential_store import save_fantrax_credentials


def save_fantrax_auth(league_secret: str = "", cookie: str = "") -> Dict[str, Any]:
    """Persist Fantrax auth through the external credential store.

    Defined locally for backward compatibility when Spyder has an older
    Athena.workspace module cached without save_fantrax_auth.
    """
    return save_fantrax_credentials(league_secret=league_secret, cookie_header=cookie)
from Providers.base.registry import get_provider, registered_providers


def _normalize_provider(provider: str) -> str:
    selected = str(provider or "").strip().lower()
    if not selected:
        raise AthenaConfigurationError("provider is required.")
    return selected


def infer_fantrax_context(league_payload: Any) -> Dict[str, Any]:
    """Infer sport/season/league metadata from Fantrax league information."""
    inferred: Dict[str, Any] = {
        "provider": "Fantrax",
        "sport": "unknown",
        "season": "unknown",
        "name": "unknown",
        "league_name": "unknown",
        "team_count": 0,
        "scoring_style": "unknown",
    }
    if not isinstance(league_payload, dict):
        return inferred

    league_name = league_payload.get("leagueName") or league_payload.get("name") or "unknown"
    inferred["name"] = league_name
    inferred["league_name"] = league_name
    inferred["season"] = str(league_payload.get("seasonYear") or league_payload.get("season") or "unknown")
    inferred["start_date"] = league_payload.get("startDate") or ""
    inferred["end_date"] = league_payload.get("endDate") or ""

    team_info = league_payload.get("teamInfo")
    if isinstance(team_info, dict):
        inferred["team_count"] = len(team_info)
    elif isinstance(team_info, list):
        inferred["team_count"] = len(team_info)

    roster_info = league_payload.get("rosterInfo") if isinstance(league_payload.get("rosterInfo"), dict) else {}
    position_constraints = roster_info.get("positionConstraints") if isinstance(roster_info.get("positionConstraints"), dict) else {}
    position_keys = {str(key).upper() for key in position_constraints.keys()}
    if {"C", "LW", "RW", "D"}.intersection(position_keys):
        inferred["sport"] = "NHL"
    elif league_payload.get("sport"):
        inferred["sport"] = str(league_payload.get("sport"))

    scoring = league_payload.get("scoringSystem")
    if isinstance(scoring, dict):
        scoring_text = json.dumps(scoring).lower()
        if "goal" in scoring_text or "assist" in scoring_text or "point" in scoring_text:
            inferred["scoring_style"] = "points/production based"
        else:
            inferred["scoring_style"] = "custom"
    elif scoring:
        inferred["scoring_style"] = str(scoring)

    return inferred


def infer_provider_context(provider: str, league_payload: Any) -> Dict[str, Any]:
    """Infer provider context using the provider-specific context parser."""
    selected = _normalize_provider(provider)
    if selected == "fantrax":
        return infer_fantrax_context(league_payload)
    return {
        "provider": provider,
        "sport": "unknown",
        "season": "unknown",
        "name": "unknown",
        "league_name": "unknown",
        "team_count": 0,
        "scoring_style": "unknown",
    }


def connect_provider(
    *,
    provider: str,
    league_id: str | None = None,
    auth_cookie: str = "",
    cookie: str = "",
    validate: bool = True,
    mode: str = "fantasy_league",
    **extra: Any,
) -> Dict[str, Any]:
    """Connect Athena to a provider through the provider registry."""
    selected = _normalize_provider(provider)
    provider_instance = get_provider(selected)

    cleaned_league_id = str(league_id or "").strip()
    if selected == "fantrax" and not cleaned_league_id:
        raise AthenaConfigurationError("Fantrax league_id is required.")

    workspace_provider_name = getattr(provider_instance, "provider_name", provider)
    secret_keys = {"league_secret", "secret", "auth_cookie", "cookie", "browser_cookie", "password", "token"}
    workspace_extra = {
        key: value for key, value in extra.items()
        if value is not None and str(key).lower() not in secret_keys
    }
    update_workspace(
        mode=mode,
        provider=workspace_provider_name,
        provider_key=selected,
        league_id=cleaned_league_id or None,
        last_connection_test_at=None,
        **workspace_extra,
    )

    # Local alpha compatibility: Fantrax auth remains stored in the local
    # secrets file, but connection validation goes through the provider adapter.
    supplied_cookie = auth_cookie or cookie
    supplied_league_secret = str(extra.get("league_secret") or extra.get("secret") or "").strip()
    secret_status: Dict[str, Any] = {}
    if selected == "fantrax" and (supplied_cookie or supplied_league_secret):
        secret_status = save_fantrax_auth(league_secret=supplied_league_secret, cookie=supplied_cookie)

    reload_configuration()

    connection_result: Dict[str, Any]
    if validate:
        connection_result = provider_instance.connect(
            league_id=cleaned_league_id,
            auth_cookie=supplied_cookie,
            cookie=supplied_cookie,
            mode=mode,
            **extra,
        )
    else:
        connection_result = {
            "ok": True,
            "provider": workspace_provider_name,
            "provider_key": selected,
            "state": "disconnected",
            "authenticated": False,
            "message": "Workspace saved; provider validation was skipped.",
        }

    inferred: Dict[str, Any] = {}
    raw_saved = False
    provider_test: Dict[str, Any] | None = None

    if validate:
        provider_test = provider_instance.test(
            league_id=cleaned_league_id,
            auth_cookie=supplied_cookie,
            cookie=supplied_cookie,
            mode=mode,
            **extra,
        )
        if not provider_test.get("ok"):
            return {
                "ok": False,
                "provider": workspace_provider_name,
                "provider_key": selected,
                "registered_providers": registered_providers(),
                "league_id": cleaned_league_id,
                "validated": True,
                "connection": connection_result,
                "provider_test": provider_test,
                "message": provider_test.get("message", "Provider validation failed."),
                "error": provider_test.get("error", "Provider validation failed."),
                "secret_status": secret_status,
            }

        # Fetch the authoritative league payload through the provider adapter so
        # Athena can infer workspace context and save the raw league file without
        # importing the concrete Fantrax client.
        league_payload = provider_instance.fetch("league")
        if isinstance(league_payload, dict):
            write_json(RAW_DIR / "league_info.json", league_payload)
            raw_saved = True
            inferred = infer_provider_context(selected, league_payload)
            # Prevent provider/provider_key/league_id from being passed twice when
            # provider-specific inference includes display metadata such as provider.
            workspace_inferred = {
                key: value for key, value in inferred.items()
                if key not in {"provider", "provider_key", "league_id"}
            }
            update_workspace(
                mode=mode,
                provider=workspace_provider_name,
                provider_key=selected,
                league_id=cleaned_league_id or None,
                **workspace_inferred,
                last_connection_test_at=utc_now_iso(),
            )

    return {
        "ok": True,
        "provider": workspace_provider_name,
        "provider_key": selected,
        "registered_providers": registered_providers(),
        "league_id": cleaned_league_id,
        "validated": bool(validate),
        "raw_saved": raw_saved,
        "inferred_context": inferred,
        "connection": connection_result,
        "provider_test": provider_test,
        "provider_status": provider_instance.status().to_dict(),
        "secret_status": secret_status,
        "message": f"{workspace_provider_name} connection succeeded." if validate else f"{workspace_provider_name} workspace saved.",
    }


def connect_fantrax(
    *,
    league_id: str,
    auth_cookie: str = "",
    league_secret: str = "",
    validate: bool = True,
    mode: str = "fantasy_league",
) -> Dict[str, Any]:
    """Compatibility wrapper for existing callers."""
    return connect_provider(
        provider="fantrax",
        league_id=league_id,
        auth_cookie=auth_cookie,
        league_secret=league_secret,
        validate=validate,
        mode=mode,
    )
