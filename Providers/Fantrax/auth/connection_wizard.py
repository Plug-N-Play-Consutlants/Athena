"""Fantrax guided connection workflow.

This module intentionally does not scrape browser profiles or passwords.  It
opens Fantrax for a normal user-owned login session, stores credentials in the
persistent Athena credential store, and runs the best available connection/sync
sequence using credentials already available to Athena.
"""

from __future__ import annotations

from dataclasses import dataclass
import webbrowser
from typing import Any, Dict

import Athena
from Athena.workspace import load_workspace, update_workspace
from Core.credential_store import credential_status, save_fantrax_credentials


def save_fantrax_auth(league_secret: str = "", cookie: str = "") -> Dict[str, Any]:
    """Persist Fantrax auth through the external credential store.

    This avoids import failures if Athena.workspace is stale in Spyder's
    autoreload cache.
    """
    return save_fantrax_credentials(league_secret=league_secret, cookie_header=cookie)


FANTRAX_HOME = "https://www.fantrax.com/"
INVALID_LEAGUE_IDS = {
    "",
    "abc123",
    "validation_league_id",
    "test_league_id_provider_registry",
    "test_league_id",
    "placeholder",
}


def is_placeholder_league_id(value: str | None) -> bool:
    """Return True for validator/demo league IDs that must never drive live Fantrax navigation."""
    return str(value or "").strip().lower() in INVALID_LEAGUE_IDS



def fantrax_league_url(league_id: str = "") -> str:
    cleaned = str(league_id or "").strip()
    if cleaned:
        return f"https://www.fantrax.com/fantasy/league/{cleaned}/home"
    return FANTRAX_HOME


def active_league_id(fallback: str = "") -> str:
    """Resolve a live-safe Fantrax league ID.

    Workspace is authoritative. Explicit fallback values from validators/UI are
    only accepted when they are not known placeholders. This prevents test IDs
    such as abc123 from leaking into live navigation or sync paths.
    """
    workspace = load_workspace().get("workspace", {})
    workspace_value = str(workspace.get("league_id") or "").strip()
    fallback_value = str(fallback or "").strip()
    if workspace_value and not is_placeholder_league_id(workspace_value):
        return workspace_value
    if fallback_value and not is_placeholder_league_id(fallback_value):
        return fallback_value
    return ""


def sanitize_live_workspace_league_id() -> Dict[str, Any]:
    """Remove validator/demo league IDs from the live workspace.

    The function intentionally does not invent a replacement league ID. If no
    valid league is known, Scout should ask the user to enter/connect one.
    """
    workspace = load_workspace().get("workspace", {})
    current = str(workspace.get("league_id") or "").strip()
    if not current or not is_placeholder_league_id(current):
        return {"ok": True, "changed": False, "league_id": current, "message": "Workspace league ID is live-safe."}
    update_workspace(league_id="", last_sync_status="requires_league_id")
    return {
        "ok": True,
        "changed": True,
        "removed_league_id": current,
        "league_id": "",
        "message": "Removed validator/demo Fantrax league ID from live workspace.",
    }


def open_fantrax_login(league_id: str = "") -> Dict[str, Any]:
    selected = active_league_id(league_id)
    url = fantrax_league_url(selected)
    opened = bool(webbrowser.open(url, new=2))
    return {
        "ok": opened,
        "url": url,
        "league_id": selected,
        "message": "Fantrax opened in the system browser." if opened else "Fantrax browser open request was not accepted by the OS.",
    }


def connection_capability_status() -> Dict[str, Any]:
    status = credential_status()
    cookie_ready = bool(status.get("fantrax_cookie_parseable"))
    league_ready = bool(status.get("fantrax_league_secret_present"))
    return {
        **status,
        "league_access_ready": league_ready,
        "browser_session_ready": cookie_ready,
        "transaction_sync_ready": cookie_ready,
        "one_click_ready": cookie_ready,
    }


def guided_connect_and_sync(
    *,
    league_id: str = "",
    league_secret: str = "",
    cookie_header: str = "",
    open_browser: bool = True,
    run_sync: bool = True,
) -> Dict[str, Any]:
    """Run Athena's best available Fantrax connect flow.

    If a parseable browser Cookie is already saved or supplied, the workflow can
    validate and sync.  Without a session Cookie, the workflow opens Fantrax and
    returns a bounded action state instead of pretending it captured auth.
    """
    selected_league_id = active_league_id(league_id)
    if league_secret or cookie_header:
        save_fantrax_auth(league_secret=league_secret, cookie=cookie_header)

    before = connection_capability_status()
    opened: Dict[str, Any] | None = None
    if open_browser:
        opened = open_fantrax_login(selected_league_id)

    if not selected_league_id:
        return {
            "ok": False,
            "status": "league_id_required",
            "stage": "initialize",
            "message": "Fantrax league ID is required before Scout can connect and sync.",
            "credential_status": before,
            "opened": opened,
            "next_action": "Enter the Fantrax league ID, then run Connect Fantrax & Sync again.",
        }

    if not before.get("browser_session_ready"):
        return {
            "ok": False,
            "status": "browser_session_required",
            "stage": "browser_login",
            "message": "Scout opened Fantrax, but Athena does not yet have a captured browser session Cookie.",
            "credential_status": before,
            "opened": opened,
            "next_action": (
                "Log in to Fantrax in the opened browser. Automatic session capture is not enabled in this local alpha yet; "
                "the Advanced Cookie bridge remains available for validation."
            ),
            "known_limitation": "Athena does not scrape browser password stores or silently read browser profiles.",
        }

    connect_result = Athena.connect_fantrax(
        league_id=selected_league_id,
        auth_cookie="",
        league_secret=league_secret,
        validate=True,
        mode="fantasy_league",
    )
    sync_result: Dict[str, Any] | None = None
    if run_sync and connect_result.get("ok"):
        sync_result = Athena.sync(mode="fantasy_league", provider="Fantrax", fetch=True)

    return {
        "ok": bool(connect_result.get("ok")) and (sync_result is None or bool(sync_result.get("ok"))),
        "status": "connected_and_synced" if sync_result and sync_result.get("ok") else "connected",
        "stage": "completed",
        "message": "Fantrax connected and synced using saved browser-session auth." if sync_result else "Fantrax connected using saved browser-session auth.",
        "credential_status": connection_capability_status(),
        "opened": opened,
        "connect_result": connect_result,
        "sync_result": sync_result,
    }
