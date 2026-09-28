"""Canonical normalization for completed historical Fantrax draft results.

The provider payload is authoritative for draft slots and exercised selections.
A configured slot without playerId is preserved as ``no_player_selection`` and
must never be reconstructed into a selection from roster or transaction data.
"""
from __future__ import annotations

from typing import Any


def normalize_historical_draft_results(
    payload: Any, *, season: int, league_id: str, provider: str = "Fantrax"
) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    raw_slots = data.get("draftPicks")
    if not isinstance(raw_slots, list):
        raw_slots = []

    slots: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    for raw in raw_slots:
        if not isinstance(raw, dict):
            continue
        player_id = raw.get("playerId")
        has_selection = player_id not in (None, "")
        slot = {
            "season": int(season),
            "provider": provider,
            "provider_league_id": str(league_id),
            "round": raw.get("round"),
            "pick_in_round": raw.get("pickInRound"),
            "overall_pick": raw.get("pick"),
            "provider_team_id": raw.get("teamId"),
            "provider_player_id": player_id if has_selection else None,
            "selected_at_epoch_ms": raw.get("time"),
            "slot_status": "selection" if has_selection else "no_player_selection",
        }
        slots.append(slot)
        if has_selection:
            selections.append(dict(slot))

    return {
        "schema": "athena.historical_draft_results.v1",
        "season": int(season),
        "provider": provider,
        "provider_league_id": str(league_id),
        "scope": "historical_read_only",
        "active_workspace_mutation_allowed": False,
        "draft_state": data.get("draftState"),
        "draft_type": data.get("draftType"),
        "draft_date": data.get("draftDate"),
        "start_date": data.get("startDate"),
        "end_date": data.get("endDate"),
        "draft_order": list(data.get("draftOrder") or []),
        "configured_slot_count": len(slots),
        "selection_count": len(selections),
        "no_player_selection_count": len(slots) - len(selections),
        "draft_slots": slots,
        "draft_selections": selections,
        "identity_resolution": {
            "team_identity": "unresolved_until_same_season_evidence",
            "player_identity": "unresolved_until_same_season_evidence",
        },
        "provenance": {
            "source": "Fantrax completed Draft Results",
            "selection_rule": "provider_player_id_present",
            "reconstruction_used": False,
        },
    }
