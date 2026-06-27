"""
Fantrax provider diagnostics.

Diagnostics stay inside the provider boundary. They validate configuration,
authentication setup, and lightweight endpoint availability without normalizing
or analyzing provider data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from Providers.Fantrax.fantrax_client import FantraxClient
from Providers.Fantrax.endpoints import FantraxEndpoints
from Core.project_paths import CONFIGURATION_DIR


def run_provider_diagnostics() -> Dict[str, Any]:
    client = FantraxClient()

    diagnostics: Dict[str, Any] = {
        "provider": client.provider_name,
        "sport": client.sport,
        "workspace": client.workspace_name,
        "league_id_present": bool(client.league_id),
        "base_url": client.base_url,
        "secrets": {
            "secrets_local_exists": (CONFIGURATION_DIR / "secrets.local.json").exists(),
            "secrets_example_exists": (CONFIGURATION_DIR / "secrets.example.json").exists(),
        },
        "cookie": client.cookie_status(),
        "endpoints": {
            name: FantraxEndpoints.get(name, "")
            for name in FantraxEndpoints.CONFIG_KEYS
        },
        "fxpa": {
            "request_url": FantraxEndpoints.FXPA_REQUEST_URL,
            "transactions_method": FantraxEndpoints.TRANSACTIONS_METHOD,
        },
    }

    try:
        client.validate_config()
        diagnostics["configuration_status"] = "valid"
    except Exception as exc:
        diagnostics["configuration_status"] = "invalid"
        diagnostics["configuration_error"] = str(exc)

    return diagnostics
