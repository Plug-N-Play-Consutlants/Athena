"""
Athena Sports Intelligence Platform

Epic 4D.4b

Historical Intelligence Graph Bridge

Converts 4D.4 historical intelligence signals into graph-ready evidence
nodes and relationships without mutating the canonical graph engine directly.

This bridge intentionally avoids depending on a single historical intelligence
builder function name. It will use any available builder exposed by
Knowledge.Historical.intelligence_engine and otherwise fall back to the
canonical Output/historical_intelligence.json artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import OUTPUT_DIR

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from Knowledge.Historical.intelligence import (
    HISTORICAL_INTELLIGENCE_VERSION,
)


HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION = (
    "4D.4b-historical-intelligence-graph-bridge"
)

HISTORICAL_INTELLIGENCE_GRAPH_NODES_FILE = (
    "historical_intelligence_graph_nodes.json"
)
HISTORICAL_INTELLIGENCE_GRAPH_RELATIONSHIPS_FILE = (
    "historical_intelligence_graph_relationships.json"
)
HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_SUMMARY_FILE = (
    "historical_intelligence_graph_bridge_summary.json"
)
HISTORICAL_INTELLIGENCE_FILE = "historical_intelligence.json"


@dataclass(slots=True)
class HistoricalIntelligenceGraphNode:
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
class HistoricalIntelligenceGraphRelationship:
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
            "from_id": self.from_id,
            "to_id": self.to_id,
            "confidence": self.confidence,
            "properties": self.properties,
        }


def _safe_id(value: Any) -> str:
    return str(value or "unknown").replace(":", "_").replace("/", "_")


def _entity_node_id(entity_id: str) -> str:
    return f"entity:{entity_id}"


def _intelligence_node_id(signal: dict[str, Any]) -> str:
    return f"historical_intelligence_node:{_safe_id(signal.get('id'))}"


def _relationship_id(kind: str, from_id: str, to_id: str) -> str:
    return f"rel:{kind}:{_safe_id(from_id)}:{_safe_id(to_id)}"


def _output_dir(project_root: Path | None = None) -> Path:
    return OUTPUT_DIR if project_root is None else Path(project_root) / "Output"


def _coerce_signal_list(payload: Any) -> list[dict[str, Any]]:
    """Extract historical intelligence signal dictionaries from known shapes."""

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    # Preferred/likely shapes.
    for key in ("signals", "intelligence", "historical_intelligence"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _coerce_signal_list(value)
            if nested:
                return nested

    # Some payloads are wrappers with output sections.
    for key in ("payload", "result", "results", "data"):
        value = payload.get(key)
        nested = _coerce_signal_list(value)
        if nested:
            return nested

    return []


def _build_or_read_historical_intelligence(
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Build historical intelligence using any available API, else read output."""

    try:
        engine = import_module("Knowledge.Historical.intelligence_engine")
    except Exception:
        engine = None

    if engine is not None:
        for function_name in (
            "build_historical_intelligence",
            "build_historical_intelligence_signals",
            "build_historical_intelligence_payload",
            "build_intelligence",
            "run_historical_intelligence",
        ):
            builder = getattr(engine, function_name, None)
            if callable(builder):
                try:
                    payload = builder(project_root)
                    if isinstance(payload, dict):
                        return payload
                except TypeError:
                    try:
                        payload = builder()
                        if isinstance(payload, dict):
                            return payload
                    except Exception:
                        continue
                except Exception:
                    continue

    output_path = _output_dir(project_root) / HISTORICAL_INTELLIGENCE_FILE
    payload = read_optional_json(output_path)

    return payload if isinstance(payload, dict) else {}


