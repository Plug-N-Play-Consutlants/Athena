"""Doctor validation for Epic 4C.3 graph reasoning engine."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Knowledge.Graph import build_canonical_context_graph, load_graph
from Knowledge.Graph.reasoning_engine import build_reasoning_package, write_reasoning_report


def run_doctor(project_root: Path | None = None) -> Dict[str, Any]:
    root = Path(project_root or PROJECT_ROOT)
    checks: List[Dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    build_canonical_context_graph(root)
    graph = load_graph(root)
    player_ids = sorted([node_id for node_id, node in graph.nodes.items() if node.type == "player"])
    sample = player_ids[0] if player_ids else ""
    check("sample_player_available", bool(sample), sample)

    if sample:
        package = build_reasoning_package(sample, context_profile="fantasy", focus=["contract", "team"], max_depth=3, project_root=root)
        check("reasoning_package_available", package.get("status") == "available", str(package)[:200])
        check("reasoning_version_current", package.get("reasoning_version") == "4C.3-reasoning-engine", str(package.get("reasoning_version")))
        check("ranked_paths_present", len(package.get("reasoning_paths", [])) > 0, str(package.get("reasoning_paths", [])[:1]))
        scores = [p.get("relevance_score") for p in package.get("reasoning_paths", [])]
        check("relevance_scores_normalized", all(isinstance(s, (int, float)) and 0 <= s <= 1 for s in scores), str(scores[:8]))
        check("developer_weighting_present", bool(package.get("developer", {}).get("relationship_weights")), str(package.get("developer", {}))[:160])
        report = write_reasoning_report(sample, context_profile="fantasy", focus=["contract"], project_root=root)
        safe_id = sample.replace(":", "_").replace("/", "_")
        check("reasoning_report_written", (root / "Output" / f"reasoning_package_{safe_id}.json").exists() and report.get("status") == "available", safe_id)

    missing = build_reasoning_package("player:missing_reasoning_entity", project_root=root)
    check("missing_entity_safe", missing.get("status") == "not_found" and missing.get("confidence") == 0.0, str(missing))

    failed = [c for c in checks if c["status"] != "PASS"]
    return {
        "doctor": "reasoning_engine",
        "overall_status": "PASS" if not failed else "FAIL",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:
    result = run_doctor(PROJECT_ROOT)
    print("Reasoning Engine Doctor")
    print("=======================")
    print(f"Overall status: {result['overall_status']}")
    print(f"Passed: {result['passed']}")
    print(f"Failed: {result['failed']}")
    print()
    for item in result["checks"]:
        print(f"[{item['status']}] {item['name']}: {item.get('detail', '')}")
    return 0 if result["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
