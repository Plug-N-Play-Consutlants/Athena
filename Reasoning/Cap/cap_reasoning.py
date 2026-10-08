"""Executable NHL salary-cap reasoning over canonical Knowledge state.

This layer applies constraints. It does not acquire facts and does not infer
missing payroll adjustments. Special CBA treatments remain unresolved until
both the applicable provision and the required factual inputs are canonical.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple

ADJUSTMENT_CLASSES = (
    "long_term_injury_relief",
    "retained_salary",
    "buried_salary",
    "performance_bonus_and_overage",
    "buyout_or_termination_charges",
    "other_cba_cap_adjustments",
)

@dataclass(frozen=True)
class CapDetermination:
    team_id: str
    team_name: str
    league_year: str
    as_of: str
    cba_environment_id: str
    status: str
    known_payroll: int | None
    lower_limit: int
    upper_limit: int
    headroom: int | None
    floor_margin: int | None
    rules_applied: Tuple[str, ...]
    unresolved_inputs: Tuple[str, ...]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_team_cap_state(team_state: Any, league_context: Any, *, verified_cap_charge_total: int | None = None,
                            resolved_adjustment_classes: Tuple[str, ...] = ()) -> CapDetermination:
    """Apply executable cap constraints to canonical team/economic state.

    A numeric compliance/headroom result is permitted only when the team state
    declares a complete verified ledger and all adjustment classes are resolved.
    `verified_cap_charge_total` is an injected canonical total for future ledger
    implementations; partial contract sums are never substituted for it.
    """
    unresolved = []
    if not bool(getattr(team_state, "aggregate_permitted", False)):
        unresolved.extend(("complete_registered_spc", "complete_current_roster", "verified_team_cap_charge_total"))
    resolved = set(resolved_adjustment_classes or ())
    unresolved.extend(x for x in ADJUSTMENT_CLASSES if x not in resolved)
    unresolved = tuple(dict.fromkeys(unresolved))

    base_rules = (
        "effective_dated_league_year",
        "applicable_cba_environment",
        "team_payroll_lower_limit",
        "team_payroll_upper_limit",
        "complete_ledger_required_for_numeric_determination",
    )
    if verified_cap_charge_total is None or unresolved:
        explanation = (
            f"The applicable {league_context.league_year} NHL upper limit is ${league_context.upper_limit/1_000_000:.1f}M "
            f"under {league_context.cba_label}. Athena cannot determine {team_state.team_name}'s actual cap usage, "
            "cap space, or compliance from a partial ledger. The missing contract/roster/adjustment inputs must be "
            "resolved before numeric cap reasoning is permitted."
        )
        return CapDetermination(
            team_id=team_state.team_id, team_name=team_state.team_name, league_year=league_context.league_year,
            as_of=team_state.as_of, cba_environment_id=league_context.cba_environment_id, status="indeterminate_incomplete_ledger",
            known_payroll=None, lower_limit=league_context.lower_limit, upper_limit=league_context.upper_limit,
            headroom=None, floor_margin=None, rules_applied=base_rules, unresolved_inputs=unresolved, explanation=explanation)

    total = int(verified_cap_charge_total)
    headroom = int(league_context.upper_limit) - total
    floor_margin = total - int(league_context.lower_limit)
    if total > int(league_context.upper_limit):
        status = "above_upper_limit"
    elif total < int(league_context.lower_limit):
        status = "below_lower_limit"
    else:
        status = "within_team_payroll_range"
    explanation = (
        f"Verified cap charges are ${total/1_000_000:.2f}M against a ${league_context.lower_limit/1_000_000:.1f}M "
        f"to ${league_context.upper_limit/1_000_000:.1f}M Team Payroll Range. The resulting determination is {status.replace('_',' ')}."
    )
    return CapDetermination(
        team_id=team_state.team_id, team_name=team_state.team_name, league_year=league_context.league_year,
        as_of=team_state.as_of, cba_environment_id=league_context.cba_environment_id, status=status,
        known_payroll=total, lower_limit=league_context.lower_limit, upper_limit=league_context.upper_limit,
        headroom=headroom, floor_margin=floor_margin, rules_applied=base_rules + ("verified_cap_charge_total_test",),
        unresolved_inputs=(), explanation=explanation)
