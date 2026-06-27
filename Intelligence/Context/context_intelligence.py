"""Athena Context Intelligence & Evaluation Profiles.

Sprint 4B.2 introduces one shared evidence layer interpreted by multiple
consumer profiles. It does not invent missing facts. It classifies which
context dimensions matter for public, fantasy, projection, and odds-style
scenarios, then produces bounded notes from the evidence already present in
an evaluation object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

from Core.json_utils import write_json

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EVALUATION_PROFILES: Dict[str, Dict[str, Any]] = {
    "public": {
        "label": "Public analysis",
        "purpose": "Explain the player or situation clearly using verified public/fantasy-neutral evidence.",
        "weights": {
            "production": 0.18,
            "achievement": 0.18,
            "trajectory": 0.16,
            "team_context": 0.14,
            "competition": 0.10,
            "usage": 0.12,
            "availability": 0.08,
            "market": 0.04,
        },
    },
    "fantasy": {
        "label": "Fantasy analysis",
        "purpose": "Assess ownership, roster fit, scoring fit, contracts, schedule, and future utility.",
        "weights": {
            "production": 0.24,
            "trajectory": 0.18,
            "fantasy_context": 0.18,
            "contract": 0.14,
            "usage": 0.10,
            "availability": 0.10,
            "competition": 0.04,
            "achievement": 0.02,
        },
    },
    "projection": {
        "label": "Projection analysis",
        "purpose": "Evaluate likely forward path using production, age/trajectory, role, health, and contextual shifts.",
        "weights": {
            "trajectory": 0.24,
            "production": 0.22,
            "usage": 0.14,
            "availability": 0.12,
            "team_context": 0.10,
            "competition": 0.08,
            "achievement": 0.06,
            "fantasy_context": 0.04,
        },
    },
    "odds": {
        "label": "Odds / probability analysis",
        "purpose": "Assess event likelihood from matchup, usage, recent form, splits, schedule, line/special-team context, and opponent resistance.",
        "weights": {
            "production": 0.16,
            "recent_form": 0.18,
            "usage": 0.16,
            "opponent_context": 0.16,
            "line_synergy": 0.12,
            "special_teams": 0.10,
            "availability": 0.08,
            "achievement": 0.04,
        },
        "disclaimer": "Athena can support probability-oriented analysis, but this is not gambling advice and does not guarantee outcomes.",
    },
}

SCENARIO_KEYWORDS = {
    "odds": ["odds", "bet", "prop", "anytime", "score tonight", "goal tonight", "assist tonight", "point tonight", "probability", "chances"],
    "projection": ["project", "projection", "future", "next season", "contender", "trajectory", "trend", "decline", "bounce back", "prime"],
    "fantasy": ["fantasy", "keeper", "contract", "roster", "pickup", "draft", "waiver", "start", "sit"],
    "public": ["who is", "tell me about", "explain", "public"],
}

CONTEXT_DIMENSIONS = {
    "production": "Current production and scoring split evidence.",
    "achievement": "Career awards, milestones, captaincy, franchise role, and historical distinctions.",
    "trajectory": "Multi-season direction, age curve, rebound/decline context, and future path.",
    "usage": "Line deployment, power-play role, time-on-ice, and assignment context.",
    "availability": "Injury, IR/LTIR, roster status, and health reliability.",
    "team_context": "Coaching, team environment, linemates, role, and organizational conditions.",
    "competition": "Division/conference/opponent strength and difficulty of environment.",
    "opponent_context": "Specific opponent tendencies, matchup suppression, goaltender/defensive resistance.",
    "line_synergy": "Evidence that linemate combinations change player production or event probability.",
    "special_teams": "Power-play/penalty-kill environment and special-team opportunity.",
    "recent_form": "Rolling-window form, streaks, shot/attempt volume, and short-term rhythm.",
    "fantasy_context": "League scoring, roster fit, ownership, scarcity, keeper and market context.",
    "contract": "Fantasy or real-world contract runway where available.",
    "market": "Perception, availability, trade market, and manager behavior context.",
}


def _safe_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def infer_evaluation_profile(question: str = "", default: str = "public") -> str:
    """Infer the consumer profile from the question without changing evidence."""
    q = _safe_lower(question)
    for profile in ("odds", "projection", "fantasy", "public"):
        if any(term in q for term in SCENARIO_KEYWORDS[profile]):
            return profile
    return default if default in EVALUATION_PROFILES else "public"


def _profile_dict(player_evaluation: Dict[str, Any], key: str) -> Dict[str, Any]:
    profiles = player_evaluation.get("profiles") if isinstance(player_evaluation.get("profiles"), dict) else {}
    value = profiles.get(key)
    return value if isinstance(value, dict) else {}


def _evidence_availability(player_evaluation: Dict[str, Any]) -> Dict[str, bool]:
    production = _profile_dict(player_evaluation, "production")
    fantasy = _profile_dict(player_evaluation, "fantasy")
    contract = _profile_dict(player_evaluation, "contract")
    availability = _profile_dict(player_evaluation, "availability")
    trajectory = _profile_dict(player_evaluation, "trajectory")
    base = player_evaluation.get("evidence_presence") if isinstance(player_evaluation.get("evidence_presence"), dict) else {}

    return {
        "production": bool(production.get("available") or base.get("production")),
        "achievement": False,
        "trajectory": bool(trajectory.get("available") or production.get("available")),
        "usage": False,
        "availability": bool(availability.get("available") or base.get("status")),
        "team_context": False,
        "competition": False,
        "opponent_context": False,
        "line_synergy": False,
        "special_teams": False,
        "recent_form": False,
        "fantasy_context": bool(fantasy.get("available") or base.get("fantasy")),
        "contract": bool(contract.get("available") or base.get("contract")),
        "market": False,
    }


def _dimension_notes(player_evaluation: Dict[str, Any], availability: Dict[str, bool]) -> List[str]:
    notes: List[str] = []
    player = player_evaluation.get("player") if isinstance(player_evaluation.get("player"), dict) else {}
    production = _profile_dict(player_evaluation, "production")
    contract = _profile_dict(player_evaluation, "contract")
    fantasy = _profile_dict(player_evaluation, "fantasy")
    name = player.get("name") or player_evaluation.get("query") or "This player"

    if availability.get("production"):
        goals = production.get("goals")
        assists = production.get("assists")
        points = production.get("points")
        ppg = production.get("points_per_game")
        notes.append(f"Production evidence exists for {name}: {points} points, {goals} goals, {assists} assists, {ppg} points/game.")
    if availability.get("trajectory"):
        notes.append("Trajectory can be described from current production band, but multi-season trend evidence is not yet available.")
    if availability.get("fantasy_context"):
        ft = fantasy.get("fantasy_team") or player.get("fantasy_team") or "a fantasy roster"
        notes.append(f"Fantasy context is available through {ft}.")
    if availability.get("contract"):
        notes.append(f"Contract runway evidence is available: {contract.get('years_remaining')} years remaining, {contract.get('contract_band')}.")
    if availability.get("availability"):
        av = _profile_dict(player_evaluation, "availability")
        notes.append(f"Availability evidence exists: {av.get('availability_status')} / {av.get('roster_slot')}.")

    missing_context = [
        "achievement" if not availability.get("achievement") else None,
        "usage" if not availability.get("usage") else None,
        "team_context" if not availability.get("team_context") else None,
        "competition" if not availability.get("competition") else None,
        "recent_form" if not availability.get("recent_form") else None,
        "opponent_context" if not availability.get("opponent_context") else None,
        "line_synergy" if not availability.get("line_synergy") else None,
        "special_teams" if not availability.get("special_teams") else None,
    ]
    missing_context = [m for m in missing_context if m]
    if missing_context:
        notes.append("Important context dimensions are not yet populated: " + ", ".join(missing_context) + ".")
    return notes


def evaluate_context(player_evaluation: Dict[str, Any], profile: str = "public", question: str = "") -> Dict[str, Any]:
    """Evaluate which context dimensions matter for the selected profile."""
    profile_key = profile if profile in EVALUATION_PROFILES else infer_evaluation_profile(question, default="public")
    spec = EVALUATION_PROFILES[profile_key]
    availability = _evidence_availability(player_evaluation)

    weighted_dimensions: List[Dict[str, Any]] = []
    usable_weight = 0.0
    total_weight = 0.0
    for dimension, weight in spec["weights"].items():
        total_weight += float(weight)
        available = bool(availability.get(dimension, False))
        if available:
            usable_weight += float(weight)
        weighted_dimensions.append({
            "dimension": dimension,
            "label": CONTEXT_DIMENSIONS.get(dimension, dimension),
            "weight": float(weight),
            "available": available,
            "status": "available" if available else "missing",
        })

    context_readiness = round(usable_weight / total_weight, 3) if total_weight else 0.0
    limitations = [
        f"{row['dimension']} context is not yet available for this profile."
        for row in weighted_dimensions
        if not row["available"]
    ]
    if profile_key == "odds":
        limitations.append(spec.get("disclaimer", "Odds-oriented analysis requires careful disclaimers."))
        limitations.append("Athena does not yet calculate event probabilities from sportsbook lines or live betting markets.")

    return {
        "profile": profile_key,
        "profile_label": spec["label"],
        "purpose": spec["purpose"],
        "status": "available" if context_readiness >= 0.5 else "partial",
        "context_readiness": context_readiness,
        "weighted_dimensions": weighted_dimensions,
        "available_dimensions": [row["dimension"] for row in weighted_dimensions if row["available"]],
        "missing_dimensions": [row["dimension"] for row in weighted_dimensions if not row["available"]],
        "notes": _dimension_notes(player_evaluation, availability),
        "limitations": limitations,
    }


def apply_context_profile(player_evaluation: Dict[str, Any], profile: str = "public", question: str = "") -> Dict[str, Any]:
    """Attach context interpretation to a player evaluation without changing base facts."""
    context = evaluate_context(player_evaluation, profile=profile, question=question)
    result = dict(player_evaluation)
    result["context_profile"] = context
    result["evaluation_profile"] = context["profile"]
    result["scenario"] = {
        "profile": context["profile"],
        "label": context["profile_label"],
        "context_changes_output": True,
        "evidence_graph_shared": True,
    }

    base_eval = str(result.get("evaluation") or "Athena completed a bounded player evaluation.")
    if context["profile"] == "odds":
        prefix = "In odds/probability context, the same player evidence must be weighted toward matchup, recent form, usage, line synergy, and special teams. "
    elif context["profile"] == "fantasy":
        prefix = "In fantasy context, the same player evidence is weighted toward scoring fit, roster fit, contract runway, availability, and future utility. "
    elif context["profile"] == "projection":
        prefix = "In projection context, the same player evidence is weighted toward trajectory, role, health, and contextual change. "
    else:
        prefix = "In public analysis context, the same player evidence is explained with career, production, and situational context. "

    result["contextual_evaluation"] = prefix + base_eval
    result.setdefault("limitations", [])
    result["limitations"] = list(result.get("limitations") or []) + context.get("limitations", [])[:6]
    dev = result.get("developer") if isinstance(result.get("developer"), dict) else {}
    dev["context_profile"] = context
    dev["modules_executed"] = list(dev.get("modules_executed", [])) + ["ContextIntelligence.apply_context_profile"]
    result["developer"] = dev
    return result


def build_context_evaluation(player_evaluation: Dict[str, Any], profile: str = "public", question: str = "", project_root: Path = PROJECT_ROOT) -> Dict[str, Any]:
    result = apply_context_profile(player_evaluation, profile=profile, question=question)
    safe_entity = re.sub(r"[^a-z0-9]+", "_", _safe_lower((result.get("player") or {}).get("name") if isinstance(result.get("player"), dict) else result.get("query")))[:60] or "player"
    out_json = project_root / "Output" / f"context_intelligence_{safe_entity}_{result.get('evaluation_profile')}.json"
    report = project_root / "Reports" / f"context_intelligence_{safe_entity}_{result.get('evaluation_profile')}.txt"
    write_json(out_json, result)
    lines = [
        "Context Intelligence",
        "====================",
        f"Profile: {result.get('evaluation_profile')}",
        f"Title: {result.get('title')}",
        f"Context readiness: {result.get('context_profile', {}).get('context_readiness')}",
        "",
        "Contextual Evaluation",
        "---------------------",
        str(result.get("contextual_evaluation")),
        "",
        "Available Dimensions",
        "--------------------",
    ]
    lines.extend([f"- {item}" for item in result.get("context_profile", {}).get("available_dimensions", [])])
    lines.extend(["", "Missing Dimensions", "------------------"])
    lines.extend([f"- {item}" for item in result.get("context_profile", {}).get("missing_dimensions", [])])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    result["context_reports"] = {"json": str(out_json), "text": str(report)}
    return result
