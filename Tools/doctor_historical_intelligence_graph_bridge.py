"""
Athena Sports Intelligence Platform

Epic 4D.4b Doctor

Historical Intelligence Graph Bridge
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version

from Knowledge.Historical.intelligence_graph_bridge import (
    HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION,
    build_historical_intelligence_graph_bridge,
    historical_intelligence_graph_nodes_for_entity,
)
from Knowledge.Historical.intelligence_engine import HISTORICAL_INTELLIGENCE_VERSION


def _check(checks: list[dict[str, Any]], name: str, condition: bool, detail: Any = "") -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})


def run_doctor(project_root: Path | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    result = build_historical_intelligence_graph_bridge(project_root)
    summary = result["summary"]
    nodes = result["nodes"].get("nodes", [])
    relationships = result["relationships"].get("relationships", [])

    sample_node = nodes[0] if nodes else {}
    sample_entity = sample_node.get("entity_id", "") if sample_node else ""
    entity_payload = historical_intelligence_graph_nodes_for_entity(sample_entity, project_root=project_root) if sample_entity else {"status": "empty"}

    _check(checks, "athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
    _check(checks, "bridge_version_present", bool(HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION), HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION)
    _check(checks, "intelligence_version_present", bool(HISTORICAL_INTELLIGENCE_VERSION), HISTORICAL_INTELLIGENCE_VERSION)
    _check(checks, "summary_version_matches_core", summary.get("athena_version") == core_version.ATHENA_VERSION, summary.get("athena_version"))
    _check(checks, "summary_bridge_version_matches_constant", summary.get("historical_intelligence_graph_bridge_version") == HISTORICAL_INTELLIGENCE_GRAPH_BRIDGE_VERSION, summary.get("historical_intelligence_graph_bridge_version"))
    _check(checks, "summary_intelligence_version_matches_constant", summary.get("historical_intelligence_version") == HISTORICAL_INTELLIGENCE_VERSION, summary.get("historical_intelligence_version"))
    _check(checks, "summary_status_ready", summary.get("status") == "ready", summary)
    _check(checks, "nodes_generated", len(nodes) > 0, len(nodes))
    _check(checks, "relationships_generated", len(relationships) > 0, len(relationships))
    _check(checks, "node_count_matches", summary.get("node_count") == len(nodes), summary.get("node_count"))
    _check(checks, "relationship_count_matches", summary.get("relationship_count") == len(relationships), summary.get("relationship_count"))
    _check(checks, "entity_lookup_available", entity_payload.get("status") == "available", entity_payload)

    if sample_node:
        props = sample_node.get("properties", {})
        _check(
    checks,
    "sample_node_graph_ready",
    sample_node.get("type") in {
        "historical_intelligence",
        "historical_intelligence_signal",
    }
    and bool(sample_node.get("id"))
    and bool(sample_node.get("entity_id"))
    and bool(sample_node.get("properties", {}).get("pattern_type")),
    sample_node,
)
        _check(checks, "sample_node_has_evidence", len(props.get("evidence_node_ids", [])) > 0, props.get("evidence_node_ids"))
        _check(checks, "sample_node_has_explanation", bool(props.get("explanation")), props.get("explanation"))

    failed = [check for check in checks if check["status"] != "PASS"]
    return {
        "doctor": "historical_intelligence_graph_bridge",
        "overall_status": "PASS" if not failed else "FAIL",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:
    report = run_doctor(PROJECT_ROOT)
    print("Historical Intelligence Graph Bridge Doctor")
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
