"""Multi-sport connector models for Athena Event Intelligence."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

MULTI_SPORT_FRAMEWORK_VERSION = "0.5.3.1.0"


@dataclass(frozen=True)
class SportProfile:
    sport_id: str
    name: str
    default_league_id: str
    event_types: List[str]
    identity_domains: List[str] = field(default_factory=lambda: ["player", "team", "competition"])
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LeagueProfile:
    league_id: str
    sport_id: str
    name: str
    region: str = "global"
    official_source_id: str = ""
    primary_connector_type: str = "official_api"
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfficialConnectorProfile:
    connector_id: str
    sport_id: str
    league_id: str
    source_id: str
    name: str
    connector_type: str = "official_api"
    supported_event_types: List[str] = field(default_factory=list)
    network_enabled: bool = False
    reliability: float = 0.90
    authority: str = "official"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SportEventTaxonomy:
    sport_id: str
    canonical_event_types: List[str]
    sport_specific_aliases: Dict[str, str] = field(default_factory=dict)

    def canonicalize(self, event_type: str) -> str:
        key = (event_type or "event").strip().lower().replace(" ", "_")
        return self.sport_specific_aliases.get(key, key if key in self.canonical_event_types else "event")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConnectorCapabilityReport:
    version: str
    sports: List[str]
    leagues: List[str]
    connectors: List[str]
    network_enabled: bool
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
