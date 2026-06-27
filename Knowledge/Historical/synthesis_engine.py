"""
Athena Sports Intelligence Platform

Epic 4D.3d

Historical Trend Synthesis Engine
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict

from Core.json_utils import write_json
from Core.project_paths import OUTPUT_DIR

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from .comparison_engine import build_historical_comparisons
from .synthesis import HistoricalTrendSynthesizer
from .synthesis_models import HistoricalTrendSignal


HISTORICAL_TREND_SIGNALS_FILE = "historical_trend_signals.json"
HISTORICAL_TREND_SYNTHESIS_SUMMARY_FILE = "historical_trend_synthesis_summary.json"


def build_historical_trend_synthesis(
    project_root: Path | None = None,
) -> dict[str, Any]:

    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"

    comparison_result = build_historical_comparisons(project_root)

    comparisons = comparison_result["comparisons"].get("comparisons", [])

    signals = HistoricalTrendSynthesizer.synthesize(comparisons)

    by_direction: DefaultDict[str, int] = defaultdict(int)
    by_strength: DefaultDict[str, int] = defaultdict(int)
    by_group: DefaultDict[str, int] = defaultdict(int)
    by_entity: DefaultDict[str, int] = defaultdict(int)

    for signal in signals:
        by_direction[signal.direction.value] += 1
        by_strength[signal.strength.value] += 1
        by_group[signal.comparison_group] += 1
        by_entity[signal.entity_id] += 1

    signals_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version": historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version": historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version": historical_version.HISTORICAL_ENGINE_VERSION,
        "historical_synthesis_version": historical_version.HISTORICAL_SYNTHESIS_VERSION,
        "signal_count": len(signals),
        "signals": [signal.to_dict() for signal in signals],
    }

    summary = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version": historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version": historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version": historical_version.HISTORICAL_ENGINE_VERSION,
        "historical_synthesis_version": historical_version.HISTORICAL_SYNTHESIS_VERSION,
        "status": "ready" if signals else "insufficient_data",
        "comparison_count": len(comparisons),
        "signal_count": len(signals),
        "entities_with_signals": len(by_entity),
        "directions": dict(by_direction),
        "strengths": dict(by_strength),
        "comparison_groups": dict(by_group),
        "signals_file": str(output_dir / HISTORICAL_TREND_SIGNALS_FILE),
    }

    write_json(output_dir / HISTORICAL_TREND_SIGNALS_FILE, signals_payload)
    write_json(output_dir / HISTORICAL_TREND_SYNTHESIS_SUMMARY_FILE, summary)

    return {
        "summary": summary,
        "signals": signals_payload,
        "comparisons": comparison_result["comparisons"],
        "skipped": comparison_result["skipped"],
    }


def historical_trend_signals_for_entity(
    entity_id: str,
    *,
    project_root: Path | None = None,
    limit: int = 20,
) -> dict[str, Any]:

    result = build_historical_trend_synthesis(project_root)

    signals = [
        signal
        for signal in result["signals"].get("signals", [])
        if signal.get("entity_id") == entity_id
    ]

    signals = sorted(
        signals,
        key=lambda signal: (
            -float(signal.get("confidence", 0.0) or 0.0),
            signal.get("comparison_group") or "",
            signal.get("id") or "",
        ),
    )[: max(1, int(limit or 20))]

    return {
        "status": "available" if signals else "empty",
        "athena_version": core_version.ATHENA_VERSION,
        "historical_engine_version": historical_version.HISTORICAL_ENGINE_VERSION,
        "historical_synthesis_version": historical_version.HISTORICAL_SYNTHESIS_VERSION,
        "entity_id": entity_id,
        "signal_count": len(signals),
        "signals": signals,
        "known_gaps": [] if signals else [
            "No historical trend signals are currently available for the requested entity."
        ],
    }


if __name__ == "__main__":
    result = build_historical_trend_synthesis()
    summary = result["summary"]
    print("Athena Historical Trend Synthesis")
    print("=================================")
    print(f"Status: {summary['status']}")
    print(f"Comparisons: {summary['comparison_count']}")
    print(f"Signals: {summary['signal_count']}")
    print(f"Entities: {summary['entities_with_signals']}")
