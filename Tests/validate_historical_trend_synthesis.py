"""
Athena Sports Intelligence Platform

Epic 4D.3d Validation

Historical Trend Synthesis
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from Knowledge.Historical.synthesis import HistoricalTrendSynthesizer
from Knowledge.Historical.synthesis_engine import (
    build_historical_trend_synthesis,
    historical_trend_signals_for_entity,
)

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


print("Historical Trend Synthesis Validation Report")
print("=" * 55)

result = build_historical_trend_synthesis(PROJECT_ROOT)
summary = result["summary"]
signals = result["signals"].get("signals", [])
comparisons = result["comparisons"].get("comparisons", [])

sample_signal = signals[0] if signals else None
sample_entity = sample_signal.get("entity_id") if sample_signal else ""
entity_payload = (
    historical_trend_signals_for_entity(sample_entity, project_root=PROJECT_ROOT)
    if sample_entity
    else {"status": "empty"}
)

check("athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
check("historical_domain_version_present", bool(historical_version.HISTORICAL_DOMAIN_VERSION), historical_version.HISTORICAL_DOMAIN_VERSION)
check("historical_schema_version_present", bool(historical_version.HISTORICAL_SCHEMA_VERSION), historical_version.HISTORICAL_SCHEMA_VERSION)
check("historical_engine_version_present", bool(historical_version.HISTORICAL_ENGINE_VERSION), historical_version.HISTORICAL_ENGINE_VERSION)
check("historical_synthesis_version_present", bool(historical_version.HISTORICAL_SYNTHESIS_VERSION), historical_version.HISTORICAL_SYNTHESIS_VERSION)

check("summary_version_matches_core", summary["athena_version"] == core_version.ATHENA_VERSION, summary["athena_version"])
check("summary_synthesis_version_matches_constant", summary["historical_synthesis_version"] == historical_version.HISTORICAL_SYNTHESIS_VERSION, summary["historical_synthesis_version"])
check("summary_status_valid", summary["status"] in {"ready", "insufficient_data"}, summary["status"])
check("comparisons_available", len(comparisons) > 0, len(comparisons))
check("signals_payload_available", isinstance(signals, list), type(signals).__name__)
check("signal_count_matches", summary["signal_count"] == len(signals), summary["signal_count"])

if sample_signal:
    check("sample_signal_has_entity", bool(sample_signal["entity_id"]), sample_signal["entity_id"])
    check("sample_signal_has_group", bool(sample_signal["comparison_group"]), sample_signal["comparison_group"])
    check("sample_signal_direction_valid", sample_signal["direction"] in {"improving", "declining", "stable", "mixed", "unknown"}, sample_signal["direction"])
    check("sample_signal_strength_valid", sample_signal["strength"] in {"none", "weak", "moderate", "strong"}, sample_signal["strength"])
    check("sample_signal_momentum_normalized", -1.0 <= sample_signal["momentum_score"] <= 1.0, sample_signal["momentum_score"])
    check("sample_signal_confidence_normalized", 0.0 <= sample_signal["confidence"] <= 1.0, sample_signal["confidence"])
    check("sample_signal_change_counts_present", isinstance(sample_signal["change_counts"], dict), sample_signal["change_counts"])
    check("sample_signal_evidence_present", len(sample_signal["evidence_comparison_ids"]) > 0, sample_signal["evidence_comparison_ids"][:3])
    check("entity_lookup_available", entity_payload["status"] == "available", entity_payload)
else:
    check("signals_absent_only_when_no_comparisons", len(comparisons) == 0, {"comparisons": len(comparisons), "signals": len(signals)})

metadata = historical_version.metadata()
check("metadata_includes_synthesis", metadata["historical_synthesis_version"] == historical_version.HISTORICAL_SYNTHESIS_VERSION, metadata)
check("synthesizer_available", HistoricalTrendSynthesizer.__name__ == "HistoricalTrendSynthesizer", HistoricalTrendSynthesizer.__name__)

print()
print("=" * 55)
overall = "PASS" if failed == 0 else "FAIL"
print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")

raise SystemExit(0 if failed == 0 else 1)
