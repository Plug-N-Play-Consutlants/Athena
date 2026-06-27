"""
Athena Sports Intelligence Platform

Epic 4D.4

Historical Intelligence Engine
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict

from Core.json_utils import write_json
from Core.project_paths import OUTPUT_DIR

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from .graph_bridge import build_historical_graph_bridge
from .intelligence import HISTORICAL_INTELLIGENCE_VERSION, HistoricalIntelligenceSynthesizer

HISTORICAL_INTELLIGENCE_FILE = "historical_intelligence.json"
HISTORICAL_INTELLIGENCE_SUMMARY_FILE = "historical_intelligence_signal_summary.json"


def build_historical_intelligence_signals(project_root: Path | None = None) -> dict[str, Any]:
    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"

    bridge = build_historical_graph_bridge(project_root)
    nodes = bridge.get("nodes", {}).get("nodes", [])

    by_entity: DefaultDict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        if not isinstance(node, dict):
            continue
        entity_id = str(node.get("entity_id") or "unknown")
        by_entity[entity_id].append(node)

    intelligence = []
    for entity_id, entity_nodes in sorted(by_entity.items()):
        intelligence.extend(HistoricalIntelligenceSynthesizer.synthesize_entity(entity_id, entity_nodes))

    by_pattern: dict[str, int] = {}
    by_direction: dict[str, int] = {}
    for signal in intelligence:
        by_pattern[signal.pattern_type.value] = by_pattern.get(signal.pattern_type.value, 0) + 1
        by_direction[signal.direction.value] = by_direction.get(signal.direction.value, 0) + 1

    payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version": historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version": historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version": historical_version.HISTORICAL_ENGINE_VERSION,
        "historical_intelligence_version": HISTORICAL_INTELLIGENCE_VERSION,
        "signal_count": len(intelligence),
        "signals": [signal.to_dict() for signal in intelligence],
    }

    summary = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_intelligence_version": HISTORICAL_INTELLIGENCE_VERSION,
        "historical_engine_version": historical_version.HISTORICAL_ENGINE_VERSION,
        "status": "ready" if intelligence else "empty",
        "source_node_count": len(nodes),
        "entity_count": len(by_entity),
        "signal_count": len(intelligence),
        "patterns": by_pattern,
        "directions": by_direction,
        "intelligence_file": str(output_dir / HISTORICAL_INTELLIGENCE_FILE),
    }

    write_json(output_dir / HISTORICAL_INTELLIGENCE_FILE, payload)
    write_json(output_dir / HISTORICAL_INTELLIGENCE_SUMMARY_FILE, summary)

    return {"summary": summary, "intelligence": payload, "source_bridge": bridge.get("summary", {})}


def historical_intelligence_for_entity(entity_id: str, *, project_root: Path | None = None, limit: int = 20) -> dict[str, Any]:
    result = build_historical_intelligence_signals(project_root)
    signals = [
        signal for signal in result["intelligence"].get("signals", [])
        if isinstance(signal, dict) and signal.get("entity_id") == entity_id
    ][: max(1, int(limit or 20))]

    return {
        "status": "available" if signals else "empty",
        "athena_version": core_version.ATHENA_VERSION,
        "historical_intelligence_version": HISTORICAL_INTELLIGENCE_VERSION,
        "entity_id": entity_id,
        "signal_count": len(signals),
        "signals": signals,
        "known_gaps": [] if signals else ["No historical intelligence signals are available for the requested entity."],
    }
