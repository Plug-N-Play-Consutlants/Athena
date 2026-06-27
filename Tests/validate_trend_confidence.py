"""
Athena Sports Intelligence Platform

4D.2d Validation

Trend Confidence & Explainability
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Knowledge.Trends.confidence_engine import CONFIDENCE_ENGINE_VERSION
from Knowledge.Trends.engine import build_trend_intelligence

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[PASS] {name}: {detail}")
    else:
        failed += 1
        print(f"[FAIL] {name}: {detail}")


print("Trend Confidence Validation Report")
print("=" * 40)

payload = build_trend_intelligence(PROJECT_ROOT)
summary = payload["summary"]
results_payload = payload["results"]
trends = results_payload.get("trends", [])
results = results_payload.get("results", [])

check("trend_intelligence_ready", summary.get("status") == "ready", summary.get("status"))
check("confidence_engine_version_summary", summary.get("confidence_engine_version") == CONFIDENCE_ENGINE_VERSION, summary.get("confidence_engine_version"))
check("trends_available", len(trends) > 0, len(trends))
check("results_available", len(results) > 0, len(results))

sample_result = results[0]
properties = sample_result.get("properties", {})
confidence_payload = properties.get("confidence_engine", {})
confidence = confidence_payload.get("confidence", {})
quality = confidence_payload.get("quality", {})
explanation = confidence_payload.get("explanation", {})

check("result_has_confidence_engine_version", properties.get("confidence_engine_version") == CONFIDENCE_ENGINE_VERSION, properties.get("confidence_engine_version"))
check("result_has_confidence_engine", bool(confidence_payload), confidence_payload.keys() if isinstance(confidence_payload, dict) else type(confidence_payload))
check("confidence_package_present", bool(confidence), confidence.keys() if isinstance(confidence, dict) else type(confidence))
check("explanation_package_present", bool(explanation), explanation.keys() if isinstance(explanation, dict) else type(explanation))
check("quality_package_present", bool(quality), quality.keys() if isinstance(quality, dict) else type(quality))

check("confidence_score_normalized", 0.0 <= confidence.get("overall_score", -1) <= 1.0, confidence.get("overall_score"))
check("confidence_band_present", bool(confidence.get("confidence_band")), confidence.get("confidence_band"))
check("confidence_components_present", len(confidence.get("components", [])) > 0, len(confidence.get("components", [])))

check("quality_score_normalized", 0.0 <= quality.get("quality_score", -1) <= 1.0, quality.get("quality_score"))
check("quality_completeness_normalized", 0.0 <= quality.get("completeness_score", -1) <= 1.0, quality.get("completeness_score"))
check("quality_freshness_normalized", 0.0 <= quality.get("freshness_score", -1) <= 1.0, quality.get("freshness_score"))
check("quality_consistency_normalized", 0.0 <= quality.get("consistency_score", -1) <= 1.0, quality.get("consistency_score"))

check("explanation_summary_present", bool(explanation.get("summary")), explanation.get("summary"))
check("explanation_evidence_present", len(explanation.get("evidence", [])) > 0, explanation.get("evidence"))
check("known_gaps_list", isinstance(explanation.get("known_gaps"), list), explanation.get("known_gaps"))
check("recommendations_list", isinstance(explanation.get("recommendations"), list), explanation.get("recommendations"))
check("result_confidence_matches_package", sample_result.get("confidence") == confidence.get("overall_score"), {"result": sample_result.get("confidence"), "package": confidence.get("overall_score")})

print()
print("=" * 40)
overall = "PASS" if failed == 0 else "FAIL"
print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")

raise SystemExit(0 if failed == 0 else 1)
