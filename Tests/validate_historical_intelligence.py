"""
Athena Sports Intelligence Platform

Epic 4D.4 Validation

Historical Intelligence
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
from Knowledge.Historical.intelligence import HISTORICAL_INTELLIGENCE_VERSION, HistoricalIntelligenceSynthesizer
from Knowledge.Historical.intelligence_engine import build_historical_intelligence_signals, historical_intelligence_for_entity

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

print("Historical Intelligence Validation Report")
print("=" * 50)

# Remove generated downstream artifact before validation to avoid stale-output false negatives.
for name in ["historical_intelligence.json", "historical_intelligence_signal_summary.json"]:
    path = PROJECT_ROOT / "Output" / name
    if path.exists():
        path.unlink()

result = build_historical_intelligence_signals(PROJECT_ROOT)
summary = result["summary"]
signals = result["intelligence"].get("signals", [])
sample = signals[0] if signals else {}
entity_payload = historical_intelligence_for_entity(sample.get("entity_id", ""), project_root=PROJECT_ROOT) if sample else {"status": "empty"}

check("athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
check("historical_intelligence_version_present", bool(HISTORICAL_INTELLIGENCE_VERSION), HISTORICAL_INTELLIGENCE_VERSION)
check("summary_version_matches_core", summary.get("athena_version") == core_version.ATHENA_VERSION, summary.get("athena_version"))
check("summary_intelligence_version_matches_constant", summary.get("historical_intelligence_version") == HISTORICAL_INTELLIGENCE_VERSION, summary.get("historical_intelligence_version"))
check("summary_status_ready", summary.get("status") == "ready", summary)
check("source_nodes_available", summary.get("source_node_count", 0) > 0, summary.get("source_node_count"))
check("intelligence_signals_generated", len(signals) > 0, len(signals))
check("signal_count_matches", summary.get("signal_count") == len(signals), summary.get("signal_count"))
check("patterns_present", bool(summary.get("patterns")), summary.get("patterns"))
check("directions_present", bool(summary.get("directions")), summary.get("directions"))

if sample:
    check("sample_signal_has_entity", bool(sample.get("entity_id")), sample.get("entity_id"))
    check("sample_signal_pattern_valid", sample.get("pattern_type") in {"trajectory", "consistency", "volatility", "regression", "insufficient"}, sample.get("pattern_type"))
    check("sample_signal_direction_valid", sample.get("direction") in {"improving", "declining", "stable", "volatile", "unknown"}, sample.get("direction"))
    check("sample_signal_strength_valid", sample.get("strength") in {"none", "weak", "moderate", "strong"}, sample.get("strength"))
    check("sample_signal_confidence_normalized", 0.0 <= float(sample.get("confidence", 0.0)) <= 1.0, sample.get("confidence"))
    check("sample_signal_has_evidence", len(sample.get("evidence_node_ids", [])) > 0, sample.get("evidence_node_ids"))
    check("sample_signal_has_explanation", bool(sample.get("explanation")), sample.get("explanation"))
    check("entity_lookup_available", entity_payload.get("status") == "available", entity_payload)

check("synthesizer_available", HistoricalIntelligenceSynthesizer.__name__ == "HistoricalIntelligenceSynthesizer", HistoricalIntelligenceSynthesizer.__name__)

print()
print("=" * 50)
overall = "PASS" if failed == 0 else "FAIL"
print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")
raise SystemExit(0 if failed == 0 else 1)
