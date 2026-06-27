"""Validate Epic 4C.3 graph reasoning engine."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION
from Knowledge.Graph import build_canonical_context_graph, load_graph
from Knowledge.Graph.reasoning_engine import build_reasoning_package, write_reasoning_report
from Tools.doctor_reasoning_engine import run_doctor


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    build_canonical_context_graph(PROJECT_ROOT)
    graph = load_graph(PROJECT_ROOT)
    player_ids = sorted([nid for nid, node in graph.nodes.items() if node.type == "player"])
    sample = player_ids[0] if player_ids else ""
    check("sample_player_available", bool(sample), sample)

    package = build_reasoning_package(sample, context_profile="fantasy", focus=["contract", "team"], max_depth=3, project_root=PROJECT_ROOT)
    check("package_available", package.get("status") == "available", str(package)[:240])
    check("reasoning_version", package.get("reasoning_version") == "4C.3-reasoning-engine", str(package.get("reasoning_version")))
    check("query_echoes_context", package.get("query", {}).get("context_profile") == "fantasy", str(package.get("query")))
    check("focus_applied", "contract" in package.get("query", {}).get("focus", []), str(package.get("query")))
    check("paths_ranked", len(package.get("reasoning_paths", [])) > 0 and package.get("reasoning_paths", [])[0].get("rank") == 1, str(package.get("reasoning_paths", [])[:1]))
    scores = [p.get("relevance_score") for p in package.get("reasoning_paths", [])]
    check("scores_normalized", all(isinstance(s, (int, float)) and 0 <= s <= 1 for s in scores), str(scores[:8]))
    check("relevant_evidence_present", len(package.get("relevant_evidence", [])) >= 2, str(package.get("relevant_evidence", [])[:2]))
    check("confidence_normalized", isinstance(package.get("confidence"), (int, float)) and 0 <= package.get("confidence") <= 1, str(package.get("confidence")))
    check("developer_weights_present", bool(package.get("developer", {}).get("relationship_weights")) and bool(package.get("developer", {}).get("node_type_weights")), str(package.get("developer", {}))[:200])

    public_package = build_reasoning_package(sample, context_profile="public", focus=["public", "rules"], max_depth=3, traversal="breadth_first", project_root=PROJECT_ROOT)
    check("alternate_context_available", public_package.get("status") == "available" and public_package.get("query", {}).get("traversal") == "breadth_first", str(public_package.get("query")))

    depth_package = build_reasoning_package(sample, context_profile="projection", traversal="depth_first", max_depth=3, project_root=PROJECT_ROOT)
    check("depth_first_supported", depth_package.get("status") == "available" and depth_package.get("query", {}).get("traversal") == "depth_first", str(depth_package.get("query")))

    missing = build_reasoning_package("player:this_entity_does_not_exist", project_root=PROJECT_ROOT)
    check("missing_entity_safe", missing.get("status") == "not_found" and missing.get("confidence") == 0.0, str(missing))

    report = write_reasoning_report(sample, context_profile="fantasy", focus=["contract"], project_root=PROJECT_ROOT)
    safe_id = sample.replace(":", "_").replace("/", "_")
    check("report_written", (PROJECT_ROOT / "Output" / f"reasoning_package_{safe_id}.json").exists() and report.get("status") == "available", safe_id)

    doctor = run_doctor(PROJECT_ROOT)
    check("doctor_validation_passes", doctor.get("overall_status") == "PASS", str(doctor))
    check("version_current", ATHENA_VERSION == "0.5.0-drop4d1", f"Athena={ATHENA_VERSION}")

    passed = sum(1 for _, ok, _ in checks)
    failed = len(checks) - passed
    print("Reasoning Engine Validation Report")
    print("==================================")
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
