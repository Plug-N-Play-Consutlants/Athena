"""
Athena Sports Intelligence Platform

Epic 4D.3e Validation

Historical Signal Explainability
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
from Knowledge.Historical.confidence_engine import (
    HISTORICAL_CONFIDENCE_ENGINE_VERSION,
    HistoricalExplainabilityEngine,
)
from Knowledge.Historical.explainability import HISTORICAL_EXPLAINABILITY_VERSION
from Knowledge.Historical.synthesis_engine import build_historical_trend_synthesis


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


print("Historical Signal Explainability Validation Report")
print("=" * 60)

synthesis = build_historical_trend_synthesis(PROJECT_ROOT)
summary = synthesis["summary"]
signals = synthesis["signals"].get("signals", [])

check("athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
check("synthesis_ready", summary.get("status") == "ready", summary.get("status"))
check("signals_available", len(signals) > 0, len(signals))

sample_signal = signals[0] if signals else {}
package = HistoricalExplainabilityEngine.build(sample_signal) if sample_signal else None
serialized = package.to_dict() if package else {}

check(
    "confidence_engine_version",
    serialized.get("historical_confidence_engine_version") == HISTORICAL_CONFIDENCE_ENGINE_VERSION,
    serialized.get("historical_confidence_engine_version"),
)
check(
    "explainability_version",
    serialized.get("historical_explainability_version") == HISTORICAL_EXPLAINABILITY_VERSION,
    serialized.get("historical_explainability_version"),
)
check("confidence_present", "confidence" in serialized, serialized.keys())
check("explanation_present", "explanation" in serialized, serialized.keys())

confidence = serialized.get("confidence", {})
explanation = serialized.get("explanation", {})

check("confidence_score_normalized", 0.0 <= float(confidence.get("score", -1)) <= 1.0, confidence.get("score"))
check("confidence_band_present", bool(confidence.get("band")), confidence.get("band"))
check("confidence_components_present", len(confidence.get("components", [])) > 0, len(confidence.get("components", [])))

check("explanation_summary_present", bool(explanation.get("summary")), explanation.get("summary"))
check("explanation_evidence_present", len(explanation.get("evidence", [])) > 0, explanation.get("evidence", []))
check("explanation_limitations_list", isinstance(explanation.get("limitations", []), list), explanation.get("limitations", []))
check("explanation_confidence_notes_present", len(explanation.get("confidence_notes", [])) > 0, explanation.get("confidence_notes", []))

metadata = HistoricalExplainabilityEngine.metadata()
check("metadata_confidence_version", metadata.get("historical_confidence_engine_version") == HISTORICAL_CONFIDENCE_ENGINE_VERSION, metadata)
check("metadata_explainability_version", metadata.get("historical_explainability_version") == HISTORICAL_EXPLAINABILITY_VERSION, metadata)

print()
print("=" * 60)
overall = "PASS" if failed == 0 else "FAIL"
print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")

raise SystemExit(0 if failed == 0 else 1)
