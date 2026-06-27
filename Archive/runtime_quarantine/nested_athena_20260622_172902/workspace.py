"""
Athena workspace helpers.

The workspace is Athena's current operating context. It is not a conversation
session. It describes the active profile/provider/league/season state that
Scout or another consumer can ask Athena to use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from Core.config import reload_configuration
from Core.json_utils import read_optional_json, write_json
from Core.credential_store import credential_status, load_persistent_secrets, save_fantrax_credentials
from Core.project_paths import CONFIGURATION_DIR

from Athena.exceptions import AthenaConfigurationError

WORKSPACE_FILE = CONFIGURATION_DIR / "workspace.json"
SECRETS_FILE = CONFIGURATION_DIR / "secrets.local.json"

from Core.version import ATHENA_VERSION

DEFAULT_WORKSPACE: Dict[str, Any] = {
    "workspace": {
        "mode": "fantasy_league",
        "provider": "Fantrax",
        "provider_key": "fantrax",
        "league_id": None,
        "league_name": None,
        "name": None,
        "sport": None,
        "season": None,
        "team_count": None,
        "start_date": None,
        "end_date": None,
        "scoring_style": None,
        "last_connection_test_at": None,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_sync_started_at": None,
        "last_sync_duration_seconds": None,
        "last_sync_error": None,
        "last_sync_summary": None,
        "engine_version": f"Athena v{ATHENA_VERSION}",
    }
}


def utc_now_iso() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _copy_default_workspace() -> Dict[str, Any]:
    return {"workspace": dict(DEFAULT_WORKSPACE["workspace"])}


def normalize_workspace(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normalize legacy flat or partially populated workspace payloads."""
    if payload is None:
        return _copy_default_workspace()
    if not isinstance(payload, dict):
        raise AthenaConfigurationError(f"Workspace file must contain a JSON object: {WORKSPACE_FILE}")

    if "workspace" in payload and isinstance(payload.get("workspace"), dict):
        workspace = dict(DEFAULT_WORKSPACE["workspace"])
        workspace.update(payload["workspace"])
        # Normalize legacy provider casing into a provider_key for registry use.
        if not workspace.get("provider_key") and workspace.get("provider"):
            workspace["provider_key"] = str(workspace.get("provider")).strip().lower()
        return {"workspace": workspace}

    # Preserve compatibility with older flat workspace files by wrapping them.
    workspace = dict(DEFAULT_WORKSPACE["workspace"])
    workspace.update(payload)
    if not workspace.get("provider_key") and workspace.get("provider"):
        workspace["provider_key"] = str(workspace.get("provider")).strip().lower()
    return {"workspace": workspace}


def load_workspace() -> Dict[str, Any]:
    """Load the current workspace, returning a safe default when absent."""
    return normalize_workspace(read_optional_json(WORKSPACE_FILE))


def save_workspace(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a workspace payload and return it."""
    normalized = normalize_workspace(payload)
    write_json(WORKSPACE_FILE, normalized)
    reload_configuration()
    return normalized


def update_workspace(**updates: Any) -> Dict[str, Any]:
    """Update fields within the current workspace object."""
    payload = load_workspace()
    workspace = payload.setdefault("workspace", {})
    workspace.update({key: value for key, value in updates.items() if value is not None})
    if not workspace.get("provider_key") and workspace.get("provider"):
        workspace["provider_key"] = str(workspace.get("provider")).strip().lower()
    workspace["engine_version"] = f"Athena v{ATHENA_VERSION}"
    return save_workspace(payload)


def get_workspace_value(key: str, default: Optional[Any] = None) -> Any:
    """Read a value from the active workspace object."""
    workspace = load_workspace().get("workspace", {})
    return workspace.get(key, default)


PLACEHOLDER_LEAGUE_IDS = {
    "",
    "abc123",
    "validation_league_id",
    "validation-league",
    "test_league_id_provider_registry",
    "test_league_id",
    "test_league_id_drop2",
    "placeholder",
}


def is_placeholder_league_id(value: Any) -> bool:
    """Return True when a league id is a validator/demo placeholder."""
    return str(value or "").strip().lower() in PLACEHOLDER_LEAGUE_IDS


def classify_fantrax_auth_secret(value: str) -> Dict[str, Any]:
    """Classify a Fantrax auth value without exposing the value itself."""
    from Core.credential_store import classify_auth_value

    return classify_auth_value(value)


def repair_workspace_file() -> Dict[str, Any]:
    """Normalize and repair the persisted workspace file in-place.

    This is intentionally conservative: it wraps legacy flat workspaces, removes
    known validator/demo league IDs, refreshes the engine version label, and
    preserves operation history/runtime metadata.
    """
    payload = load_workspace()
    workspace = payload.setdefault("workspace", {})
    changed = False

    if is_placeholder_league_id(workspace.get("league_id")):
        workspace["league_id"] = None
        workspace["last_sync_status"] = workspace.get("last_sync_status") or "requires_league_id"
        changed = True

    if not workspace.get("provider_key") and workspace.get("provider"):
        workspace["provider_key"] = str(workspace.get("provider")).strip().lower()
        changed = True

    engine_label = f"Athena v{ATHENA_VERSION}"
    if workspace.get("engine_version") != engine_label:
        workspace["engine_version"] = engine_label
        changed = True

    if changed or not WORKSPACE_FILE.exists():
        write_json(WORKSPACE_FILE, payload)
        reload_configuration()
    return payload


def record_operation_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Persist the latest operation result and maintain bounded history."""
    payload = load_workspace()
    workspace = payload.setdefault("workspace", {})
    safe_result = result if isinstance(result, dict) else {"result": result}
    workspace["last_operation_result"] = safe_result
    history = workspace.get("operation_history")
    if not isinstance(history, list):
        history = []
    record = dict(safe_result)
    record.setdefault("recorded_at", utc_now_iso())
    history.append(record)
    workspace["operation_history"] = history[-25:]
    return save_workspace(payload)


def load_secrets() -> Dict[str, Any]:
    """Load local secrets from Athena's persistent external credential store."""
    return load_persistent_secrets()


def save_fantrax_cookie(cookie: str) -> Dict[str, Any]:
    """Persist a Fantrax browser Cookie header and return safe metadata."""
    result = save_fantrax_credentials(cookie_header=cookie)
    reload_configuration()
    return result


def save_fantrax_auth(league_secret: str = "", cookie: str = "") -> Dict[str, Any]:
    """Persist separated Fantrax league-secret and browser-session auth."""
    result = save_fantrax_credentials(league_secret=league_secret, cookie_header=cookie)
    reload_configuration()
    return result


def secrets_status() -> Dict[str, Any]:
    """Return safe metadata about local secrets without exposing secret values."""
    return credential_status()
