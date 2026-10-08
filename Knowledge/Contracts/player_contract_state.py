"""Canonical effective-dated NHL player contract state.

This module is deliberately separate from Knowledge/player_contracts.py, which
represents fantasy/Fantrax contract rules and values. A PlayerContractState is a
professional-league evidence object and must retain provenance for every record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Dict, Tuple

_PACK = Path(__file__).resolve().parents[1] / "Packs" / "NHL" / "contracts" / "canonical_contracts.json"


def _day(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


@dataclass(frozen=True)
class PlayerContractState:
    contract_id: str
    player_entity_id: str
    player_name: str
    team_id: str
    team_name: str
    signed_on: str
    effective_from: str
    effective_to: str
    start_league_year: str
    term_years: int
    total_value: int
    aav: int
    contract_level: str
    expiry_status: str
    evidence_status: str
    provenance: Tuple[Dict[str, Any], ...]
    limitations: Tuple[str, ...]

    def active_on(self, as_of: str | date) -> bool:
        target = _day(as_of)
        return _day(self.effective_from) <= target <= _day(self.effective_to)

    def cap_share(self, as_of: str | date) -> float:
        """AAV as share of that date's league upper limit, not team cap usage."""
        from Knowledge.Economics.league_season_context import resolve_league_season_context
        economic = resolve_league_season_context(as_of=as_of)
        return self.aav / economic.upper_limit

    def to_dict(self, *, as_of: str | date | None = None) -> Dict[str, Any]:
        payload = asdict(self)
        payload["provenance"] = [dict(item) for item in self.provenance]
        payload["limitations"] = list(self.limitations)
        if as_of is not None:
            payload["active_on_as_of"] = self.active_on(as_of)
            payload["cap_share_of_upper_limit"] = round(self.cap_share(as_of), 6) if self.active_on(as_of) else None
        return payload


def all_player_contract_states() -> Tuple[PlayerContractState, ...]:
    payload = json.loads(_PACK.read_text(encoding="utf-8"))
    return tuple(PlayerContractState(
        contract_id=row["contract_id"], player_entity_id=row["player_entity_id"],
        player_name=row["player_name"], team_id=row["team_id"], team_name=row["team_name"],
        signed_on=row["signed_on"], effective_from=row["effective_from"], effective_to=row["effective_to"],
        start_league_year=row["start_league_year"], term_years=int(row["term_years"]),
        total_value=int(row["total_value"]), aav=int(row["aav"]), contract_level=row["contract_level"],
        expiry_status=row["expiry_status"], evidence_status=row["evidence_status"],
        provenance=tuple(row.get("provenance", [])), limitations=tuple(row.get("limitations", [])),
    ) for row in payload.get("contracts", []))


def resolve_player_contract_state(*, player_entity_id: str = "", player_name: str = "", as_of: str | date | None = None) -> PlayerContractState:
    matches = [item for item in all_player_contract_states()
               if (player_entity_id and item.player_entity_id == player_entity_id)
               or (player_name and item.player_name.casefold() == player_name.casefold())]
    if not matches:
        raise LookupError("No canonical NHL contract evidence is available for that player.")
    if as_of is not None:
        active = [item for item in matches if item.active_on(as_of)]
        if len(active) == 1:
            return active[0]
        if not active:
            raise LookupError("Canonical contract evidence exists, but not for the requested effective date.")
    if len(matches) != 1:
        raise LookupError("Multiple contract states match; an effective date is required.")
    return matches[0]
