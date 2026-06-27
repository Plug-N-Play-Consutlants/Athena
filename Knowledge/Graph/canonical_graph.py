"""Canonical context graph primitives for Athena.

The graph stores connected evidence, not provider objects. Providers/builders can
populate it, but downstream intelligence should traverse graph nodes and
relationships instead of reaching back into raw files.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GraphNode:
    id: str
    type: str
    label: str
    evidence_type: str = "canonical"
    source: str = "athena"
    confidence: float = 0.75
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphRelationship:
    id: str
    source_id: str
    target_id: str
    type: str
    source: str = "athena"
    confidence: float = 0.75
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CanonicalContextGraph:
    """In-memory canonical graph with deterministic traversal."""

    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        self.metadata = metadata or {}
        self.nodes: Dict[str, GraphNode] = {}
        self.relationships: Dict[str, GraphRelationship] = {}
        self.outgoing: Dict[str, List[str]] = {}
        self.incoming: Dict[str, List[str]] = {}

    def add_node(self, node: GraphNode) -> GraphNode:
        if node.id in self.nodes:
            existing = self.nodes[node.id]
            existing.properties.update({k: v for k, v in node.properties.items() if v not in (None, "", [], {})})
            existing.confidence = max(existing.confidence, node.confidence)
            return existing
        self.nodes[node.id] = node
        self.outgoing.setdefault(node.id, [])
        self.incoming.setdefault(node.id, [])
        return node

    def add_relationship(self, relationship: GraphRelationship) -> GraphRelationship:
        if relationship.source_id not in self.nodes or relationship.target_id not in self.nodes:
            raise ValueError(f"Relationship references unknown node: {relationship.source_id} -> {relationship.target_id}")
        if relationship.id in self.relationships:
            return self.relationships[relationship.id]
        self.relationships[relationship.id] = relationship
        self.outgoing.setdefault(relationship.source_id, []).append(relationship.id)
        self.incoming.setdefault(relationship.target_id, []).append(relationship.id)
        return relationship

    def neighbors(self, node_id: str, *, direction: str = "both") -> List[Dict[str, Any]]:
        rel_ids: List[str] = []
        if direction in {"out", "both"}:
            rel_ids.extend(self.outgoing.get(node_id, []))
        if direction in {"in", "both"}:
            rel_ids.extend(self.incoming.get(node_id, []))
        seen = set()
        items = []
        for rel_id in rel_ids:
            if rel_id in seen:
                continue
            seen.add(rel_id)
            rel = self.relationships[rel_id]
            other_id = rel.target_id if rel.source_id == node_id else rel.source_id
            items.append({"relationship": rel.to_dict(), "node": self.nodes[other_id].to_dict()})
        return items

    def walk(self, start_id: str, *, max_depth: int = 2, relationship_types: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        allowed = set(relationship_types or [])
        visited_nodes = {start_id}
        visited_relationships = set()
        paths: List[Dict[str, Any]] = []
        q = deque([(start_id, 0, [])])
        while q:
            current, depth, path = q.popleft()
            if depth >= max_depth:
                continue
            for rel_id in self.outgoing.get(current, []) + self.incoming.get(current, []):
                rel = self.relationships[rel_id]
                if allowed and rel.type not in allowed:
                    continue
                other = rel.target_id if rel.source_id == current else rel.source_id
                edge = {"relationship_id": rel.id, "relationship_type": rel.type, "from": rel.source_id, "to": rel.target_id}
                new_path = [*path, edge]
                visited_relationships.add(rel_id)
                paths.append({"depth": depth + 1, "end_node": other, "path": new_path})
                if other not in visited_nodes:
                    visited_nodes.add(other)
                    q.append((other, depth + 1, new_path))
        return {
            "start_id": start_id,
            "max_depth": max_depth,
            "nodes": [self.nodes[n].to_dict() for n in sorted(visited_nodes) if n in self.nodes],
            "relationships": [self.relationships[r].to_dict() for r in sorted(visited_relationships)],
            "paths": paths,
        }

    def evidence_chain(self, node_id: str, *, max_depth: int = 2) -> Dict[str, Any]:
        walked = self.walk(node_id, max_depth=max_depth)
        evidence = []
        for node in walked["nodes"]:
            evidence.append({
                "node_id": node["id"],
                "type": node["type"],
                "label": node["label"],
                "source": node.get("source"),
                "confidence": node.get("confidence"),
                "evidence_type": node.get("evidence_type"),
            })
        return {"node_id": node_id, "evidence": evidence, "walk": walked}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": {**self.metadata, "generated_at": self.metadata.get("generated_at") or utc_now_iso()},
            "node_count": len(self.nodes),
            "relationship_count": len(self.relationships),
            "nodes": [n.to_dict() for n in sorted(self.nodes.values(), key=lambda x: x.id)],
            "relationships": [r.to_dict() for r in sorted(self.relationships.values(), key=lambda x: x.id)],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "CanonicalContextGraph":
        graph = cls(metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
        for item in payload.get("nodes", []) if isinstance(payload.get("nodes"), list) else []:
            graph.add_node(GraphNode(**item))
        for item in payload.get("relationships", []) if isinstance(payload.get("relationships"), list) else []:
            graph.add_relationship(GraphRelationship(**item))
        return graph
