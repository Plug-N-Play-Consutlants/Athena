"""Evidence inventory for league recaps; presence is never proof of period coverage.

This module is read-only. Acquisition belongs to provider/Fetch/Build and must
not be simulated by the reporting layer.
"""
from __future__ import annotations
import json
from pathlib import Path


def _load(path):
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError, TypeError):
        return None


def _candidates(root, names):
    found = []
    if root.exists():
        for name in names:
            found.extend(root.glob(f"**/{name}"))
    return sorted(set(found))[:5]


def _inventory(root, names, period, kind):
    candidates = _candidates(root, names)
    if not candidates:
        return {"status": "not_available_in_output", "reason":
                "No recognized canonical artifact found; provider acquisition not verified",
                "candidate_paths": [], "period": period}
    descriptions = []
    for path in candidates:
        payload = _load(path)
        records = payload if isinstance(payload, list) else payload.get("records", []) if isinstance(payload, dict) else []
        if not isinstance(records, list):
            records = []
        seasons = sorted({str(r.get("season")) for r in records if isinstance(r, dict) and r.get("season") is not None})
        metadata = payload if isinstance(payload, dict) else {}
        description = {"path": str(path.relative_to(root)), "record_count": len(records),
                       "seasons": seasons[:12], "fetched_at": metadata.get("fetched_at"),
                       "active_season": metadata.get("active_season")}
        descriptions.append(description)
    if kind == "player_production":
        reason = "Production artifacts exist, but season totals cannot establish scoring-period production without period attribution and current-season validation"
    elif kind == "roster":
        reason = "Roster artifacts exist, but snapshot freshness and scoring-period lineup/keeper reconciliation are unverified"
    else:
        reason = "Draft artifacts exist; season, team ownership and pick rights must be reconciled"
    return {"status": "candidate_present_unverified", "reason": reason,
            "candidate_paths": [d["path"] for d in descriptions],
            "candidate_metadata": descriptions, "period": period}


def audit_recap_evidence(output, period):
    root = Path(output)
    result = {
        "player_production": _inventory(root, ("player_production.json", "player_stats.json"), period, "player_production"),
        "roster": _inventory(root, ("player_pool_master.json", "player_pool.json"), period, "roster"),
        "draft_assets": _inventory(root, ("draft_picks.json",), period, "draft_assets"),
        "injuries": {"status": "unresolved", "reason": "Injury source and scoring-period timing not reconciled", "period": period},
        "trading_block": {"status": "unresolved", "reason": "Authenticated current trading-block acquisition not verified", "period": period},
    }
    return result
