"""
Athena Sports Intelligence Platform

Epic 4D.3f Validation

Historical Graph Bridge
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version

from Knowledge.Historical.graph_bridge import (
    HISTORICAL_GRAPH_BRIDGE_VERSION,
    build_historical_graph_bridge,
    historical_graph_nodes_for_entity,
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


print("Historical Graph Bridge Validation Report")
print("=" * 50)

result = build_historical_graph_bridge(PROJECT_ROOT)
summary = result["summary"]
nodes = result["nodes"].get("nodes", [])
relationships = result["relationships"].get("relationships", [])

sample_node = nodes[0] if nodes else None
sample_entity = sample_node.get("entity_id") if sample_node else ""
entity_payload = historical_graph_nodes_for_entity(sample_entity, project_root=PROJECT_ROOT) if sample_entity else {"status": "empty"}

check("athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
check("graph_bridge_version_present", HISTORICAL_GRAPH_BRIDGE_VERSION == "4D.3f-historical-graph-bridge", HISTORICAL_GRAPH_BRIDGE_VERSION)
check("summary_version_matches_core", summary["athena_version"] == core_version.ATHENA_VERSION, summary["athena_version"])
check("summary_bridge_version_matches_constant", summary["historical_graph_bridge_version"] == HISTORICAL_GRAPH_BRIDGE_VERSION, summary["historical_graph_bridge_version"])
check("summary_status_ready", summary["status"] == "ready", summary)
check("signals_available", summary["signal_count"] > 0, summary["signal_count"])
check("nodes_generated", len(nodes) > 0, len(nodes))
check("node_count_matches", summary["node_count"] == len(nodes), summary["node_count"])
check("relationships_generated", len(relationships) > 0, len(relationships))
check("relationship_count_matches", summary["relationship_count"] == len(relationships), summary["relationship_count"])
check("groups_present", isinstance(summary.get("groups"), dict), summary.get("groups"))

if sample_node:
    check("sample_node_type", sample_node.get("type") == "historical_trend_signal", sample_node.get("type"))
    check("sample_node_has_entity", bool(sample_node.get("entity_id")), sample_node.get("entity_id"))
    check("sample_node_confidence_normalized", 0.0 <= float(sample_node.get("confidence", 0.0)) <= 1.0, sample_node.get("confidence"))
    check("sample_node_has_properties", isinstance(sample_node.get("properties"), dict), sample_node.get("properties", {}).keys())
    check("sample_node_has_explainability", "explainability" in sample_node.get("properties", {}), sample_node.get("properties", {}).keys())
    check("sample_node_explainability_hydrated", sample_node.get("properties", {}).get("explainability") is not None, sample_node.get("properties", {}).get("explainability"))
    check("sample_node_explainability_version_hydrated", sample_node.get("properties", {}).get("historical_explainability_version") != "unavailable", sample_node.get("properties", {}).get("historical_explainability_version"))
    check("entity_lookup_available", entity_payload["status"] == "available", entity_payload)

sample_relationship = relationships[0] if relationships else None
if sample_relationship:
    check("sample_relationship_has_type", bool(sample_relationship.get("type")), sample_relationship.get("type"))
    check("sample_relationship_has_from", bool(sample_relationship.get("from")), sample_relationship.get("from"))
    check("sample_relationship_has_to", bool(sample_relationship.get("to")), sample_relationship.get("to"))
    check("sample_relationship_confidence_normalized", 0.0 <= float(sample_relationship.get("confidence", 0.0)) <= 1.0, sample_relationship.get("confidence"))

print()
print("=" * 50)
overall = "PASS" if failed == 0 else "FAIL"
print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")

raise SystemExit(0 if failed == 0 else 1)
