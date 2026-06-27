"""Doctor for Athena v0.5.5.1.0 Explainable Intelligence Pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(condition), detail))


def main() -> int:
    print("Explainable Intelligence Pipeline Doctor")
    print("=" * 64)
    required = [
        "Intelligence/Explainability/__init__.py",
        "Intelligence/Explainability/models.py",
        "Intelligence/Pipeline/__init__.py",
        "Intelligence/Pipeline/execution_pipeline.py",
        "Intelligence/Confidence/__init__.py",
        "Intelligence/Confidence/confidence_propagation.py",
        "Tests/validate_explainable_intelligence_pipeline.py",
        "Tools/doctor_explainable_intelligence_pipeline.py",
    ]
    for rel in required:
        check(f"required file exists: {rel}", (ROOT / rel).exists(), rel)

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    check("version metadata", ATHENA_VERSION == ATHENA_BUILD and tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 5, 5, 1, 0) and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", ATHENA_VERSION)
    check("release family", bool(RELEASE_NAME), RELEASE_NAME)

    from Intelligence.Explainability import EXPLAINABLE_INTELLIGENCE_VERSION, EvidenceBundle, EvidenceItem, ReasoningStep, ReasoningTrace
    from Intelligence.Confidence import CONFIDENCE_PROPAGATION_VERSION, propagate_confidence
    from Intelligence.Pipeline import EXPLAINABLE_PIPELINE_VERSION, execute_explainable_intelligence, studio_explainability_diagnostics

    check("explainability package version", EXPLAINABLE_INTELLIGENCE_VERSION == "0.5.5.1.0", EXPLAINABLE_INTELLIGENCE_VERSION)
    check("pipeline package version", EXPLAINABLE_PIPELINE_VERSION == "0.5.5.1.0", EXPLAINABLE_PIPELINE_VERSION)
    check("confidence package version", CONFIDENCE_PROPAGATION_VERSION == "0.5.5.1.0", CONFIDENCE_PROPAGATION_VERSION)

    evidence = EvidenceBundle(knowledge=(EvidenceItem("knowledge", "sample", "doctor", 0.7),))
    trace = ReasoningTrace((ReasoningStep("doctor", "Doctor Step", detail="ok"),))
    confidence = propagate_confidence(0.65, evidence, trace)
    check("confidence propagation", confidence.score > 0.4 and confidence.factors, str(confidence.to_dict()))

    result = execute_explainable_intelligence("Compare Auston Matthews vs Connor McDavid in the NHL")
    payload = result.to_dict()
    check("execution pipeline returns trace", payload["reasoning"]["step_count"] >= 5, str(payload["reasoning"]))
    check("execution pipeline returns evidence", sum(payload["evidence"]["source_counts"].values()) >= 3, str(payload["evidence"]["source_counts"]))
    check("execution pipeline returns confidence", payload["confidence"]["score"] > 0.4, str(payload["confidence"]))

    diagnostics = studio_explainability_diagnostics()
    check("Studio diagnostics payload", diagnostics["panel"] == "explainable_intelligence" and diagnostics["status"] == "pass", str(diagnostics.keys()))

    from Knowledge.Intelligence.Routing.multi_sport_router import studio_route_diagnostics
    check("routing diagnostics bridge", studio_route_diagnostics().get("explainability", {}).get("panel") == "explainable_intelligence", str(studio_route_diagnostics().keys()))

    failed = [row for row in CHECKS if not row[1]]
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
