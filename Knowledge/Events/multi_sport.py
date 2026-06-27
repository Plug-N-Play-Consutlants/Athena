"""Knowledge-facing multi-sport connector registry helpers."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from Engine.MultiSport.connectors import connector_capability_report, run_official_connector
from Engine.MultiSport.registry import MultiSportRegistry, seed_multi_sport_registry


def multi_sport_event_framework_summary() -> Dict[str, Any]:
    registry = seed_multi_sport_registry()
    report = connector_capability_report(registry)
    return {
        "version": report.version,
        "sports": report.sports,
        "leagues": report.leagues,
        "connectors": report.connectors,
        "network_enabled": report.network_enabled,
        "registry": registry.to_dict(),
    }


def acquire_sample_multi_sport_events(leagues: Iterable[str] | None = None) -> List[Dict[str, Any]]:
    targets = list(leagues or ["nhl", "nfl", "nba", "mlb", "uefa"])
    events: List[Dict[str, Any]] = []
    for league in targets:
        result = run_official_connector(league)
        events.extend(event.to_dict() for event in result.events)
    return events