def _historical_intelligence_signals(
    project_root: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _build_or_read_historical_intelligence(project_root)
    signals = _coerce_signal_list(payload)
    return payload, signals


def node_from_signal(signal: dict[str, Any]) -> HistoricalIntelligenceGraphNode:
    entity_id = str(signal.get("entity_id") or "unknown")
    pattern = str(signal.get("pattern_type") or "unknown")
    direction = str(signal.get("direction") or "unknown")
    strength = str(signal.get("strength") or "unknown")
    confidence = float(signal.get("confidence", 0.0) or 0.0)

    return HistoricalIntelligenceGraphNode(
        id=_intelligence_node_id(signal),
        type="historical_intelligence",
        label=f"{entity_id} {pattern} historical intelligence",
        entity_id=entity_id,
        confidence=confidence,
        source="historical_intelligence",
        properties={
            "historical_intelligence_graph_bridge_version":
                HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
            "historical_intelligence_version":
                HISTORICAL_INTELLIGENCE_VERSION,
            "signal_id": signal.get("id"),
            "pattern_type": pattern,
            "comparison_group": signal.get("properties", {}).get(
                "comparison_group",
            ),
            "direction": direction,
            "strength": strength,
            "evidence_node_ids": signal.get("evidence_node_ids", []),
            "evidence_signal_ids": signal.get("evidence_signal_ids", []),
            "explanation": signal.get("explanation"),
            "known_gaps": signal.get("known_gaps", []),
            "source_properties": signal.get("properties", {}),
        },
    )


def relationships_from_signal(
    signal: dict[str, Any],
    node: HistoricalIntelligenceGraphNode,
) -> list[HistoricalIntelligenceGraphRelationship]:
    entity_id = str(signal.get("entity_id") or "unknown")
    entity_node_id = _entity_node_id(entity_id)

    relationships = [
        HistoricalIntelligenceGraphRelationship(
            id=_relationship_id(
                "has_historical_intelligence",
                entity_node_id,
                node.id,
            ),
            type="has_historical_intelligence",
            from_id=entity_node_id,
            to_id=node.id,
            confidence=node.confidence,
            properties={
                "historical_intelligence_graph_bridge_version":
                    HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
                "pattern_type": signal.get("pattern_type"),
            },
        )
    ]

    for evidence_node_id in signal.get("evidence_node_ids", []) or []:
        relationships.append(
            HistoricalIntelligenceGraphRelationship(
                id=_relationship_id(
                    "derived_from_historical_signal_node",
                    node.id,
                    evidence_node_id,
                ),
                type="derived_from_historical_signal_node",
                from_id=node.id,
                to_id=evidence_node_id,
                confidence=node.confidence,
                properties={
                    "historical_intelligence_graph_bridge_version":
                        HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
                    "evidence_node_id": evidence_node_id,
                },
            )
        )

    return relationships


def build_historical_intelligence_graph_bridge(
    project_root: Path | None = None,
) -> dict[str, Any]:
    output_dir = _output_dir(project_root)

    source_payload, signals = _historical_intelligence_signals(project_root)

    nodes: list[HistoricalIntelligenceGraphNode] = []
    relationships: list[HistoricalIntelligenceGraphRelationship] = []

    for signal in signals:
        node = node_from_signal(signal)
        nodes.append(node)
        relationships.extend(relationships_from_signal(signal, node))

    by_pattern: dict[str, int] = {}
    by_direction: dict[str, int] = {}

    for node in nodes:
        pattern = str(node.properties.get("pattern_type") or "unknown")
        direction = str(node.properties.get("direction") or "unknown")
        by_pattern[pattern] = by_pattern.get(pattern, 0) + 1
        by_direction[direction] = by_direction.get(direction, 0) + 1

    node_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_intelligence_graph_bridge_version":
            HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
        "historical_intelligence_version": HISTORICAL_INTELLIGENCE_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "node_count": len(nodes),
        "nodes": [node.to_dict() for node in nodes],
    }

    relationship_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_intelligence_graph_bridge_version":
            HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
        "relationship_count": len(relationships),
        "relationships": [relationship.to_dict() for relationship in relationships],
    }

    summary = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_intelligence_graph_bridge_version":
            HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
        "historical_intelligence_version": HISTORICAL_INTELLIGENCE_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "status": "ready" if nodes else "empty",
        "source_signal_count": len(signals),
        "node_count": len(nodes),
        "relationship_count": len(relationships),
        "patterns": by_pattern,
        "directions": by_direction,
        "nodes_file": str(
            output_dir / HISTORICAL_INTELLIGENCE_GRAPH_NODES_FILE,
        ),
        "relationships_file": str(
            output_dir / HISTORICAL_INTELLIGENCE_GRAPH_RELATIONSHIPS_FILE,
        ),
        "source_payload_keys": sorted(source_payload.keys())
        if isinstance(source_payload, dict)
        else [],
    }

    write_json(
        output_dir / HISTORICAL_INTELLIGENCE_GRAPH_NODES_FILE,
        node_payload,
    )
    write_json(
        output_dir / HISTORICAL_INTELLIGENCE_GRAPH_RELATIONSHIPS_FILE,
        relationship_payload,
    )
    write_json(
        output_dir / HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_SUMMARY_FILE,
        summary,
    )

    return {
        "summary": summary,
        "nodes": node_payload,
        "relationships": relationship_payload,
    }


def historical_intelligence_graph_nodes_for_entity(
    entity_id: str,
    *,
    project_root: Path | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    result = build_historical_intelligence_graph_bridge(project_root)

    nodes = [
        node
        for node in result["nodes"].get("nodes", [])
        if node.get("entity_id") == entity_id
    ]

    nodes = nodes[: max(1, int(limit or 20))]

    return {
        "status": "available" if nodes else "empty",
        "athena_version": core_version.ATHENA_VERSION,
        "historical_intelligence_graph_bridge_version":
            HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
        "entity_id": entity_id,
        "node_count": len(nodes),
        "nodes": nodes,
        "known_gaps": []
        if nodes
        else [
            "No historical intelligence graph nodes are available for the requested entity."
        ],
    }
