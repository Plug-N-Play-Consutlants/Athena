"""Epic 4C.2 evidence-chain engine for Athena's context graph.

The chain engine turns graph traversal into an explainable, scored evidence
chain. It does not create subjective conclusions; it exposes the connected
facts, relationship path, confidence propagation, and developer-facing evidence
trace that Scout and Intelligence can consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from Core.json_utils import write_json
from Core.project_paths import OUTPUT_DIR
from Core.version import ATHENA_VERSION
from Knowledge.Graph.canonical_graph import CanonicalContextGraph, utc_now_iso
from Knowledge.Graph.evidence_chain import load_graph

DEFAULT_RELATIONSHIP_WEIGHTS: Dict[str, float] = {
    "has_contract": 0.92,
    "plays_for": 0.86,
    "rostered_by": 0.86,
    "member_of": 0.74,
    "uses_rules_from": 0.64,
}

DEFAULT_NODE_TYPE_WEIGHTS: Dict[str, float] = {
    "player": 1.0,
    "contract": 0.9,
    "team": 0.82,
    "league": 0.78,
    "knowledge_pack": 0.72,
}


@dataclass(frozen=True)
class ChainStep:
    index: int
    relationship_id: str
    relationship_type: str
    from_node_id: str
    from_label: str
    from_type: str
    to_node_id: str
    to_label: str
    to_type: str
    relationship_confidence: float
    relationship_weight: float
    target_confidence: float
    node_weight: float
    step_confidence: float
    direction: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "relationship_id": self.relationship_id,
            "relationship_type": self.relationship_type,
            "from": {"id": self.from_node_id, "label": self.from_label, "type": self.from_type},
            "to": {"id": self.to_node_id, "label": self.to_label, "type": self.to_type},
            "relationship_confidence": round(self.relationship_confidence, 4),
            "relationship_weight": round(self.relationship_weight, 4),
            "target_confidence": round(self.target_confidence, 4),
            "node_weight": round(self.node_weight, 4),
            "step_confidence": round(self.step_confidence, 4),
            "direction": self.direction,
        }


def _clamp(value: Any, default: float = 0.75) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0.0, min(1.0, numeric))


def _node_brief(graph: CanonicalContextGraph, node_id: str) -> Dict[str, Any]:
    node = graph.nodes.get(node_id)
    if not node:
        return {"id": node_id, "status": "missing"}
    return {
        "id": node.id,
        "type": node.type,
        "label": node.label,
        "evidence_type": node.evidence_type,
        "source": node.source,
        "confidence": round(_clamp(node.confidence), 4),
        "properties": node.properties,
    }


def _step_from_edge(
    graph: CanonicalContextGraph,
    edge: Dict[str, Any],
    index: int,
    current_node_id: str,
    relationship_weights: Dict[str, float],
    node_type_weights: Dict[str, float],
) -> Optional[ChainStep]:
    rel = graph.relationships.get(str(edge.get("relationship_id") or ""))
    if not rel:
        return None
    from_node = graph.nodes.get(rel.source_id)
    to_node = graph.nodes.get(rel.target_id)
    if not from_node or not to_node:
        return None
    if current_node_id == rel.target_id:
        target_node = from_node
        direction = "incoming"
    else:
        target_node = to_node
        direction = "outgoing"
    rel_weight = _clamp(relationship_weights.get(rel.type, 0.7), 0.7)
    node_weight = _clamp(node_type_weights.get(target_node.type, 0.7), 0.7)
    rel_conf = _clamp(rel.confidence)
    target_conf = _clamp(target_node.confidence)
    step_conf = rel_conf * rel_weight * target_conf * node_weight
    return ChainStep(
        index=index,
        relationship_id=rel.id,
        relationship_type=rel.type,
        from_node_id=rel.source_id,
        from_label=from_node.label,
        from_type=from_node.type,
        to_node_id=rel.target_id,
        to_label=to_node.label,
        to_type=to_node.type,
        relationship_confidence=rel_conf,
        relationship_weight=rel_weight,
        target_confidence=target_conf,
        node_weight=node_weight,
        step_confidence=step_conf,
        direction=direction,
    )


def _path_steps(
    graph: CanonicalContextGraph,
    path: List[Dict[str, Any]],
    start_id: str,
    relationship_weights: Dict[str, float],
    node_type_weights: Dict[str, float],
) -> List[ChainStep]:
    steps: List[ChainStep] = []
    current = start_id
    for idx, edge in enumerate(path, start=1):
        step = _step_from_edge(graph, edge, idx, current, relationship_weights, node_type_weights)
        if not step:
            continue
        steps.append(step)
        rel = graph.relationships.get(step.relationship_id)
        if rel:
            current = rel.target_id if current == rel.source_id else rel.source_id
    return steps


def _path_confidence(steps: List[ChainStep]) -> float:
    if not steps:
        return 0.0
    product = 1.0
    for step in steps:
        product *= max(0.01, step.step_confidence)
    # Geometric mean preserves path confidence without punishing longer paths too harshly.
    return product ** (1 / len(steps))


def _relation_phrase(step: ChainStep) -> str:
    labels = {
        "has_contract": "has contract evidence",
        "plays_for": "plays for",
        "rostered_by": "is rostered by",
        "member_of": "is a member of",
        "uses_rules_from": "uses rules from",
    }
    return labels.get(step.relationship_type, step.relationship_type.replace("_", " "))


def _summary_for_path(path_record: Dict[str, Any]) -> str:
    steps = path_record.get("steps", [])
    if not steps:
        return "No connected evidence steps were found."
    first = steps[0]
    last = steps[-1]
    return f"{first['from']['label']} {_relation_phrase_obj(first)} {last['to']['label']}."


def _relation_phrase_obj(step: Dict[str, Any]) -> str:
    labels = {
        "has_contract": "has contract evidence connected to",
        "plays_for": "plays for",
        "rostered_by": "is rostered by",
        "member_of": "is connected through membership to",
        "uses_rules_from": "uses rules from",
    }
    return labels.get(str(step.get("relationship_type") or ""), str(step.get("relationship_type") or "relationship"))


def build_evidence_chain(
    entity_id: str,
    *,
    max_depth: int = 2,
    relationship_types: Optional[Iterable[str]] = None,
    project_root: Path | None = None,
    relationship_weights: Optional[Dict[str, float]] = None,
    node_type_weights: Optional[Dict[str, float]] = None,
    limit: int = 12,
) -> Dict[str, Any]:
    """Build a scored, explainable evidence chain for a graph entity."""
    graph = load_graph(project_root)
    if entity_id not in graph.nodes:
        return {
            "status": "not_found",
            "athena_version": ATHENA_VERSION,
            "entity_id": entity_id,
            "message": "Entity is not present in the canonical context graph.",
            "evidence_chain": [],
            "confidence": 0.0,
            "known_limitations": ["No graph node exists for the requested entity."],
        }

    rel_weights = {**DEFAULT_RELATIONSHIP_WEIGHTS, **(relationship_weights or {})}
    node_weights = {**DEFAULT_NODE_TYPE_WEIGHTS, **(node_type_weights or {})}
    walked = graph.walk(entity_id, max_depth=max_depth, relationship_types=relationship_types)
    scored_paths: List[Dict[str, Any]] = []

    for path_item in walked.get("paths", []):
        steps = _path_steps(graph, path_item.get("path", []), entity_id, rel_weights, node_weights)
        if not steps:
            continue
        confidence = _path_confidence(steps)
        scored_paths.append({
            "depth": path_item.get("depth"),
            "end_node": _node_brief(graph, str(path_item.get("end_node") or "")),
            "confidence": round(confidence, 4),
            "score": round(confidence * (1 / max(1, int(path_item.get("depth") or 1))), 4),
            "steps": [s.to_dict() for s in steps],
        })

    scored_paths.sort(key=lambda p: (p.get("score", 0), p.get("confidence", 0)), reverse=True)
    selected = scored_paths[: max(1, int(limit or 12))]
    confidence = round(sum(float(p.get("confidence") or 0) for p in selected) / len(selected), 4) if selected else _clamp(graph.nodes[entity_id].confidence)
    evidence_chain = []
    seen_nodes = set()
    for p in selected:
        for step in p.get("steps", []):
            for side in ("from", "to"):
                node_id = step.get(side, {}).get("id")
                if node_id and node_id not in seen_nodes:
                    seen_nodes.add(node_id)
                    evidence_chain.append(_node_brief(graph, node_id))

    known_limitations = []
    if not selected:
        known_limitations.append("The entity exists but has no traversable relationships within the requested depth.")
    if max_depth < 3:
        known_limitations.append("Traversal depth is intentionally shallow; wider context may exist beyond the requested depth.")

    payload = {
        "status": "available",
        "athena_version": ATHENA_VERSION,
        "chain_version": "4C.2-evidence-chain-engine",
        "generated_at": utc_now_iso(),
        "entity": _node_brief(graph, entity_id),
        "max_depth": max_depth,
        "relationship_types": list(relationship_types or []),
        "confidence": confidence,
        "evidence_chain": evidence_chain,
        "paths": selected,
        "conclusion": "Connected evidence chain generated. Intelligence consumers may use this chain to explain why a conclusion is supported.",
        "known_limitations": known_limitations,
        "developer": {
            "graph_metadata": graph.metadata,
            "visited_node_count": len(walked.get("nodes", [])),
            "visited_relationship_count": len(walked.get("relationships", [])),
            "available_path_count": len(scored_paths),
            "relationship_weights": rel_weights,
            "node_type_weights": node_weights,
        },
    }
    return payload


def write_evidence_chain_report(
    entity_id: str,
    *,
    max_depth: int = 2,
    project_root: Path | None = None,
) -> Dict[str, Any]:
    root_output = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"
    report = build_evidence_chain(entity_id, max_depth=max_depth, project_root=project_root)
    safe_id = entity_id.replace(":", "_").replace("/", "_")
    write_json(root_output / f"evidence_chain_{safe_id}.json", report)
    return report
