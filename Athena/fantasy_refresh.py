"""Bounded, freshness-aware Fantrax acquisition before fantasy inquiries."""
from __future__ import annotations
from datetime import datetime, timezone
from threading import Lock

_REFRESH_LOCK = Lock()
MAX_AGE_SECONDS = 30 * 60


def ensure_fantasy_freshness(*, now=None, sync_fn=None, workspace_fn=None) -> dict:
    from Athena.workspace import load_workspace
    from Athena.sync import sync
    workspace_fn = workspace_fn or load_workspace
    sync_fn = sync_fn or sync
    now = now or datetime.now(timezone.utc)
    workspace = workspace_fn().get("workspace", {})
    if not workspace.get("league_id") or str(workspace.get("provider_key") or "fantrax").lower() != "fantrax":
        return {"attempted": False, "status": "no_active_fantrax_league"}
    stamp = workspace.get("last_sync_at")
    if workspace.get("last_sync_status") == "completed" and stamp:
        try:
            age = (now - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds()
            if 0 <= age < MAX_AGE_SECONDS:
                return {"attempted": False, "status": "fresh", "age_seconds": round(age)}
        except (TypeError, ValueError):
            pass
    if not _REFRESH_LOCK.acquire(blocking=False):
        return {"attempted": False, "status": "sync_already_in_progress"}
    try:
        # Recheck inside the lock to avoid duplicate refreshes.
        current = workspace_fn().get("workspace", {})
        stamp = current.get("last_sync_at")
        if current.get("last_sync_status") == "completed" and stamp:
            try:
                age = (now - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds()
                if 0 <= age < MAX_AGE_SECONDS:
                    return {"attempted": False, "status": "fresh", "age_seconds": round(age)}
            except (TypeError, ValueError):
                pass
        try:
            result = sync_fn(mode="fantasy_league", provider="Fantrax", fetch=True)
            return {"attempted": True, "status": "completed" if result.get("ok") else "failed", "partial": bool(result.get("partial")), "warnings": result.get("warnings", [])[:5] if isinstance(result.get("warnings"), list) else []}
        except Exception as exc:
            return {"attempted": True, "status": "failed", "error_type": type(exc).__name__, "fallback": "last_verified_snapshot_if_available"}
    finally:
        _REFRESH_LOCK.release()
