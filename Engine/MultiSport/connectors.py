"""Offline-safe official multi-sport connector facades."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

from Engine.MultiSport.models import ConnectorCapabilityReport, OfficialConnectorProfile
from Engine.MultiSport.registry import MultiSportRegistry, seed_multi_sport_registry
from Knowledge.Events.normalizer import normalize_event_payload
from Knowledge.Events.models import EventRecord


@dataclass
class MultiSportConnectorResult:
    connector_id: str
    status: str
    events: List[EventRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "status": self.status,
            "events": [event.to_dict() for event in self.events],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


class OfficialMultiSportConnector:
    def __init__(self, profile: OfficialConnectorProfile, registry: MultiSportRegistry | None = None) -> None:
        self.profile = profile
        self.registry = registry or seed_multi_sport_registry()
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def fetch(self, payloads: Iterable[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
        if not self.connected:
            raise RuntimeError("connector is not connected")
        if payloads is not None:
            return list(payloads)
        return [{
            "event_id": f"{self.profile.league_id}_sample_event",
            "event_type": "game_result",
            "sport": self.profile.sport_id,
            "league": self.profile.league_id,
            "subject": self.profile.name,
            "summary": f"Sample official {self.profile.league_id.upper()} event payload.",
            "source_id": self.profile.source_id,
            "source_confidence": self.profile.reliability,
        }]

    def normalize(self, payload: Dict[str, Any]) -> EventRecord:
        payload = dict(payload)
        sport = str(payload.get("sport") or self.profile.sport_id).lower()
        payload["sport"] = sport
        payload.setdefault("league", self.profile.league_id)
        payload.setdefault("source_id", self.profile.source_id)
        payload["event_type"] = self.registry.canonical_event_type(sport, str(payload.get("event_type") or "event"))
        payload.setdefault("source_confidence", self.profile.reliability)
        return normalize_event_payload(payload)

    def run(self, payloads: Iterable[Dict[str, Any]] | None = None) -> MultiSportConnectorResult:
        warnings: List[str] = []
        errors: List[str] = []
        events: List[EventRecord] = []
        status = "success"
        try:
            self.connect()
            for payload in self.fetch(payloads):
                events.append(self.normalize(payload))
        except Exception as exc:
            status = "failure"
            errors.append(str(exc))
        finally:
            self.connected = False
        if not events and not errors:
            status = "warning"
            warnings.append("connector returned no events")
        return MultiSportConnectorResult(self.profile.connector_id, status, events, warnings, errors)


def connector_for_league(league_id: str, registry: MultiSportRegistry | None = None) -> OfficialMultiSportConnector:
    registry = registry or seed_multi_sport_registry()
    matches = registry.connectors_for(league_id=league_id)
    if not matches:
        raise KeyError(f"unknown league connector: {league_id}")
    return OfficialMultiSportConnector(matches[0], registry)


def run_official_connector(league_id: str, payloads: Iterable[Dict[str, Any]] | None = None) -> MultiSportConnectorResult:
    return connector_for_league(league_id).run(payloads)


def connector_capability_report(registry: MultiSportRegistry | None = None) -> ConnectorCapabilityReport:
    registry = registry or seed_multi_sport_registry()
    return ConnectorCapabilityReport(
        version="0.5.3.1.0",
        sports=sorted(registry.sports),
        leagues=sorted(registry.leagues),
        connectors=sorted(registry.connectors),
        network_enabled=False,
        notes=["Official connector scaffolds are offline-safe until live provider credentials are introduced."],
    )
