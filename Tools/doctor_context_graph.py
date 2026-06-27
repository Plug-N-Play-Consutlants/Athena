"""Doctor validation for Athena's canonical context graph."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import OUTPUT_DIR, REPORTS_DIR
from Knowledge.Graph import build_canonical_context_graph
from Knowledge.Graph.registries import EntityRegistry, RelationshipRegistry


def run_doctor(project_root: Path | None = None) -> Dict[str, Any]:
    root = Path(project_root) if project_root else PROJECT_ROOT
    output_dir = root / "Output"
    reports_dir = root / "Reports"
    graph_path = output_dir / "canonical_context_graph.json"
    if not graph_path.exists():
        build_canonical_context_graph(root)
    graph = read_optional_json(graph_path)
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    relationships = graph.get("relationships", []) if isinstance(graph, dict) else []
    nodes_by_id = {n.get("id"): n for n in nodes if isinstance(n, dict)}
    entity_registry = EntityRegistry()
    relationship_registry = RelationshipRegistry()

    failures: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    for node in nodes:
        result = entity_registry.validate_node(node)
        if not result.get("ok"):
            failures.append({"type": "node", "id": node.get("id"), **result})
    for rel in relationships:
        result = relationship_registry.validate_relationship(rel, nodes_by_id)
        if not result.get("ok"):
            failures.append({"type": "relationship", "id": rel.get("id"), **result})

    if not nodes:
        failures.append({"type": "graph", "reason": "No graph nodes found."})
    if not relationships:
        warnings.append({"type": "graph", "reason": "No graph relationships found."})

    report = {
        "overall_status": "PASS" if not failures else "FAIL",
        "node_count": len(nodes),
        "relationship_count": len(relationships),
        "failures": failures,
        "warnings": warnings,
        "entity_registry": entity_registry.to_dict(),
        "relationship_registry": relationship_registry.to_dict(),
    }
    write_json(reports_dir / "context_graph_doctor_report.json", report)
    text = [
        "Context Graph Doctor Report",
        "===========================",
        f"Overall status: {report['overall_status']}",
        f"Nodes: {len(nodes)}",
        f"Relationships: {len(relationships)}",
        f"Warnings: {len(warnings)}",
        f"Failures: {len(failures)}",
    ]
    (reports_dir / "context_graph_doctor_report.txt").write_text("\n".join(text), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run_doctor()
    print("Context Graph Doctor Report")
    print("===========================")
    print(f"Overall status: {result['overall_status']}")
    print(f"Nodes: {result['node_count']}")
    print(f"Relationships: {result['relationship_count']}")
    print(f"Warnings: {len(result['warnings'])}")
    print(f"Failures: {len(result['failures'])}")
    raise SystemExit(0 if result["overall_status"] == "PASS" else 1)
