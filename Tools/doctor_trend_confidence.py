"""Doctor validation for 4D.2d Trend Confidence & Explainability."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Knowledge.Trends.confidence_engine import CONFIDENCE_ENGINE_VERSION
from Knowledge.Trends.engine import build_trend_intelligence

checks = []


def check(name: str, condition: bool, detail=""):
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})

payload = build_trend_intelligence(PROJECT_ROOT)
summary = payload["summary"]
results = payload["results"].get("results", [])
sample = results[0] if results else {}
properties = sample.get("properties", {}) if isinstance(sample, dict) else {}
confidence_payload = properties.get("confidence_engine", {}) if isinstance(properties, dict) else {}
confidence = confidence_payload.get("confidence", {}) if isinstance(confidence_payload, dict) else {}
quality = confidence_payload.get("quality", {}) if isinstance(confidence_payload, dict) else {}
explanation = confidence_payload.get("explanation", {}) if isinstance(confidence_payload, dict) else {}

check("engine_ready", summary.get("status") == "ready", summary)
check("confidence_engine_version_current", summary.get("confidence_engine_version") == CONFIDENCE_ENGINE_VERSION, summary.get("confidence_engine_version"))
check("results_available", len(results) > 0, len(results))
check("result_confidence_payload_present", bool(confidence_payload), confidence_payload.keys() if isinstance(confidence_payload, dict) else type(confidence_payload))
check("confidence_score_normalized", 0.0 <= confidence.get("overall_score", -1) <= 1.0, confidence.get("overall_score"))
check("confidence_components_present", len(confidence.get("components", [])) > 0, len(confidence.get("components", [])))
check("quality_score_normalized", 0.0 <= quality.get("quality_score", -1) <= 1.0, quality.get("quality_score"))
check("explanation_summary_present", bool(explanation.get("summary")), explanation.get("summary"))

failed = [item for item in checks if item["status"] != "PASS"]

print("Trend Confidence Doctor")
print("=" * 24)
print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
print(f"Passed: {len(checks) - len(failed)}")
print(f"Failed: {len(failed)}")
print()
for item in checks:
    print(f"[{item['status']}] {item['name']}: {item['detail']}")

raise SystemExit(0 if not failed else 1)
