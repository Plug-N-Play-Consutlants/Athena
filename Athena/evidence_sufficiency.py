"""Evidence acquisition accountability for team investigations.

A missing source is not evidence of a weakness. The ledger distinguishes
attempted retrieval, unavailable coverage, and conclusions actually supported.
"""
from __future__ import annotations
from typing import Any


def audit_team_evidence(evidence: dict[str, Any], *, needs_roster: bool = True) -> dict[str, Any]:
    sources = set(evidence.get("sources") or [])
    missing = set(evidence.get("missing") or [])
    checks = {
        "season_performance": ("nhl_club_stats_season", "verified_current_season_club_stats"),
        "team_results": ("nhl_official_current_standings", "verified_current_standings"),
        "recent_games": ("nhl_official_completed_games", "verified_recent_completed_games"),
    }
    if needs_roster:
        checks.update({
            "current_roster": ("nhl_current_roster", "verified_current_roster"),
            "canonical_economics": ("canonical_team_economic_state", "canonical_team_economic_context"),
        })
    stages = {}
    for key, (source, missing_key) in checks.items():
        stages[key] = {"state": "acquired" if source in sources else "not_acquired",
                       "source": source, "missing_marker": missing_key if missing_key in missing else None}
    economics = evidence.get("economics") or {}
    if needs_roster:
        coverage = economics.get("contract_coverage")
        stages["complete_contract_ledger"] = {
            "state": "verified" if economics.get("aggregate_permitted") is True else "incomplete",
            "covered_contract_count": coverage if isinstance(coverage, int) and not isinstance(coverage, bool) else None,
            "source": "canonical_contracts_pack_not_live_nhl_roster",
            "remediation": "Acquire independently verified contracts and reconcile effective dates, team rights and cap adjustments; do not count roster players as verified SPCs.",
        }
    return {"schema": "athena.team_evidence_sufficiency.v1", "stages": stages,
            "acquired": sum(v["state"] in ("acquired", "verified") for v in stages.values()),
            "total": len(stages), "causal_diagnosis_verified": False,
            "contract_completeness_verified": bool(needs_roster and economics.get("aggregate_permitted") is True)}
