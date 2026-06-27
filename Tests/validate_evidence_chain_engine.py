"""Validate Epic 4C.2 evidence-chain engine."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION
from Knowledge.Graph import build_canonical_context_graph, build_evidence_chain, load_graph, write_evidence_chain_report
from Tools.doctor_evidence_chain import run_doctor


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    build_canonical_context_graph(PROJECT_ROOT)
    graph = load_graph(PROJECT_ROOT)
    player_ids = sorted([nid for nid, node in graph.nodes.items() if node.type == "player"])
    sample = player_ids[0] if player_ids else ""

    chain = build_evidence_chain(sample, max_depth=2, project_root=PROJECT_ROOT)
    check("chain_available", chain.get("status") == "available", str(chain)[:240])
    check("chain_has_version", chain.get("chain_version") == "4C.2-evidence-chain-engine", str(chain.get("chain_version")))
    check("chain_has_entity", chain.get("entity", {}).get("id") == sample, str(chain.get("entity")))
    check("chain_has_paths", len(chain.get("paths", [])) > 0, str(chain.get("paths", [])[:1]))
    check("chain_has_steps", any(p.get("steps") for p in chain.get("paths", [])), str(chain.get("paths", [])[:1]))
    check("chain_has_evidence_nodes", len(chain.get("evidence_chain", [])) >= 2, str(chain.get("evidence_chain", [])[:2]))
    check("confidence_normalized", isinstance(chain.get("confidence"), (int, float)) and 0 <= chain.get("confidence") <= 1, str(chain.get("confidence")))
    check("developer_trace_present", bool(chain.get("developer", {}).get("relationship_weights")) and bool(chain.get("developer", {}).get("node_type_weights")), str(chain.get("developer", {}))[:200])

    contract_chain = build_evidence_chain(sample, max_depth=1, relationship_types=["has_contract"], project_root=PROJECT_ROOT)
    relationship_types = {step.get("relationship_type") for path in contract_chain.get("paths", []) for step in path.get("steps", [])}
    check("relationship_filter_applies", relationship_types == {"has_contract"} if relationship_types else False, str(relationship_types))

    missing = build_evidence_chain("player:this_entity_does_not_exist", project_root=PROJECT_ROOT)
    check("missing_entity_safe", missing.get("status") == "not_found" and missing.get("confidence") == 0.0, str(missing))

    report = write_evidence_chain_report(sample, max_depth=2, project_root=PROJECT_ROOT)
    safe_id = sample.replace(":", "_").replace("/", "_")
    check("report_written", (PROJECT_ROOT / "Output" / f"evidence_chain_{safe_id}.json").exists() and report.get("status") == "available", safe_id)

    doctor = run_doctor(PROJECT_ROOT)
    check("doctor_validation_passes", doctor.get("overall_status") == "PASS", str(doctor))
    check("version_current", ATHENA_VERSION == "0.5.0-drop4d1", f"Athena={ATHENA_VERSION}")

    passed = sum(1 for _, ok, _ in checks if ok)
    failed = len(checks) - passed
    print("Evidence Chain Engine Validation Report")
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
