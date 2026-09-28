"""Discover normalized historical league evidence without exposing storage details to Scout."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def discover_historical_evidence(domain: str, *, project_root: Path | None = None) -> dict[str, Any]:
    """Return available season evidence for a registered historical domain.

    Discovery is intentionally filesystem-backed at this boundary so callers ask
    for a domain rather than knowing provider paths or season filenames.
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    domain_key = (domain or "").strip().lower()
    if domain_key not in {"draft", "draft_results"}:
        return {"domain": domain_key, "status": "unsupported", "seasons": [], "coverage": 0}

    historical_root = root / "Output" / "Historical"
    records: list[dict[str, Any]] = []
    if historical_root.exists():
        for season_dir in historical_root.iterdir():
            if not season_dir.is_dir() or not season_dir.name.isdigit():
                continue
            path = season_dir / "draft_results_canonical.json"
            payload = _read_json(path)
            if not payload:
                continue
            identity_path = season_dir / "historical_identity_resolution.json"
            enriched_path = season_dir / "draft_observations_enriched.json"
            identity = _read_json(identity_path) or {}
            enriched = _read_json(enriched_path) or {}
            coverage = identity.get("coverage") or {}
            observations = enriched.get("observations") or []
            resolved_player_names = sum(1 for row in observations if (row.get("historical_player_identity") or {}).get("player_identity_status") == "resolved")
            resolved_positions = sum(1 for row in observations if (row.get("historical_player_identity") or {}).get("position_resolution_status") == "resolved")
            resolved_team_names = sum(1 for row in observations if (row.get("historical_team_identity") or {}).get("team_identity_status") == "resolved")
            records.append({
                "season": int(payload.get("season") or season_dir.name),
                "provider": payload.get("provider"),
                "provider_league_id": payload.get("provider_league_id"),
                "provider_draft_state": payload.get("draft_state"),
                "draft_type": payload.get("draft_type"),
                "configured_slots": int(payload.get("configured_slot_count") or 0),
                "selections": int(payload.get("selection_count") or 0),
                "no_player_selection": int(payload.get("no_player_selection_count") or 0),
                "identity_available": bool(identity),
                "enriched_observations_available": bool(enriched),
                "resolved_team_names": resolved_team_names,
                "resolved_player_names": resolved_player_names,
                "resolved_positions": resolved_positions,
                "manager_identities_resolved": int(coverage.get("manager_identities_resolved") or 0),
                "artifact": str(path.relative_to(root)).replace("\\", "/"),
                "identity_artifact": str(identity_path.relative_to(root)).replace("\\", "/") if identity else None,
                "enriched_artifact": str(enriched_path.relative_to(root)).replace("\\", "/") if enriched else None,
            })
    records.sort(key=lambda item: item["season"])
    return {
        "schema": "athena.historical_evidence_registry.v1",
        "domain": "draft_results",
        "status": "available" if records else "missing",
        "coverage": len(records),
        "first_season": records[0]["season"] if records else None,
        "last_season": records[-1]["season"] if records else None,
        "seasons": records,
    }
