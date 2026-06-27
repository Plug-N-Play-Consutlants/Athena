"""Doctor for Epic 4D.1 temporal intelligence foundation."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION
from Knowledge.Graph.temporal_intelligence import (
    TEMPORAL_VERSION,
    build_temporal_evidence,
    enrich_graph_with_temporal_events,
    timeline_for_entity,
)


def run_doctor(project_root: Path | None = None) -> Dict[str, Any]:
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    checks: List[Dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any = "") -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:600]})

    timeline_result = build_temporal_evidence(root)
    summary = timeline_result.get("summary", {})
    check("temporal_version_current", summary.get("temporal_version") == TEMPORAL_VERSION, summary.get("temporal_version"))
    check("timeline_available", summary.get("status") == "ready" and summary.get("event_count", 0) > 0, summary)
    check("event_types_present", len(summary.get("event_types", {})) >= 2, summary.get("event_types"))
    check("dated_events_present", summary.get("earliest_event") is not None and summary.get("latest_event") is not None, summary)

    graph_result = enrich_graph_with_temporal_events(root)
    graph_summary = graph_result.get("summary", {})
    check("temporal_graph_available", graph_summary.get("status") == "ready", graph_summary)
    check("temporal_event_nodes_present", graph_summary.get("temporal_event_nodes", 0) > 0, graph_summary)
    check("temporal_relationships_present", graph_summary.get("has_temporal_event_relationships", 0) > 0, graph_summary)

    events = timeline_result.get("timeline", {}).get("events", [])
    sample_subject = next((e.get("subject_id") for e in events if isinstance(e, dict) and e.get("subject_id", "").startswith("player:")), "")
    entity_timeline = timeline_for_entity(sample_subject, project_root=root) if sample_subject else {"status": "empty"}
    check("entity_timeline_available", entity_timeline.get("status") == "available", entity_timeline)
    check("version_current", ATHENA_VERSION == "0.5.0-drop4d1", f"Athena={ATHENA_VERSION}")

    failed = sum(1 for item in checks if item["status"] != "PASS")
    return {
        "doctor": "temporal_intelligence",
        "overall_status": "PASS" if failed == 0 else "FAIL",
        "passed": len(checks) - failed,
        "failed": failed,
        "checks": checks,
    }


if __name__ == "__main__":
    result = run_doctor()
    print("Temporal Intelligence Doctor")
    print("============================")
    print(f"Overall status: {result['overall_status']}")
    print(f"Passed: {result['passed']}")
    print(f"Failed: {result['failed']}")
    print()
    for item in result["checks"]:
        print(f"[{item['status']}] {item['name']}: {item['detail']}")
    raise SystemExit(0 if result["overall_status"] == "PASS" else 1)
