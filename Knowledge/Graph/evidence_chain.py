"""Evidence-chain API over Athena's canonical context graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from Core.json_utils import read_optional_json
from Core.project_paths import OUTPUT_DIR
from Knowledge.Graph.builder import build_canonical_context_graph
from Knowledge.Graph.canonical_graph import CanonicalContextGraph


def load_graph(project_root: Path | None = None) -> CanonicalContextGraph:
    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"
    payload = read_optional_json(output_dir / "canonical_context_graph.json")
    if not isinstance(payload, dict) or not payload.get("nodes"):
        payload = build_canonical_context_graph(project_root)["graph"]
    return CanonicalContextGraph.from_dict(payload)


def evidence_chain_for_entity(entity_id: str, *, max_depth: int = 2, project_root: Path | None = None) -> Dict[str, Any]:
    graph = load_graph(project_root)
    if entity_id not in graph.nodes:
        return {"status": "not_found", "entity_id": entity_id, "evidence": [], "message": "Entity is not present in the canonical context graph."}
    chain = graph.evidence_chain(entity_id, max_depth=max_depth)
    return {"status": "available", **chain}
