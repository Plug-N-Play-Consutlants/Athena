"""Validation for Athena v0.5.5.2.0 Cross-Sport Reasoning Engine."""
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
    from Core.version import ATHENA_VERSION, RELEASE_NAME
    from Intelligence import CROSS_SPORT_REASONING_VERSION, reason_cross_sport_query, studio_reasoning_diagnostics
    from Intelligence.Reasoning import (
        ReasoningAdapter,
        FusedEvidence,
        AmbiguityResolution,
        CrossSportReasoningResult,
        seed_reasoning_adapter_registry,
        adapter_registry_diagnostics,
    )
    from Intelligence.Pipeline import execute_explainable_intelligence
    from Intelligence.Foundation import capability_matrix, seed_intelligence_registry
    from Knowledge.Intelligence.Routing.multi_sport_router import route_multi_sport_query, studio_route_diagnostics

    version_tuple = tuple(map(int, ATHENA_VERSION.split(".")))
    check("version", version_tuple >= (0, 5, 5, 2, 0), ATHENA_VERSION)
    check("release", bool(RELEASE_NAME), RELEASE_NAME)
    check("reasoning version", tuple(map(int, CROSS_SPORT_REASONING_VERSION.split("."))) >= (0, 5, 5, 2, 0), CROSS_SPORT_REASONING_VERSION)

    registry = seed_reasoning_adapter_registry()
    adapters = registry.all_adapters()
    check("adapter registry type", len(adapters) >= 5 and all(isinstance(item, ReasoningAdapter) for item in adapters), str(registry.stats()))
    check("league adapter lookup", registry.resolve(league="NHL").label == "Hockey Reasoning" and registry.resolve(league="NBA").label == "Basketball Reasoning", str(registry.stats()))
    check("adapter diagnostics", adapter_registry_diagnostics()["status"] == "pass", str(adapter_registry_diagnostics()["stats"]))

    result = reason_cross_sport_query("Compare Auston Matthews vs Connor McDavid in the NHL")
    payload = result.to_dict()
    check("result object", isinstance(result, CrossSportReasoningResult), str(type(result)))
    check("route preserved", payload["route"] == "multi_sport_comparison", payload["route"])
    check("sport adapter selected", payload["adapter"] == "Hockey Reasoning", payload["adapter"])
    check("modules preserved", "player_assessment" in payload["modules"], str(payload["modules"]))
    check("evidence fusion", payload["evidence_count"] >= 4 and all("source" in item for item in payload["fused_evidence"]), str(payload["evidence_count"]))
    check("ambiguity payload", payload["ambiguity"]["status"] in {"resolved", "none", "ambiguous"}, str(payload["ambiguity"]))
    check("comparison enabled", payload["comparison"]["enabled"] is True, str(payload["comparison"]))
    check("confidence bounded", 0.4 <= payload["confidence"] <= 0.95, str(payload["confidence"]))
    check("steps generated", len(payload["reasoning_steps"]) >= 6, str(payload["reasoning_steps"]))

    event_result = reason_cross_sport_query("Summarize Blue Jays injuries")
    event_payload = event_result.to_dict()
    check("event context adapter", event_payload["adapter"] == "Baseball Reasoning" and event_payload["intent"] == "event_context", str(event_payload))
    check("event context evidence", event_payload["evidence_count"] >= 3, str(event_payload["evidence_count"]))

    basketball_result = reason_cross_sport_query("Tell me about the Toronto Raptors")
    check("basketball adapter", basketball_result.adapter == "Basketball Reasoning", str(basketball_result.to_dict()))

    # Prior sprint guardrails.
    explanation = execute_explainable_intelligence("Compare Auston Matthews vs Connor McDavid in the NHL")
    check("explainable pipeline preserved", explanation.reasoning.to_dict()["step_count"] >= 5 and explanation.evidence.source_counts()["knowledge"] >= 1, str(explanation.to_dict()))
    foundation = seed_intelligence_registry()
    check("foundation registry preserved", foundation.stats()["modules"] >= 10, str(foundation.stats()))
    check("capability matrix preserved", capability_matrix()["status"] == "pass", str(capability_matrix()["registry"]))
    route = route_multi_sport_query("Tell me about the Toronto Raptors")
    check("routing preserved", route.sport == "basketball" and route.intelligence_modules, str(route.to_dict()))

    diag = studio_reasoning_diagnostics()
    check("Studio reasoning diagnostics", diag["panel"] == "cross_sport_reasoning" and diag["status"] == "pass", str(diag.keys()))
    route_diag = studio_route_diagnostics()
    check("route diagnostics reasoning bridge", route_diag.get("reasoning", {}).get("panel") == "cross_sport_reasoning", str(route_diag.keys()))

    # Model smoke checks for public exports.
    check("model exports", FusedEvidence("x", "y").weighted_confidence() > 0 and AmbiguityResolution("none").ambiguous is False, "exports ok")

    failed = [row for row in CHECKS if not row[1]]
    print("Cross-Sport Reasoning Engine Validation")
    print("=" * 64)
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
