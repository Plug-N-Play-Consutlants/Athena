"""
Shared configuration helpers.
"""

from typing import Any, Dict

from Core.json_utils import read_optional_json
from Core.project_paths import CONFIGURATION_DIR
from Core.credential_store import load_persistent_secrets


CONFIG_FILE = CONFIGURATION_DIR / "config.json"
CONFIG_EXAMPLE_FILE = CONFIGURATION_DIR / "config.example.json"

WORKSPACE_FILE = CONFIGURATION_DIR / "workspace.json"
WORKSPACE_EXAMPLE_FILE = CONFIGURATION_DIR / "workspace.example.json"

SECRETS_FILE = CONFIGURATION_DIR / "secrets.local.json"
SECRETS_EXAMPLE_FILE = CONFIGURATION_DIR / "secrets.example.json"


def load_config() -> Dict[str, Any]:
    config = read_optional_json(CONFIG_FILE)

    if isinstance(config, dict):
        return config

    example = read_optional_json(CONFIG_EXAMPLE_FILE)

    if isinstance(example, dict):
        return example

    return {}


def load_workspace() -> Dict[str, Any]:
    workspace = read_optional_json(WORKSPACE_FILE)

    if isinstance(workspace, dict):
        return workspace

    example = read_optional_json(WORKSPACE_EXAMPLE_FILE)

    if isinstance(example, dict):
        return example

    return {}


def load_secrets() -> Dict[str, Any]:
    """Load runtime secrets from the persistent external credential store.

    secrets.local.json under Configuration is treated as a migration source only.
    The active store lives outside the repository so patch application does not
    wipe authenticated sessions.
    """
    secrets = load_persistent_secrets()

    if isinstance(secrets, dict) and secrets:
        return secrets

    example = read_optional_json(SECRETS_EXAMPLE_FILE)

    if isinstance(example, dict):
        return example

    return {}


def get_config_value(path: str, default: Any = None) -> Any:
    config = load_config()
    return get_nested_value(config, path, default)


def get_workspace_value(path: str, default: Any = None) -> Any:
    workspace = load_workspace()
    return get_nested_value(workspace, path, default)


def get_secret_value(path: str, default: Any = None) -> Any:
    secrets = load_secrets()
    return get_nested_value(secrets, path, default)


def get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = data

    for part in path.split("."):
        if not isinstance(current, dict):
            return default

        current = current.get(part)

        if current is None:
            return default

    return current


def reload_configuration() -> None:
    """Compatibility hook for runtime configuration refresh.

    Configuration is loaded from disk on each access in this module, so there is
    currently no in-memory cache to clear. The function exists as a stable API
    for callers that update workspace/secrets and then want to signal a refresh.
    """
    return None
