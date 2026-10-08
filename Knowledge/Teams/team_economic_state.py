"""Canonical NHL team roster/economic state with completeness gating."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Dict, Tuple

_PACK = Path(__file__).resolve().parents[1] / "Packs" / "NHL" / "teams" / "canonical_team_states.json"

@dataclass(frozen=True)
class TeamEconomicState:
    team_id: str
    team_name: str
    abbreviation: str
    league_year: str
    as_of: str
    roster_evidence_status: str
    economic_completeness: str
    aggregate_cap_usage_status: str
    roster_observations: Tuple[Dict[str, Any], ...]
    provenance: Tuple[Dict[str, Any], ...]
    limitations: Tuple[str, ...]

    @property
    def aggregate_permitted(self) -> bool:
        return self.aggregate_cap_usage_status == "complete_verified_ledger"

    def covered_contracts(self) -> Tuple[Any, ...]:
        from Knowledge.Contracts.player_contract_state import all_player_contract_states
        target = date.fromisoformat(self.as_of)
        return tuple(c for c in all_player_contract_states() if c.team_id == self.team_id and c.active_on(target))

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["roster_observations"] = [dict(x) for x in self.roster_observations]
        payload["provenance"] = [dict(x) for x in self.provenance]
        covered = self.covered_contracts()
        payload["canonical_contract_coverage"] = {
            "covered_players": [c.player_name for c in covered],
            "covered_contract_count": len(covered),
            "aggregate_permitted": self.aggregate_permitted,
        }
        return payload

def all_team_economic_states() -> Tuple[TeamEconomicState, ...]:
    payload=json.loads(_PACK.read_text(encoding="utf-8"))
    return tuple(TeamEconomicState(
        team_id=r["team_id"], team_name=r["team_name"], abbreviation=r["abbreviation"],
        league_year=r["league_year"], as_of=r["as_of"], roster_evidence_status=r["roster_evidence_status"],
        economic_completeness=r["economic_completeness"], aggregate_cap_usage_status=r["aggregate_cap_usage_status"],
        roster_observations=tuple(r.get("roster_observations",[])), provenance=tuple(r.get("provenance",[])),
        limitations=tuple(r.get("limitations",[]))) for r in payload.get("teams",[]))

def resolve_team_economic_state(*, team_id: str = "", team_name: str = "", abbreviation: str = "") -> TeamEconomicState:
    keys={str(team_id).casefold(),str(team_name).casefold(),str(abbreviation).casefold()}-{""}
    matches=[t for t in all_team_economic_states() if keys & {t.team_id.casefold(),t.team_name.casefold(),t.abbreviation.casefold()}]
    if len(matches)!=1:
        raise LookupError("No single canonical NHL team economic state is available for that team.")
    return matches[0]
