"""Doctor validation for Athena Epic 4C.2 evidence chains."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Knowledge.Graph import build_canonical_context_graph, build_evidence_chain, load_graph


def run_doctor(project_root: Path | None = None) -> Dict[str, Any]:
    root = Path(project_root) if project_root else PROJECT_ROOT
    build_canonical_context_graph(root)
    graph = load_graph(root)
    failures: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    player_ids = sorted([nid for nid, node in graph.nodes.items() if node.type == "player"])
    if not player_ids:
        failures.append({"type": "graph", "reason": "No player nodes available for evidence-chain validation."})
        sample_id = ""
        chain: Dict[str, Any] = {}
    else:
        sample_id = player_ids[0]
        chain = build_evidence_chain(sample_id, max_depth=2, project_root=root)
        if chain.get("status") != "available":
            failures.append({"type": "chain", "reason": "Evidence chain was not available.", "detail": chain})
        if not chain.get("paths"):
            failures.append({"type": "chain", "reason": "Evidence chain has no scored paths."})
        if not chain.get("evidence_chain"):
            failures.append({"type": "chain", "reason": "Evidence chain contains no node evidence."})
        confidence = chain.get("confidence")
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            failures.append({"type": "chain", "reason": "Confidence is not normalized between 0 and 1.", "confidence": confidence})
        developer = chain.get("developer") if isinstance(chain.get("developer"), dict) else {}
        if not developer.get("relationship_weights"):
            failures.append({"type": "chain", "reason": "Developer relationship weights are missing."})
        if len(chain.get("paths", [])) < 2:
            warnings.append({"type": "chain", "reason": "Only one path was found for the sample entity."})

    report = {
        "overall_status": "PASS" if not failures else "FAIL",
        "sample_entity_id": sample_id,
        "chain_status": chain.get("status") if isinstance(chain, dict) else None,
        "chain_confidence": chain.get("confidence") if isinstance(chain, dict) else None,
        "path_count": len(chain.get("paths", [])) if isinstance(chain, dict) else 0,
        "evidence_count": len(chain.get("evidence_chain", [])) if isinstance(chain, dict) else 0,
        "failures": failures,
        "warnings": warnings,
    }
    reports_dir = root / "Reports"
    write_json(reports_dir / "evidence_chain_doctor_report.json", report)
    text = [
        "Evidence Chain Doctor Report",
        "============================",
        f"Overall status: {report['overall_status']}",
        f"Sample entity: {sample_id}",
        f"Paths: {report['path_count']}",
        f"Evidence nodes: {report['evidence_count']}",
        f"Confidence: {report['chain_confidence']}",
        f"Warnings: {len(warnings)}",
        f"Failures: {len(failures)}",
    ]
    (reports_dir / "evidence_chain_doctor_report.txt").write_text("\n".join(text), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run_doctor()
    print("Evidence Chain Doctor Report")
    print("============================")
    print(f"Overall status: {result['overall_status']}")
    print(f"Sample entity: {result['sample_entity_id']}")
    print(f"Paths: {result['path_count']}")
    print(f"Evidence nodes: {result['evidence_count']}")
    print(f"Confidence: {result['chain_confidence']}")
    print(f"Warnings: {len(result['warnings'])}")
    print(f"Failures: {len(result['failures'])}")
    raise SystemExit(0 if result["overall_status"] == "PASS" else 1)
