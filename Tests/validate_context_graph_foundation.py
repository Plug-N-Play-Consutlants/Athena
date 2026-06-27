"""Validate Epic 4C.1 canonical context graph foundation."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION
from Knowledge.Graph import build_canonical_context_graph, evidence_chain_for_entity, load_graph
from Knowledge.Graph.registries import EntityRegistry, RelationshipRegistry
from Tools.doctor_context_graph import run_doctor


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    result = build_canonical_context_graph(PROJECT_ROOT)
    summary = result.get("summary", {})
    graph_payload = result.get("graph", {})

    check("graph_built", summary.get("status") == "ready", str(summary))
    check("player_nodes_present", summary.get("node_types", {}).get("player", 0) > 0, str(summary.get("node_types")))
    check("team_nodes_present", summary.get("node_types", {}).get("team", 0) > 0, str(summary.get("node_types")))
    check("contract_nodes_present", summary.get("node_types", {}).get("contract", 0) > 0, str(summary.get("node_types")))
    check("knowledge_pack_nodes_present", summary.get("node_types", {}).get("knowledge_pack", 0) >= 2, str(summary.get("node_types")))
    check("relationships_present", summary.get("relationship_count", 0) > 0, str(summary.get("relationship_types")))
    check("graph_is_provider_agnostic_output", graph_payload.get("metadata", {}).get("principle") == "connected_evidence_not_raw_files", str(graph_payload.get("metadata")))

    graph = load_graph(PROJECT_ROOT)
    player_ids = [nid for nid, n in graph.nodes.items() if n.type == "player"]
    first_player = player_ids[0] if player_ids else ""
    chain = evidence_chain_for_entity(first_player, project_root=PROJECT_ROOT)
    check("evidence_chain_available", chain.get("status") == "available" and len(chain.get("evidence", [])) >= 1, str(chain)[:200])
    check("graph_walk_returns_paths", bool(chain.get("walk", {}).get("paths")), str(chain.get("walk", {}).get("paths", [])[:2]))
    check("entity_registry_available", EntityRegistry().has("player") and EntityRegistry().has("knowledge_pack"), "player/knowledge_pack")
    check("relationship_registry_available", RelationshipRegistry().has("has_contract") and RelationshipRegistry().has("uses_rules_from"), "has_contract/uses_rules_from")
    doctor = run_doctor(PROJECT_ROOT)
    check("doctor_validation_passes", doctor.get("overall_status") == "PASS", str({"failures": doctor.get("failures", [])[:2], "warnings": doctor.get("warnings", [])[:2]}))
    check("version_current", ATHENA_VERSION == "0.5.0-drop4d1", f"Athena={ATHENA_VERSION}")

    passed = sum(1 for _, ok, _ in checks if ok)
    failed = len(checks) - passed
    print("Context Graph Foundation Validation Report")
    print("==========================================")
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
