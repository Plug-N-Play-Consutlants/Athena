"""
Athena Sports Intelligence Platform

Epic 4D.4c

Historical Intelligence Context Graph Integration

Builds an integrated canonical context graph that includes verified
historical trend signal and historical intelligence graph evidence without
mutating the base 4C graph builder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import OUTPUT_DIR

import Core.version as core_version

from Knowledge.Graph.builder import build_canonical_context_graph
from Knowledge.Graph.canonical_graph import (
    CanonicalContextGraph,
    GraphNode,
    GraphRelationship,
    utc_now_iso,
)

try:
    from Knowledge.Historical.graph_bridge import build_historical_graph_bridge
except Exception:  # pragma: no cover - compatibility guard
    build_historical_graph_bridge = None

try:
    from Knowledge.Historical.intelligence_graph_bridge import (
        build_historical_intelligence_graph_bridge,
    )
except Exception:  # pragma: no cover - compatibility guard
    build_historical_intelligence_graph_bridge = None


HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION = (
    "4D.4c-historical-context-graph-integration"
)

INTEGRATED_CONTEXT_GRAPH_FILE = "canonical_context_graph_with_historical_intelligence.json"
INTEGRATED_CONTEXT_GRAPH_SUMMARY_FILE = (
    "canonical_context_graph_with_historical_intelligence_summary.json"
)

HISTORICAL_GRAPH_NODES_FILE = "historical_graph_nodes.json"
HISTORICAL_GRAPH_RELATIONSHIPS_FILE = "historical_graph_relationships.json"
HISTORICAL_INTELLIGENCE_GRAPH_NODES_FILE = "historical_intelligence_graph_nodes.json"
HISTORICAL_INTELLIGENCE_GRAPH_RELATIONSHIPS_FILE = (
    "historical_intelligence_graph_relationships.json"
)


def _output_dir(project_root: Path | None = None) -> Path:
    return OUTPUT_DIR if project_root is None else Path(project_root) / "Output"


def _safe_id(value: Any) -> str:
    return str(value or "unknown").replace(":", "_").replace("/", "_")


def _relationship_id(kind: str, source_id: str, target_id: str) -> str:
    return f"rel:{kind}:{_safe_id(source_id)}:{_safe_id(target_id)}"


def _read_list_payload(output_dir: Path, file_name: str, key: str) -> list[dict[str, Any]]:
    payload = read_optional_json(output_dir / file_name)
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return [item for item in payload[key] if isinstance(item, dict)]
    return []


def _normalize_entity_endpoint(endpoint_id: str, graph: CanonicalContextGraph) -> str:
    """Translate bridge entity placeholders onto canonical entity ids where possible."""

    endpoint_id = str(endpoint_id or "unknown")

    if endpoint_id.startswith("entity:"):
        candidate = endpoint_id[len("entity:"):]
        if candidate in graph.nodes:
            return candidate

    return endpoint_id


def _ensure_node(
    graph: CanonicalContextGraph,
    node_id: str,
    *,
    node_type: str = "external_evidence",
    label: str | None = None,
    source: str = "historical_context_graph_integration",
    confidence: float = 0.5,
    properties: dict[str, Any] | None = None,
) -> None:
    if node_id in graph.nodes:
        return

    graph.add_node(
        GraphNode(
            id=node_id,
            type=node_type,
            label=label or node_id,
            evidence_type="historical_bridge_placeholder",
            source=source,
            confidence=confidence,
            properties=properties or {},
        )
    )


def _convert_historical_node(node: dict[str, Any]) -> GraphNode:
    node_id = str(node.get("id") or f"historical_node:{_safe_id(node)}")
    node_type = str(node.get("type") or "historical_evidence")
    label = str(node.get("label") or node_id)
    confidence = float(node.get("confidence", 0.0) or 0.0)
    source = str(node.get("source") or "historical_graph_bridge")

    properties = dict(node.get("properties") or {})
    properties["historical_context_graph_integration_version"] = (
        HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION
    )
    if node.get("entity_id"):
        properties["entity_id"] = node.get("entity_id")

    return GraphNode(
        id=node_id,
        type=node_type,
        label=label,
        evidence_type="historical_intelligence",
        source=source,
        confidence=confidence,
        properties=properties,
    )


def _convert_historical_relationship(
    relationship: dict[str, Any],
    graph: CanonicalContextGraph,
) -> GraphRelationship | None:
    raw_source = relationship.get("source_id") or relationship.get("from_id")
    raw_target = relationship.get("target_id") or relationship.get("to_id")

    if not raw_source or not raw_target:
        return None

    source_id = _normalize_entity_endpoint(str(raw_source), graph)
    target_id = _normalize_entity_endpoint(str(raw_target), graph)
    relationship_type = str(relationship.get("type") or "historically_related_to")
    confidence = float(relationship.get("confidence", 0.0) or 0.0)

    _ensure_node(
        graph,
        source_id,
        label=source_id,
        confidence=confidence,
        properties={"placeholder_reason": "historical_relationship_source"},
    )
    _ensure_node(
        graph,
        target_id,
        label=target_id,
        confidence=confidence,
        properties={"placeholder_reason": "historical_relationship_target"},
    )

    properties = dict(relationship.get("properties") or {})
    properties["historical_context_graph_integration_version"] = (
        HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION
    )
    properties["raw_source_id"] = raw_source
    properties["raw_target_id"] = raw_target

    return GraphRelationship(
        id=str(
            relationship.get("id")
            or _relationship_id(relationship_type, source_id, target_id)
        ),
        source_id=source_id,
        target_id=target_id,
        type=relationship_type,
        source="historical_context_graph_integration",
        confidence=confidence,
        properties=properties,
    )


def _build_upstream_historical_outputs(project_root: Path | None = None) -> None:
    if callable(build_historical_graph_bridge):
        try:
            build_historical_graph_bridge(project_root)
        except TypeError:
            build_historical_graph_bridge()
        except Exception:
            pass

    if callable(build_historical_intelligence_graph_bridge):
        try:
            build_historical_intelligence_graph_bridge(project_root)
        except TypeError:
            build_historical_intelligence_graph_bridge()
        except Exception:
            pass


def build_context_graph_with_historical_intelligence(
    project_root: Path | None = None,
) -> dict[str, Any]:
    output_dir = _output_dir(project_root)

    base = build_canonical_context_graph(project_root)
    base_graph_payload = base.get("graph", {})
    graph = CanonicalContextGraph.from_dict(base_graph_payload)

    _build_upstream_historical_outputs(project_root)

    historical_signal_nodes = _read_list_payload(
        output_dir,
        HISTORICAL_GRAPH_NODES_FILE,
        "nodes",
    )
    historical_signal_relationships = _read_list_payload(
        output_dir,
        HISTORICAL_GRAPH_RELATIONSHIPS_FILE,
        "relationships",
    )
    historical_intelligence_nodes = _read_list_payload(
        output_dir,
        HISTORICAL_INTELLIGENCE_GRAPH_NODES_FILE,
        "nodes",
    )
    historical_intelligence_relationships = _read_list_payload(
        output_dir,
        HISTORICAL_INTELLIGENCE_GRAPH_RELATIONSHIPS_FILE,
        "relationships",
    )

    base_node_count = len(graph.nodes)
    base_relationship_count = len(graph.relationships)

    for node in [*historical_signal_nodes, *historical_intelligence_nodes]:
        graph.add_node(_convert_historical_node(node))

    skipped_relationships: list[dict[str, Any]] = []
    for relationship in [*historical_signal_relationships, *historical_intelligence_relationships]:
        converted = _convert_historical_relationship(relationship, graph)
        if converted is None:
            skipped_relationships.append(
                {"relationship": relationship, "reason": "missing_source_or_target"}
            )
            continue
        graph.add_relationship(converted)

    graph.metadata.update(
        {
            "athena_version": core_version.ATHENA_VERSION,
            "historical_context_graph_integration_version":
                HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION,
            "base_graph_version": graph.metadata.get("graph_version"),
            "generated_at": utc_now_iso(),
        }
    )

    payload = graph.to_dict()

    node_types: dict[str, int] = {}
    relationship_types: dict[str, int] = {}
    for node in payload["nodes"]:
        node_types[node["type"]] = node_types.get(node["type"], 0) + 1
    for relationship in payload["relationships"]:
        relationship_types[relationship["type"]] = relationship_types.get(
            relationship["type"],
            0,
        ) + 1

    summary = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_context_graph_integration_version":
            HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION,
        "status": "ready" if payload["node_count"] > 0 else "empty",
        "base_node_count": base_node_count,
        "base_relationship_count": base_relationship_count,
        "node_count": payload["node_count"],
        "relationship_count": payload["relationship_count"],
        "historical_signal_node_count": len(historical_signal_nodes),
        "historical_signal_relationship_count": len(historical_signal_relationships),
        "historical_intelligence_node_count": len(historical_intelligence_nodes),
        "historical_intelligence_relationship_count": len(historical_intelligence_relationships),
        "added_node_count": max(0, payload["node_count"] - base_node_count),
        "added_relationship_count": max(
            0,
            payload["relationship_count"] - base_relationship_count,
        ),
        "skipped_relationship_count": len(skipped_relationships),
        "node_types": node_types,
        "relationship_types": relationship_types,
        "graph_file": str(output_dir / INTEGRATED_CONTEXT_GRAPH_FILE),
    }

    write_json(output_dir / INTEGRATED_CONTEXT_GRAPH_FILE, payload)
    write_json(output_dir / INTEGRATED_CONTEXT_GRAPH_SUMMARY_FILE, summary)

    return {
        "summary": summary,
        "graph": payload,
        "skipped_relationships": skipped_relationships,
    }


def historical_context_graph_nodes_for_entity(
    entity_id: str,
    *,
    project_root: Path | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    result = build_context_graph_with_historical_intelligence(project_root)
    graph = result["graph"]

    nodes = [
        node
        for node in graph.get("nodes", [])
        if node.get("id") == entity_id
        or node.get("properties", {}).get("entity_id") == entity_id
    ]

    nodes = nodes[: max(1, int(limit or 20))]

    return {
        "status": "available" if nodes else "empty",
        "athena_version": core_version.ATHENA_VERSION,
        "historical_context_graph_integration_version":
            HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION,
        "entity_id": entity_id,
        "node_count": len(nodes),
        "nodes": nodes,
        "known_gaps": []
        if nodes
        else ["No integrated historical context graph nodes found for entity."],
    }
