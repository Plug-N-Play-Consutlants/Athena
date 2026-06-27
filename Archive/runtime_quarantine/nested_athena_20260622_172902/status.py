"""
Athena status helpers.

Status is intentionally read-only. It provides lightweight observability for
Scout Engine Insights and future API consumers without requiring them to inspect
individual JSON files directly.
"""

from __future__ import annotations

from typing import Any, Dict

from Core.json_utils import read_optional_json
from Core.project_paths import OUTPUT_DIR, RAW_DIR

from Athena.workspace import load_workspace, secrets_status, repair_workspace_file
from Athena.capabilities import assess_capabilities, capability_dashboard
from Providers.base.registry import get_provider, registered_providers

from Core.version import ATHENA_VERSION


def _count_records(payload: Any) -> int:
    if isinstance(payload, dict):
        if isinstance(payload.get("records"), list):
            return len(payload["records"])
        if isinstance(payload.get("transactions"), list):
            return len(payload["transactions"])
        if isinstance(payload.get("team_transaction_history"), list):
            return len(payload["team_transaction_history"])
        if isinstance(payload.get("record_count"), int):
            return payload["record_count"]
        if isinstance(payload.get("asset_movements"), list):
            return len(payload["asset_movements"])
    if isinstance(payload, list):
        return len(payload)
    return 0


def _active_provider_status(workspace: Dict[str, Any]) -> Dict[str, Any]:
    provider_key = str(
        workspace.get("provider_key")
        or workspace.get("provider")
        or ""
    ).strip().lower()
    if provider_key == "fantrax":
        provider_key = "fantrax"
    if not provider_key:
        return {"available": False, "message": "No active provider in workspace."}
    try:
        provider = get_provider(provider_key)
        return {
            "available": True,
            "provider_key": provider_key,
            "status": provider.status().to_dict(),
        }
    except Exception as exc:  # read-only status must never crash Scout
        return {
            "available": False,
            "provider_key": provider_key,
            "message": str(exc),
        }


def get_status() -> Dict[str, Any]:
    """Return Athena's current read-only status snapshot."""
    raw_files = {
        "league_info": RAW_DIR / "league_info.json",
        "fantrax_player_pool": RAW_DIR / "fantrax_player_pool.json",
        "transactions": RAW_DIR / "transactions.json",
    }
    output_files = {
        "player_master": OUTPUT_DIR / "player_master.json",
        "transaction_master": OUTPUT_DIR / "transaction_master.json",
        "transaction_history": OUTPUT_DIR / "transaction_history.json",
        "manager_behavior": OUTPUT_DIR / "manager_behavior.json",
        "league_market": OUTPUT_DIR / "league_market.json",
        "knowledge_readiness": OUTPUT_DIR / "knowledge_readiness.json",
    }

    outputs: Dict[str, Any] = {}
    for name, path in output_files.items():
        payload = read_optional_json(path)
        outputs[name] = {
            "exists": path.exists(),
            "record_count": _count_records(payload),
        }

    raw = {name: {"exists": path.exists()} for name, path in raw_files.items()}

    readiness_payload = read_optional_json(OUTPUT_DIR / "knowledge_readiness.json")
    readiness_score = None
    if isinstance(readiness_payload, dict):
        readiness_score = readiness_payload.get("readiness_score") or readiness_payload.get("score")

    workspace = repair_workspace_file().get("workspace", {})

    capability_report = assess_capabilities(str(workspace.get("provider") or "Fantrax"))

    return {
        "athena_version": ATHENA_VERSION,
        "workspace": workspace,
        "registered_providers": registered_providers(),
        "active_provider": _active_provider_status(workspace),
        "secrets": secrets_status(),
        "raw_files": raw,
        "outputs": outputs,
        "readiness_score": readiness_score,
        "capabilities": capability_report,
        "capability_dashboard": capability_dashboard(capability_report),
    }
