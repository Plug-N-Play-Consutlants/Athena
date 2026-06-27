"""Build Athena's canonical context graph from Knowledge outputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import OUTPUT_DIR
from Core.version import ATHENA_VERSION
from Knowledge.Graph.canonical_graph import CanonicalContextGraph, GraphNode, GraphRelationship, utc_now_iso

GRAPH_FILE = OUTPUT_DIR / "canonical_context_graph.json"
GRAPH_REPORT = OUTPUT_DIR / "canonical_context_graph_summary.json"


def _slug(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def _records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("records", "players", "teams", "packs", "sources"):
            val = payload.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
    return []


def _relationship_id(source_id: str, rel_type: str, target_id: str) -> str:
    return f"rel:{_slug(source_id)}:{_slug(rel_type)}:{_slug(target_id)}"


def _add_rel(graph: CanonicalContextGraph, source_id: str, rel_type: str, target_id: str, *, source: str, confidence: float = 0.75, **props: Any) -> None:
    if source_id in graph.nodes and target_id in graph.nodes:
        graph.add_relationship(GraphRelationship(
            id=_relationship_id(source_id, rel_type, target_id),
            source_id=source_id,
            target_id=target_id,
            type=rel_type,
            source=source,
            confidence=confidence,
            properties={k: v for k, v in props.items() if v not in (None, "", [], {})},
        ))


def build_canonical_context_graph(project_root: Path | None = None) -> Dict[str, Any]:
    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"
    graph = CanonicalContextGraph(metadata={
        "athena_version": ATHENA_VERSION,
        "graph_version": "4C.1-foundation",
        "principle": "connected_evidence_not_raw_files",
        "generated_at": utc_now_iso(),
    })

    league = read_optional_json(output_dir / "league_profile.json")
    league_id = "league:active"
    if isinstance(league, dict):
        league_id = f"league:{_slug(league.get('league_id') or league.get('league_name') or 'active')}"
        graph.add_node(GraphNode(league_id, "league", str(league.get("league_name") or league.get("league_id") or "Active League"), "knowledge", "league_profile", 0.82, league))

    for team in _records(read_optional_json(output_dir / "team_profiles.json")):
        team_id = f"team:{_slug(team.get('team_id') or team.get('team_name'))}"
        graph.add_node(GraphNode(team_id, "team", str(team.get("team_name") or team.get("team_id")), "knowledge", "team_profiles", float(team.get("confidence") or 0.75), team))
        _add_rel(graph, team_id, "member_of", league_id, source="team_profiles", confidence=float(team.get("confidence") or 0.75))

    player_rows = _records(read_optional_json(output_dir / "player_master.json"))
    for player in player_rows:
        pid = f"player:{_slug(player.get('player_id') or player.get('fantrax_player_id') or player.get('player_name'))}"
        graph.add_node(GraphNode(pid, "player", str(player.get("player_name") or player.get("name") or pid), "canonical", "player_master", 0.78, player))
        owner = player.get("owner_team") or player.get("fantasy_team")
        if owner:
            team_candidates = [tid for tid, node in graph.nodes.items() if node.type == "team" and _slug(node.label) == _slug(owner)]
            if team_candidates:
                _add_rel(graph, pid, "rostered_by", team_candidates[0], source="player_master", confidence=0.78, roster_status=player.get("roster_status"))
        if player.get("nhl_team"):
            nhl_team_id = f"nhl_team:{_slug(player.get('nhl_team'))}"
            graph.add_node(GraphNode(nhl_team_id, "team", str(player.get("nhl_team")), "canonical", "player_master", 0.68, {"abbreviation": player.get("nhl_team"), "team_scope": "public_hockey"}))
            _add_rel(graph, pid, "plays_for", nhl_team_id, source="player_master", confidence=0.68)

    for contract in _records(read_optional_json(output_dir / "player_contracts.json")):
        player_key = contract.get("fantrax_player_id") or contract.get("player_id") or contract.get("player_name")
        pid = f"player:{_slug(player_key)}"
        if pid not in graph.nodes:
            # fall back to name match for contract records using display names
            matches = [nid for nid, node in graph.nodes.items() if node.type == "player" and _slug(node.label) == _slug(contract.get("player_name"))]
            pid = matches[0] if matches else pid
        if pid in graph.nodes:
            cid = f"contract:{_slug(player_key)}:{_slug(contract.get('expiry_year') or contract.get('contract_expiry_year'))}"
            graph.add_node(GraphNode(cid, "contract", f"{contract.get('player_name') or player_key} contract", "knowledge", "player_contracts", float(contract.get("confidence") or 0.85), contract))
            _add_rel(graph, pid, "has_contract", cid, source="player_contracts", confidence=float(contract.get("confidence") or 0.85))

    packs = read_optional_json(output_dir / "public_hockey_knowledge_packs.json")
    for pack in _records(packs):
        source_id = str(pack.get("source_id") or pack.get("pack_root") or "knowledge_pack")
        kid = f"knowledge_pack:{_slug(source_id)}"
        graph.add_node(GraphNode(kid, "knowledge_pack", source_id, "document_backed_pack", "public_hockey_knowledge_packs", 0.9 if pack.get("source_document_present") else 0.65, pack))
        if league_id in graph.nodes:
            _add_rel(graph, league_id, "uses_rules_from", kid, source="public_hockey_knowledge_packs", confidence=0.7)

    payload = graph.to_dict()
    write_json(output_dir / "canonical_context_graph.json", payload)
    summary = {
        "athena_version": ATHENA_VERSION,
        "status": "ready" if payload["node_count"] > 0 else "empty",
        "node_count": payload["node_count"],
        "relationship_count": payload["relationship_count"],
        "node_types": {},
        "relationship_types": {},
        "graph_file": str(output_dir / "canonical_context_graph.json"),
    }
    for node in payload["nodes"]:
        summary["node_types"][node["type"]] = summary["node_types"].get(node["type"], 0) + 1
    for rel in payload["relationships"]:
        summary["relationship_types"][rel["type"]] = summary["relationship_types"].get(rel["type"], 0) + 1
    write_json(output_dir / "canonical_context_graph_summary.json", summary)
    return {"graph": payload, "summary": summary}


if __name__ == "__main__":
    result = build_canonical_context_graph()
    print("Canonical Context Graph Foundation")
    print("==================================")
    print(f"Status: {result['summary']['status']}")
    print(f"Nodes: {result['summary']['node_count']}")
    print(f"Relationships: {result['summary']['relationship_count']}")
