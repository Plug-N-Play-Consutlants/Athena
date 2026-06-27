"""
Athena Sports Intelligence Platform

Epic 4D.4c Doctor

Historical Intelligence Context Graph Integration
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version

from Knowledge.Graph.historical_integration import (
    HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION,
    build_context_graph_with_historical_intelligence,
    historical_context_graph_nodes_for_entity,
)


def _check(checks: list[dict[str, Any]], name: str, condition: bool, detail: Any = "") -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})


def run_doctor(project_root: Path | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    result = build_context_graph_with_historical_intelligence(project_root)
    summary = result["summary"]
    graph = result["graph"]
    nodes = graph.get("nodes", [])
    relationships = graph.get("relationships", [])

    historical_nodes = [node for node in nodes if node.get("type") in {"historical_trend_signal", "historical_intelligence"}]
    historical_intelligence_nodes = [node for node in nodes if node.get("type") == "historical_intelligence"]
    historical_relationships = [
        rel for rel in relationships
        if rel.get("type") in {
            "has_historical_signal",
            "derived_from_historical_comparison",
            "has_historical_intelligence",
            "derived_from_historical_signal_node",
        }
    ]

    sample_node = historical_intelligence_nodes[0] if historical_intelligence_nodes else (historical_nodes[0] if historical_nodes else {})
    sample_entity = sample_node.get("properties", {}).get("entity_id") or sample_node.get("entity_id", "") if sample_node else ""
    entity_payload = historical_context_graph_nodes_for_entity(sample_entity, project_root=project_root) if sample_entity else {"status": "empty"}

    _check(checks, "athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
    _check(checks, "integration_version_present", bool(HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION), HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION)
    _check(checks, "summary_version_matches_core", summary.get("athena_version") == core_version.ATHENA_VERSION, summary.get("athena_version"))
    _check(checks, "summary_integration_version_matches_constant", summary.get("historical_context_graph_integration_version") == HISTORICAL_CONTEXT_GRAPH_INTEGRATION_VERSION, summary.get("historical_context_graph_integration_version"))
    _check(checks, "summary_status_ready", summary.get("status") == "ready", summary)
    _check(checks, "base_graph_present", summary.get("base_node_count", 0) > 0, summary.get("base_node_count"))
    _check(checks, "nodes_generated", len(nodes) > 0, len(nodes))
    _check(checks, "relationships_generated", len(relationships) > 0, len(relationships))
    _check(checks, "historical_nodes_integrated", len(historical_nodes) > 0, len(historical_nodes))
    _check(checks, "historical_intelligence_nodes_integrated", len(historical_intelligence_nodes) > 0, len(historical_intelligence_nodes))
    _check(checks, "historical_relationships_integrated", len(historical_relationships) > 0, len(historical_relationships))
    _check(checks, "node_count_matches", summary.get("node_count") == len(nodes), summary.get("node_count"))
    _check(checks, "relationship_count_matches", summary.get("relationship_count") == len(relationships), summary.get("relationship_count"))
    _check(checks, "entity_lookup_available", entity_payload.get("status") == "available", entity_payload)

    if sample_node:
        props = sample_node.get("properties", {})
        _check(
            checks,
            "sample_node_graph_ready",
            bool(sample_node.get("id"))
            and sample_node.get("type") in {"historical_trend_signal", "historical_intelligence"}
            and bool(props.get("historical_context_graph_integration_version")),
            sample_node,
        )

    failed = [check for check in checks if check["status"] != "PASS"]
    return {
        "doctor": "context_graph_historical_integration",
        "overall_status": "PASS" if not failed else "FAIL",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:
    report = run_doctor(PROJECT_ROOT)
    print("Historical Context Graph Integration Doctor")
    print("=" * 50)
    print(f"Overall status: {report['overall_status']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print()
    for check in report["checks"]:
        print(f"[{check['status']}] {check['name']}: {check['detail']}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
