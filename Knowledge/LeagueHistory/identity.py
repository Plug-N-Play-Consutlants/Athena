"""Season-scoped historical identity resolution from already-acquired evidence.

This layer enriches canonical historical evidence without mutating it. Provider IDs
remain the join keys; missing or conflicting evidence is reported, never guessed.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def _walk(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _state(values: set[str]) -> str:
    return "resolved" if len(values) == 1 else ("ambiguous" if len(values) > 1 else "unresolved")


def build_historical_identity_resolution(*, season: int, league_id: str, raw_payloads: dict[str, Any], provider: str = "Fantrax") -> dict[str, Any]:
    league_info = raw_payloads.get("league_info") if isinstance(raw_payloads.get("league_info"), dict) else {}
    player_pool = raw_payloads.get("player_pool") if isinstance(raw_payloads.get("player_pool"), dict) else {}
    transactions = raw_payloads.get("transactions") if isinstance(raw_payloads.get("transactions"), dict) else {}

    teams: dict[str, dict[str, Any]] = {}
    for provider_team_id, row in (league_info.get("teamInfo") or {}).items():
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        teams[str(provider_team_id)] = {
            "season": int(season), "provider": provider, "provider_team_id": str(provider_team_id),
            "team_name": name or None,
            "team_identity_status": "resolved" if name else "unresolved",
            "franchise_identity_status": "unresolved",
            "manager_identity_status": "unresolved",
            "canonical_franchise_id": None, "canonical_manager_id": None,
            "evidence": [{"source": "league_info.teamInfo", "field": "name"}] if name else [],
        }

    player_names: dict[str, set[str]] = defaultdict(set)
    player_positions: dict[str, set[str]] = defaultdict(set)
    player_context: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in _walk(transactions):
        pid = row.get("scorerId") if isinstance(row, dict) else None
        if pid in (None, ""):
            continue
        pid = str(pid)
        name = str(row.get("name") or "").strip()
        if name:
            player_names[pid].add(name)
        for pos in str(row.get("posShortNames") or "").split(","):
            if pos.strip(): player_positions[pid].add(pos.strip())
        ctx = {k: row.get(k) for k in ("teamShortName", "teamName", "urlName") if row.get(k) not in (None, "")}
        if ctx and ctx not in player_context[pid]: player_context[pid].append(ctx)

    for provider_team_id, roster in (player_pool.get("rosters") or {}).items():
        if not isinstance(roster, dict):
            continue
        roster_team_name = str(roster.get("teamName") or "").strip()
        for item in roster.get("rosterItems") or []:
            if not isinstance(item, dict) or item.get("id") in (None, ""):
                continue
            pid = str(item["id"])
            pos = str(item.get("position") or "").strip()
            if pos: player_positions[pid].add(pos)
            ctx = {"provider_team_id": str(provider_team_id), "roster_team_name": roster_team_name or None, "roster_status": item.get("status")}
            if ctx not in player_context[pid]: player_context[pid].append(ctx)

    all_player_ids = sorted(set(player_names) | set(player_positions) | set(player_context))
    players = []
    for pid in all_player_ids:
        names, positions = player_names[pid], player_positions[pid]
        players.append({
            "season": int(season), "provider": provider, "provider_player_id": pid,
            "canonical_player_name": next(iter(names)) if len(names) == 1 else None,
            "player_identity_status": _state(names),
            "positions": sorted(positions),
            "position_resolution_status": "resolved" if positions else "unresolved",
            "same_season_context": player_context[pid],
            "evidence": ([{"source": "transactions.table.rows.scorer", "fields": ["scorerId", "name", "posShortNames"]}] if names else []) + ([{"source": "player_pool.rosters.rosterItems", "fields": ["id", "position", "status"]}] if positions else []),
        })

    return {
        "schema": "athena.historical_identity_resolution.v1", "season": int(season), "provider": provider,
        "provider_league_id": str(league_id), "scope": "historical_read_only", "active_workspace_mutation_allowed": False,
        "teams": sorted(teams.values(), key=lambda x: x["provider_team_id"]), "players": players,
        "coverage": {
            "team_provider_ids": len(teams),
            "team_names_resolved": sum(x["team_identity_status"] == "resolved" for x in teams.values()),
            "manager_identities_resolved": 0, "franchise_continuities_resolved": 0,
            "player_provider_ids": len(players),
            "player_names_resolved": sum(x["player_identity_status"] == "resolved" for x in players),
            "player_positions_resolved": sum(x["position_resolution_status"] == "resolved" for x in players),
        },
        "limitations": [
            "Provider team slot, fantasy team, franchise, team name, and manager/person are distinct identities.",
            "No inspected same-season source establishes manager/person identity; manager identity remains unresolved.",
            "Team-name continuity alone is insufficient to establish cross-season franchise continuity.",
        ],
    }


def enrich_historical_draft_observations(canonical_draft: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    teams = {x["provider_team_id"]: x for x in identity.get("teams", [])}
    players = {x["provider_player_id"]: x for x in identity.get("players", [])}
    observations = []
    for selection in canonical_draft.get("draft_selections") or []:
        row = dict(selection)
        team = teams.get(str(row.get("provider_team_id") or ""))
        player = players.get(str(row.get("provider_player_id") or ""))
        row["historical_team_identity"] = team or {"team_identity_status": "unresolved", "provider_team_id": row.get("provider_team_id")}
        row["historical_player_identity"] = player or {"player_identity_status": "unresolved", "position_resolution_status": "unresolved", "provider_player_id": row.get("provider_player_id"), "positions": []}
        observations.append(row)
    return {
        "schema": "athena.historical_draft_observations.v1", "season": canonical_draft.get("season"),
        "provider": canonical_draft.get("provider"), "provider_league_id": canonical_draft.get("provider_league_id"),
        "scope": "historical_read_only", "active_workspace_mutation_allowed": False,
        "canonical_source": "draft_results_canonical.json", "identity_source": "historical_identity_resolution.json",
        "selection_count": len(observations), "observations": observations,
        "provenance": {"canonical_draft_mutated": False, "draft_selection_authority": "draft_results.provider_team_id + provider_player_id"},
    }
