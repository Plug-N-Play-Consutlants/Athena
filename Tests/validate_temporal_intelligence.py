"""Validate Epic 4D.1 temporal intelligence foundation."""

from __future__ import annotations

from pathlib import Path
import sys

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
from Tools.doctor_temporal_intelligence import run_doctor


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    temporal = build_temporal_evidence(PROJECT_ROOT)
    summary = temporal.get("summary", {})
    timeline = temporal.get("timeline", {})
    events = timeline.get("events", [])

    check("temporal_version", timeline.get("temporal_version") == TEMPORAL_VERSION, str(timeline.get("temporal_version")))
    check("timeline_ready", summary.get("status") == "ready" and summary.get("event_count", 0) > 0, str(summary))
    check("events_sorted", events == sorted(events, key=lambda e: (e.get("occurred_at") or "9999-12-31T23:59:59+00:00", e.get("type") or "", e.get("id") or "")), "sorted")
    check("contract_events_present", summary.get("event_types", {}).get("contract_snapshot", 0) > 0, str(summary.get("event_types")))
    check("transaction_events_present", summary.get("event_types", {}).get("transaction", 0) > 0, str(summary.get("event_types")))
    check("asset_movement_events_present", summary.get("event_types", {}).get("asset_movement", 0) > 0, str(summary.get("event_types")))
    check("production_events_present", summary.get("event_types", {}).get("production_snapshot", 0) > 0, str(summary.get("event_types")))
    check("dated_range_present", bool(summary.get("earliest_event")) and bool(summary.get("latest_event")), str(summary))
    check("timeline_file_written", (PROJECT_ROOT / "Output" / "temporal_evidence_timeline.json").exists(), "temporal_evidence_timeline.json")

    enriched = enrich_graph_with_temporal_events(PROJECT_ROOT)
    graph_summary = enriched.get("summary", {})
    check("temporal_graph_ready", graph_summary.get("status") == "ready", str(graph_summary))
    check("temporal_nodes_added", graph_summary.get("temporal_event_nodes", 0) == summary.get("event_count", -1), str(graph_summary))
    check("temporal_relationships_added", graph_summary.get("has_temporal_event_relationships", 0) > 0, str(graph_summary))
    check("temporal_graph_file_written", (PROJECT_ROOT / "Output" / "canonical_context_graph_temporal.json").exists(), "canonical_context_graph_temporal.json")

    sample_subject = next((e.get("subject_id") for e in events if isinstance(e, dict) and str(e.get("subject_id", "")).startswith("player:")), "")
    entity_timeline = timeline_for_entity(sample_subject, project_root=PROJECT_ROOT) if sample_subject else {"status": "empty"}
    check("sample_entity_timeline_available", entity_timeline.get("status") == "available" and entity_timeline.get("event_count", 0) > 0, str(entity_timeline)[:500])

    missing = timeline_for_entity("player:this_entity_does_not_exist", project_root=PROJECT_ROOT)
    check("missing_entity_timeline_safe", missing.get("status") == "empty" and missing.get("known_gaps"), str(missing))

    scout_app = (PROJECT_ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    check("scout_timeline_endpoint_present", "/api/graph/timeline" in scout_app and "timeline_for_entity" in scout_app, "endpoint/import present")

    doctor = run_doctor(PROJECT_ROOT)
    check("doctor_validation_passes", doctor.get("overall_status") == "PASS", str(doctor))
    check("version_current", ATHENA_VERSION == "0.5.0-drop4d1", f"Athena={ATHENA_VERSION}")

    passed = sum(1 for _, ok, _ in checks)
    failed = len(checks) - passed
    print("Temporal Intelligence Validation Report")
    print("=======================================")
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    print(f"Passed: {passed}")
    print("Warnings: 0")
    print(f"Failed: {failed}")
    print()
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
