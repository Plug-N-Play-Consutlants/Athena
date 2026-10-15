"""Evidence-preserving Fantrax trading-block snapshot comparison.

Only explicitly validated complete acquisitions may enter history.  This module
never infers private negotiations or reconstructs intermediate changes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identity(record: dict[str, Any]) -> str:
    value = record.get("team_id")
    if value is None or str(value).strip() == "":
        raise ValueError("Trading-block team_id is required; display names are insufficient")
    return str(value)


def validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Validate a complete, authenticated provider observation, without guessing schema."""
    if snapshot.get("status") != "complete" or snapshot.get("authenticated") is not True:
        raise ValueError("Incomplete or unauthenticated trading-block observations cannot be snapshotted")
    if not snapshot.get("league_id") or not snapshot.get("season"):
        raise ValueError("Trading-block observation requires league and season identity")
    records = snapshot.get("teams")
    if not isinstance(records, list):
        raise ValueError("Trading-block teams must be an explicit complete list")
    keys = [_identity(record) for record in records if isinstance(record, dict)]
    if len(keys) != len(records) or len(keys) != len(set(keys)):
        raise ValueError("Invalid or duplicate trading-block team identities")
    return snapshot


def compare_snapshots(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare observed state; never attribute a precise change time or motive."""
    validate_snapshot(previous)
    validate_snapshot(current)
    if (str(previous["league_id"]), str(previous["season"])) != (str(current["league_id"]), str(current["season"])):
        raise ValueError("Cannot compare different leagues or seasons")
    before = {_identity(r): r for r in previous["teams"]}
    after = {_identity(r): r for r in current["teams"]}
    changes = []
    for team_id in sorted(before.keys() | after.keys()):
        old, new = before.get(team_id), after.get(team_id)
        if old is not None and new is not None and _canonical(old.get("block")) == _canonical(new.get("block")):
            continue
        changes.append({
            "team_id": team_id,
            "kind": "new_observation" if old is None else "no_longer_observed" if new is None else "block_changed",
            "previous": None if old is None else old.get("block"),
            "current": None if new is None else new.get("block"),
            "first_observed_at": current.get("observed_at"),
            "time_precision": "between_observations",
        })
    return changes


def store_snapshot(snapshot: dict[str, Any], directory: str | Path) -> Path:
    """Append an immutable, content-addressed observation; never overwrite history."""
    validate_snapshot(snapshot)
    stamp = snapshot.get("observed_at")
    if not isinstance(stamp, str) or not stamp:
        raise ValueError("Explicit observed_at timestamp required")
    datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    body = _canonical(snapshot).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    root = Path(directory) / str(snapshot["league_id"]) / str(snapshot["season"])
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{digest}.json"
    if not path.exists():
        with path.open("xb") as handle:
            handle.write(body)
    return path
