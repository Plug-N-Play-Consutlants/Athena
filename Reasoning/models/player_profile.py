from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlayerProfile:
    entity_id: str
    name: str
    position: Optional[str] = None
    team: Optional[str] = None
    age: Optional[float] = None
    handedness: Optional[str] = None
    fantasy_team: Optional[str] = None
    nhl_player_id: Optional[str] = None
    strengths: List[str] = field(default_factory=list)

    @classmethod
    def from_evaluation(cls, evaluation: Dict[str, Any]) -> "PlayerProfile":
        player = evaluation.get("player") if isinstance(evaluation.get("player"), dict) else {}
        return cls(
            entity_id=str(player.get("player_id") or player.get("nhl_player_id") or evaluation.get("query") or ""),
            name=str(player.get("name") or evaluation.get("query") or "Unknown Player"),
            position=player.get("position"),
            team=player.get("nhl_team"),
            fantasy_team=player.get("fantasy_team"),
            nhl_player_id=player.get("nhl_player_id"),
        )
