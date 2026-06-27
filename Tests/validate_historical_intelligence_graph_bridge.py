"""
Athena Sports Intelligence Platform

Epic 4D.4b Validation

Historical Intelligence Graph Bridge
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version

from Knowledge.Historical.intelligence import (
    HISTORICAL_INTELLIGENCE_VERSION,
)

from Knowledge.Historical.intelligence_graph_bridge import (
    HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
    build_historical_intelligence_graph_bridge,
    historical_intelligence_graph_nodes_for_entity,
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


print("Historical Intelligence Graph Bridge Validation Report")
print("=" * 60)

result = build_historical_intelligence_graph_bridge(PROJECT_ROOT)

summary = result["summary"]
nodes = result["nodes"].get("nodes", [])
relationships = result["relationships"].get("relationships", [])

sample_node = nodes[0] if nodes else None
sample_relationship = relationships[0] if relationships else None

sample_entity = sample_node.get("entity_id") if sample_node else ""

entity_payload = (
    historical_intelligence_graph_nodes_for_entity(
        sample_entity,
        project_root=PROJECT_ROOT,
    )
    if sample_entity
    else {"status": "empty"}
)

check("athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)

check(
    "bridge_version_present",
    bool(HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION),
    HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
)

check(
    "intelligence_version_present",
    bool(HISTORICAL_INTELLIGENCE_VERSION),
    HISTORICAL_INTELLIGENCE_VERSION,
)

check(
    "summary_version_matches_core",
    summary.get("athena_version") == core_version.ATHENA_VERSION,
    summary.get("athena_version"),
)

check(
    "summary_bridge_version_matches_constant",
    summary.get("historical_intelligence_graph_bridge_version")
    == HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
    summary.get("historical_intelligence_graph_bridge_version"),
)

check(
    "summary_intelligence_version_matches_constant",
    summary.get("historical_intelligence_version") == HISTORICAL_INTELLIGENCE_VERSION,
    summary.get("historical_intelligence_version"),
)

check("summary_status_ready", summary.get("status") == "ready", summary)

check("nodes_generated", len(nodes) > 0, len(nodes))

check("node_count_matches", summary.get("node_count") == len(nodes), summary.get("node_count"))

check("relationships_generated", len(relationships) > 0, len(relationships))

check(
    "relationship_count_matches",
    summary.get("relationship_count") == len(relationships),
    summary.get("relationship_count"),
)

check("patterns_present", bool(summary.get("patterns")), summary.get("patterns"))

check("directions_present", bool(summary.get("directions")), summary.get("directions"))

if sample_node:
    check(
        "sample_node_type",
        sample_node.get("type")
        in {
            "historical_intelligence",
            "historical_intelligence_signal",
        },
        sample_node.get("type"),
    )

    check("sample_node_has_entity", bool(sample_node.get("entity_id")), sample_node.get("entity_id"))

    check(
        "sample_node_confidence_normalized",
        0.0 <= float(sample_node.get("confidence", 0.0)) <= 1.0,
        sample_node.get("confidence"),
    )

    properties = sample_node.get("properties", {})

    check("sample_node_has_properties", bool(properties), properties.keys())

    check("sample_node_has_pattern", bool(properties.get("pattern_type")), properties.get("pattern_type"))

    check("sample_node_has_evidence", bool(properties.get("evidence_node_ids")), properties.get("evidence_node_ids"))

    check("sample_node_has_explanation", bool(properties.get("explanation")), properties.get("explanation"))

    check("entity_lookup_available", entity_payload.get("status") == "available", entity_payload)

else:
    check("sample_node_available", False, "no nodes generated")

if sample_relationship:
    check(
        "sample_relationship_has_type",
        bool(sample_relationship.get("type")),
        sample_relationship.get("type"),
    )

    check(
        "sample_relationship_has_from",
        bool(sample_relationship.get("from_id")),
        sample_relationship.get("from_id"),
    )

    check(
        "sample_relationship_has_to",
        bool(sample_relationship.get("to_id")),
        sample_relationship.get("to_id"),
    )

    check(
        "sample_relationship_confidence_normalized",
        0.0 <= float(sample_relationship.get("confidence", 0.0)) <= 1.0,
        sample_relationship.get("confidence"),
    )

else:
    check("sample_relationship_available", False, "no relationships generated")


print()
print("=" * 60)

overall = "PASS" if failed == 0 else "FAIL"

print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")

raise SystemExit(0 if failed == 0 else 1)