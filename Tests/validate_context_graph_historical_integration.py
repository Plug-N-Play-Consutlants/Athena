"""
Athena Sports Intelligence Platform

Epic 4D.4c Validation

Historical Intelligence Context Graph Integration
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version

from Knowledge.Graph.historical_integration import (
    HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION,
    build_context_graph_with_historical_intelligence,
    historical_context_graph_nodes_for_entity,
)


passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[PASS] {name}: {detail}")
    else:
        failed += 1
        print(f"[FAIL] {name}: {detail}")


print("Historical Context Graph Integration Validation Report")
print("=" * 65)

result = build_context_graph_with_historical_intelligence(PROJECT_ROOT)
summary = result["summary"]
graph = result["graph"]
nodes = graph.get("nodes", [])
relationships = graph.get("relationships", [])

historical_nodes = [
    node for node in nodes
    if node.get("type") in {"historical_trend_signal", "historical_intelligence"}
]
historical_intelligence_nodes = [
    node for node in nodes
    if node.get("type") == "historical_intelligence"
]
historical_signal_nodes = [
    node for node in nodes
    if node.get("type") == "historical_trend_signal"
]
historical_relationships = [
    rel for rel in relationships
    if rel.get("type") in {
        "has_historical_signal",
        "derived_from_historical_comparison",
        "has_historical_intelligence",
        "derived_from_historical_signal_node",
    }
]

sample_node = historical_intelligence_nodes[0] if historical_intelligence_nodes else (historical_nodes[0] if historical_nodes else None)
sample_entity = sample_node.get("properties", {}).get("entity_id") or sample_node.get("entity_id") if sample_node else ""
entity_payload = (
    historical_context_graph_nodes_for_entity(sample_entity, project_root=PROJECT_ROOT)
    if sample_entity else {"status": "empty"}
)

check("athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
check("integration_version_present", bool(HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION), HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION)
check("summary_version_matches_core", summary.get("athena_version") == core_version.ATHENA_VERSION, summary.get("athena_version"))
check("summary_integration_version_matches_constant", summary.get("historical_context_graph_integration_version") == HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION, summary.get("historical_context_graph_integration_version"))
check("summary_status_ready", summary.get("status") == "ready", summary)
check("base_graph_present", summary.get("base_node_count", 0) > 0, summary.get("base_node_count"))
check("integrated_graph_has_nodes", len(nodes) > 0, len(nodes))
check("integrated_graph_has_relationships", len(relationships) > 0, len(relationships))
check("node_count_matches", summary.get("node_count") == len(nodes), summary.get("node_count"))
check("relationship_count_matches", summary.get("relationship_count") == len(relationships), summary.get("relationship_count"))
check("historical_signal_nodes_integrated", len(historical_signal_nodes) == summary.get("historical_signal_node_count"), {"actual": len(historical_signal_nodes), "summary": summary.get("historical_signal_node_count")})
check("historical_intelligence_nodes_integrated", len(historical_intelligence_nodes) == summary.get("historical_intelligence_node_count"), {"actual": len(historical_intelligence_nodes), "summary": summary.get("historical_intelligence_node_count")})
check("historical_nodes_present", len(historical_nodes) > 0, len(historical_nodes))
check("historical_relationships_present", len(historical_relationships) > 0, len(historical_relationships))
check("node_types_include_historical_intelligence", "historical_intelligence" in summary.get("node_types", {}), summary.get("node_types"))
check("relationship_types_include_historical_intelligence", "has_historical_intelligence" in summary.get("relationship_types", {}), summary.get("relationship_types"))

if sample_node:
    props = sample_node.get("properties", {})
    check("sample_node_graph_ready", bool(sample_node.get("id")) and bool(sample_node.get("type")) and bool(props), sample_node)
    check("sample_node_has_integration_version", props.get("historical_context_graph_integration_version") == HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION, props.get("historical_context_graph_integration_version"))
    check("sample_node_has_entity_linkage", bool(props.get("entity_id") or sample_node.get("entity_id")), props.get("entity_id") or sample_node.get("entity_id"))
    check("entity_lookup_available", entity_payload.get("status") == "available", entity_payload)
else:
    check("sample_node_available", False, "no historical nodes generated")

print()
print("=" * 65)
overall = "PASS" if failed == 0 else "FAIL"
print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")

raise SystemExit(0 if failed == 0 else 1)
