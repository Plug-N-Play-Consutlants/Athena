"""Adapters from Intelligence.Player output into Reasoning player inputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from Reasoning.models.player_profile import PlayerProfile


@dataclass
class PlayerEvidenceItem:
    source_type: str
    summary: str
    confidence: float = 0.5
    metadata: Dict[str, Any] | None = None


def _safe(value: Any) -> str:
    return "" if value is None else str(value).strip()


def build_player_profile_from_evaluation(evaluation: Dict[str, Any], fallback_name: str = "Player") -> PlayerProfile:
    player = evaluation.get("player") if isinstance(evaluation.get("player"), dict) else {}
    return PlayerProfile(
        entity_id=_safe(player.get("player_id") or player.get("nhl_player_id") or evaluation.get("query") or fallback_name),
        name=_safe(player.get("name") or fallback_name),
        position=_safe(player.get("position")) or None,
        team=_safe(player.get("nhl_team")) or None,
    )


def build_player_evidence_from_evaluation(evaluation: Dict[str, Any]) -> List[PlayerEvidenceItem]:
    evidence: List[PlayerEvidenceItem] = []
    confidence = float(evaluation.get("confidence") or 0.5)
    profiles = evaluation.get("profiles") if isinstance(evaluation.get("profiles"), dict) else {}

    for fact in evaluation.get("observed_facts") or []:
        evidence.append(PlayerEvidenceItem("observed_fact", str(fact), confidence, {"source": "player_intelligence"}))

    production = profiles.get("production") if isinstance(profiles.get("production"), dict) else {}
    if production.get("available"):
        band = _safe(production.get("production_band")).replace("_", " ")
        ppg = production.get("points_per_game")
        points = production.get("points")
        games = production.get("games_played")
        summary = f"Production profile: {band or 'available'}"
        if points is not None and games is not None:
            summary += f"; {int(points or 0)} points in {int(games or 0)} games"
        if ppg is not None:
            summary += f"; {float(ppg):.3f} points/game"
        evidence.append(PlayerEvidenceItem("production", summary + ".", confidence, production))

    fantasy = profiles.get("fantasy") if isinstance(profiles.get("fantasy"), dict) else {}
    if fantasy.get("available"):
        evidence.append(PlayerEvidenceItem("fantasy_profile", "Fantasy profile evidence is available.", confidence, fantasy))

    contract = profiles.get("contract") if isinstance(profiles.get("contract"), dict) else {}
    if contract.get("available"):
        yrs = contract.get("years_remaining", "unknown")
        band = contract.get("contract_band", "available")
        evidence.append(PlayerEvidenceItem("contract", f"Contract profile: {band}; years remaining {yrs}.", confidence, contract))

    availability = profiles.get("availability") if isinstance(profiles.get("availability"), dict) else {}
    if availability.get("available"):
        evidence.append(PlayerEvidenceItem("availability", f"Availability: {availability.get('availability_status', 'unknown')} / {availability.get('roster_slot', 'unknown')}.", confidence, availability))

    trajectory = profiles.get("trajectory") if isinstance(profiles.get("trajectory"), dict) else {}
    if trajectory.get("available"):
        evidence.append(PlayerEvidenceItem("trajectory", f"Trajectory classification: {trajectory.get('classification', 'unknown')}.", confidence, trajectory))

    for limitation in evaluation.get("limitations") or []:
        evidence.append(PlayerEvidenceItem("limitation", str(limitation), 0.35, {"source": "player_intelligence"}))

    return evidence
