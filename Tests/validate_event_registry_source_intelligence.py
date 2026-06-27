"""Validation suite for Athena 0.5.1.1.x Event Registry & Source Intelligence."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_EPIC, RELEASE_HOTFIX, RELEASE_NAME, RELEASE_PATCH, RELEASE_SPRINT, VERSION_SCHEMA
from Knowledge.Events import (
    EVENT_TYPES,
    EventRegistry,
    SourceRegistry,
    bind_event_to_graph,
    canonical_event_type,
    normalize_event_payload,
    score_source_confidence,
    seed_event_registry,
    seed_source_registry,
    source_registry_summary,
)


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Event Registry & Source Intelligence Validation")
    print("=" * 64)
    checks: list[bool] = []

    checks.append(report("version is Epic 5 Sprint 1 Patch 1 or later", (ATHENA_VERSION.startswith("0.5.1.") or ATHENA_VERSION.startswith("0.5.2.")) and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("version uses locked schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix" and bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", ATHENA_VERSION)), VERSION_SCHEMA))
    checks.append(report("release metadata identifies Epic 5 Sprint 1", RELEASE_EPIC == "5" and RELEASE_HOTFIX.isdigit(), RELEASE_NAME))

    source_registry = seed_source_registry()
    checks.append(report("source registry object created", isinstance(source_registry, SourceRegistry), type(source_registry).__name__))
    checks.append(report("source registry seeds official/trusted/provider sources", len(source_registry.sources) >= 7 and len(source_registry.primary_fact_sources()) >= 5, f"sources={len(source_registry.sources)} primary={len(source_registry.primary_fact_sources())}"))
    checks.append(report("source scoring prioritizes official sources", source_registry.get("nhl_api").trust_score > source_registry.get("opinion_article").trust_score, f"nhl_api={source_registry.get('nhl_api').trust_score:.3f}; opinion={source_registry.get('opinion_article').trust_score:.3f}"))
    checks.append(report("opinion sources are not primary facts", not source_registry.get("opinion_article").is_primary_fact_source(), "opinion_article deprioritized"))
    checks.append(report("source confidence scoring returns bounded values", 0.0 <= score_source_confidence("nhl_api", 0.6) <= 1.0 and score_source_confidence("nhl_api", 0.6) > score_source_confidence("opinion_article", 0.6), "bounded and source-weighted"))

    event_registry = seed_event_registry()
    checks.append(report("event registry object created", isinstance(event_registry, EventRegistry), type(event_registry).__name__))
    checks.append(report("event registry receives source profiles", event_registry.source_count() == len(source_registry.sources), f"sources={event_registry.source_count()}"))
    checks.append(report("event taxonomy includes expanded categories", {"trade", "free_agent_signing", "contract_extension", "waiver", "claim", "recall", "assignment", "injury", "return", "suspension", "retirement", "coaching_change", "schedule_change", "game_result", "transaction"}.issubset(set(EVENT_TYPES)), str(EVENT_TYPES)))
    checks.append(report("event type aliases canonicalize", canonical_event_type("signing") == "free_agent_signing" and canonical_event_type("extension") == "contract_extension" and canonical_event_type("unknown weird thing") == "event", "aliases stable"))

    payload = {
        "event_type": "trade",
        "sport": "nhl",
        "subject": "Example Player",
        "summary": "Example Player was traded from Team A to Team B.",
        "entities": ["Example Player", "Team A", "Team B"],
        "entity_links": [
            {"entity_id": "player_example", "label": "Example Player", "role": "moved_asset", "entity_type": "player", "confidence": 0.9},
            {"entity_id": "team_a", "label": "Team A", "role": "from_team", "entity_type": "team", "confidence": 0.85},
            {"entity_id": "team_b", "label": "Team B", "role": "to_team", "entity_type": "team", "confidence": 0.85},
        ],
        "evidence": [
            {"source_id": "league_feed", "title": "Official trade notice", "observed_at": "2026-06-23T12:00:00+00:00", "confidence": 0.9},
            {"source_id": "trusted_newswire", "title": "Newswire trade confirmation", "observed_at": "2026-06-23T12:02:00+00:00", "confidence": 0.8},
        ],
        "published_at": "2026-06-23T12:00:00+00:00",
    }
    event = normalize_event_payload(payload)
    checks.append(report("normalizer creates stable event id", event.event_id.startswith("evt_") and len(event.event_id) == 20, event.event_id))
    checks.append(report("normalizer preserves canonical event facts", event.event_type == "trade" and event.sport == "nhl" and event.subject == "Example Player", event.summary))
    checks.append(report("normalizer attaches source-weighted evidence", len(event.evidence) == 2 and all(item.confidence >= 0.7 for item in event.evidence), str([item.to_dict() for item in event.evidence])))
    checks.append(report("normalizer creates entity links", len(event.entity_links) >= 3 and {link.role for link in event.entity_links}.issuperset({"moved_asset", "from_team", "to_team"}), str([link.to_dict() for link in event.entity_links])))
    checks.append(report("knowledge model avoids conclusions", not hasattr(event, "conclusion") and not hasattr(event, "recommendation"), "Reasoning owns conclusions"))

    graph, binding = bind_event_to_graph(event)
    graph_data = graph.to_dict()
    checks.append(report("event graph creates event node", binding.event_node_id in graph.nodes and graph.nodes[binding.event_node_id].type == "event", binding.event_node_id))
    checks.append(report("event graph binds sources", len(binding.source_node_ids) == 2 and all(node_id in graph.nodes for node_id in binding.source_node_ids), str(binding.source_node_ids)))
    checks.append(report("event graph binds entities", len(binding.entity_node_ids) >= 3 and all(node_id in graph.nodes for node_id in binding.entity_node_ids), str(binding.entity_node_ids)))
    checks.append(report("event graph binds evidence", len(binding.evidence_node_ids) == 2 and all(node_id in graph.nodes for node_id in binding.evidence_node_ids), str(binding.evidence_node_ids)))
    checks.append(report("event graph relationship types are reasoning-ready", {rel.type for rel in graph.relationships.values()}.issuperset({"reported_by", "supported_by", "participated_in"}), str([rel.type for rel in graph.relationships.values()])))
    checks.append(report("event graph is non-empty and serializable", graph_data["node_count"] >= 8 and graph_data["relationship_count"] >= 7, f"nodes={graph_data['node_count']} rels={graph_data['relationship_count']}"))

    summary = source_registry_summary()
    checks.append(report("registry summary exposes preferred source types", "official_api" in summary.get("preferred_source_types", []) and "provider_feed" in summary.get("preferred_source_types", []), str(summary.get("preferred_source_types"))))
    checks.append(report("registry summary marks opinion deprioritization", summary.get("opinion_sources_deprioritized") is True, str(summary)))

    failed = [ok for ok in checks if not ok]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
