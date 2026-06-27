"""
Athena Sports Intelligence Platform

Epic 4D.3f

Historical Graph Bridge

Converts historical trend signals into graph-ready evidence nodes and
relationships without mutating the canonical graph engine directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from Core.json_utils import write_json
from Core.project_paths import OUTPUT_DIR

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from Knowledge.Historical.synthesis_engine import (
    build_historical_trend_synthesis,
)

try:
    from Knowledge.Historical.confidence_engine import (
        HistoricalExplainabilityEngine,
    )
    from Knowledge.Historical.explainability import (
        HISTORICAL_EXPLAINABILITY_VERSION,
    )
except Exception:  # pragma: no cover - defensive compatibility
    HistoricalExplainabilityEngine = None
    HISTORICAL_EXPLAINABILITY_VERSION = "unavailable"


HISTORICAL_GRAPH_BRIDGE_VERSION = "4D.3f-historical-graph-bridge"
HISTORICAL_GRAPH_NODES_FILE = "historical_graph_nodes.json"
HISTORICAL_GRAPH_RELATIONSHIPS_FILE = "historical_graph_relationships.json"
HISTORICAL_GRAPH_BRIDGE_SUMMARY_FILE = "historical_graph_bridge_summary.json"


@dataclass(slots=True)
class HistoricalGraphNode:
    id: str
    type: str
    label: str
    entity_id: str
    confidence: float
    source: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "entity_id": self.entity_id,
            "confidence": self.confidence,
            "source": self.source,
            "properties": self.properties,
        }


@dataclass(slots=True)
class HistoricalGraphRelationship:
    id: str
    type: str
    from_id: str
    to_id: str
    confidence: float
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "from": self.from_id,
            "to": self.to_id,
            "confidence": self.confidence,
            "properties": self.properties,
        }


def _safe_id(value: str) -> str:
    return str(value).replace(":", "_").replace("/", "_").replace(" ", "_")


def _signal_node_id(signal: dict[str, Any]) -> str:
    return f"historical_signal_node:{_safe_id(signal.get('id') or signal.get('entity_id') or 'unknown')}"


def _entity_node_id(entity_id: str) -> str:
    return f"entity:{entity_id}"


def _relationship_id(rel_type: str, from_id: str, to_id: str) -> str:
    return f"historical_rel:{rel_type}:{_safe_id(from_id)}:{_safe_id(to_id)}"


def node_from_signal(signal: dict[str, Any]) -> HistoricalGraphNode:
    entity_id = str(signal.get("entity_id") or "unknown")
    group = str(signal.get("comparison_group") or "unknown")
    direction = str(signal.get("direction") or "unknown")
    strength = str(signal.get("strength") or "none")
    confidence = float(signal.get("confidence", 0.0) or 0.0)

    explanation_package: dict[str, Any] | None = None
    if HistoricalExplainabilityEngine is not None:
        try:
            explanation_package = HistoricalExplainabilityEngine.build(signal).to_dict()
        except Exception:
            explanation_package = None

    return HistoricalGraphNode(
        id=_signal_node_id(signal),
        type="historical_trend_signal",
        label=f"{entity_id} {group} historical signal",
        entity_id=entity_id,
        confidence=confidence,
        source="historical_trend_synthesis",
        properties={
            "historical_graph_bridge_version": HISTORICAL_GRAPH_BRIDGE_VERSION,
            "historical_synthesis_version": signal.get("properties", {}).get("synthesis_version"),
            "historical_explainability_version": HISTORICAL_EXPLAINABILITY_VERSION,
            "signal_id": signal.get("id"),
            "comparison_group": group,
            "direction": direction,
            "strength": strength,
            "momentum_score": signal.get("momentum_score"),
            "comparison_count": signal.get("comparison_count"),
            "change_counts": signal.get("change_counts", {}),
            "delta_summary": signal.get("delta_summary", {}),
            "known_gaps": signal.get("known_gaps", []),
            "evidence_comparison_ids": signal.get("evidence_comparison_ids", []),
            "explainability": explanation_package,
        },
    )


def relationships_from_signal(signal: dict[str, Any], node: HistoricalGraphNode) -> list[HistoricalGraphRelationship]:
    entity_id = str(signal.get("entity_id") or "unknown")
    entity_node_id = _entity_node_id(entity_id)

    relationships = [
        HistoricalGraphRelationship(
            id=_relationship_id("has_historical_signal", entity_node_id, node.id),
            type="has_historical_signal",
            from_id=entity_node_id,
            to_id=node.id,
            confidence=node.confidence,
            properties={
                "historical_graph_bridge_version": HISTORICAL_GRAPH_BRIDGE_VERSION,
                "comparison_group": signal.get("comparison_group"),
            },
        )
    ]

    for comparison_id in signal.get("evidence_comparison_ids", []) or []:
        evidence_node_id = f"historical_comparison_node:{_safe_id(comparison_id)}"
        relationships.append(
            HistoricalGraphRelationship(
                id=_relationship_id("derived_from_historical_comparison", node.id, evidence_node_id),
                type="derived_from_historical_comparison",
                from_id=node.id,
                to_id=evidence_node_id,
                confidence=node.confidence,
                properties={
                    "historical_graph_bridge_version": HISTORICAL_GRAPH_BRIDGE_VERSION,
                    "comparison_id": comparison_id,
                },
            )
        )

    return relationships


def build_historical_graph_bridge(project_root: Path | None = None) -> dict[str, Any]:
    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"

    synthesis = build_historical_trend_synthesis(project_root)
    signals = synthesis.get("signals", {}).get("signals", [])

    nodes: list[HistoricalGraphNode] = []
    relationships: list[HistoricalGraphRelationship] = []

    for signal in signals:
        if not isinstance(signal, dict):
            continue
        node = node_from_signal(signal)
        nodes.append(node)
        relationships.extend(relationships_from_signal(signal, node))

    by_group: dict[str, int] = {}
    for node in nodes:
        group = str(node.properties.get("comparison_group") or "unknown")
        by_group[group] = by_group.get(group, 0) + 1

    node_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version": historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version": historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version": historical_version.HISTORICAL_ENGINE_VERSION,
        "historical_graph_bridge_version": HISTORICAL_GRAPH_BRIDGE_VERSION,
        "node_count": len(nodes),
        "nodes": [node.to_dict() for node in nodes],
    }

    relationship_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_graph_bridge_version": HISTORICAL_GRAPH_BRIDGE_VERSION,
        "relationship_count": len(relationships),
        "relationships": [relationship.to_dict() for relationship in relationships],
    }

    summary = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_graph_bridge_version": HISTORICAL_GRAPH_BRIDGE_VERSION,
        "historical_engine_version": historical_version.HISTORICAL_ENGINE_VERSION,
        "status": "ready" if nodes else "empty",
        "signal_count": len(signals),
        "node_count": len(nodes),
        "relationship_count": len(relationships),
        "groups": by_group,
        "nodes_file": str(output_dir / HISTORICAL_GRAPH_NODES_FILE),
        "relationships_file": str(output_dir / HISTORICAL_GRAPH_RELATIONSHIPS_FILE),
    }

    write_json(output_dir / HISTORICAL_GRAPH_NODES_FILE, node_payload)
    write_json(output_dir / HISTORICAL_GRAPH_RELATIONSHIPS_FILE, relationship_payload)
    write_json(output_dir / HISTORICAL_GRAPH_BRIDGE_SUMMARY_FILE, summary)

    return {
        "summary": summary,
        "nodes": node_payload,
        "relationships": relationship_payload,
    }


def historical_graph_nodes_for_entity(
    entity_id: str,
    *,
    project_root: Path | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    result = build_historical_graph_bridge(project_root)
    nodes = [
        node
        for node in result["nodes"].get("nodes", [])
        if node.get("entity_id") == entity_id
    ][: max(1, int(limit or 20))]

    return {
        "status": "available" if nodes else "empty",
        "athena_version": core_version.ATHENA_VERSION,
        "historical_graph_bridge_version": HISTORICAL_GRAPH_BRIDGE_VERSION,
        "entity_id": entity_id,
        "node_count": len(nodes),
        "nodes": nodes,
        "known_gaps": [] if nodes else ["No historical graph nodes are currently available for the requested entity."],
    }
