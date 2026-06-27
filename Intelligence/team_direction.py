"""
Team Direction Intelligence Builder.

Classifies each fantasy organization's preliminary competitive direction using
canonical team profiles and the active analysis profile. This module belongs in
Intelligence: it reasons over Knowledge outputs, but it does not make autonomous
recommendations or prescribe manager actions.

Current limitation: direction is production-backed but not yet contract-, age-,
transaction-, or market-aware. Labels are therefore intentionally preliminary.
"""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
from typing import Any

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR


TEAM_PROFILES_PATH = OUTPUT_DIR / "team_profiles.json"
LEAGUE_PROFILE_PATH = OUTPUT_DIR / "league_profile.json"
ANALYSIS_PROFILE_PATH = OUTPUT_DIR / "analysis_profile.json"
KNOWLEDGE_READINESS_PATH = OUTPUT_DIR / "knowledge_readiness.json"

OUTPUT_JSON = OUTPUT_DIR / "team_direction.json"
OUTPUT_CSV = OUTPUT_DIR / "team_direction.csv"

POSITION_ORDER = ["C", "LW", "RW", "D"]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_optional_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return read_json(path)
    except Exception:
        return default


def _round(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _average(values: list[float]) -> float:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return 0.0
    return _round(sum(clean_values) / len(clean_values))


def _percentile_rank(value: float, values: list[float]) -> float:
    """Return a deterministic 0-100 percentile where higher is better."""
    clean_values = sorted([_safe_float(item) for item in values])
    if not clean_values:
        return 0.0
    if len(clean_values) == 1:
        return 100.0

    below = sum(1 for item in clean_values if item < value)
    equal = sum(1 for item in clean_values if item == value)
    percentile = ((below + (0.5 * equal)) / len(clean_values)) * 100
    return _round(percentile)


def _extract_dimension(team: dict[str, Any], key: str) -> float:
    dimensions = team.get("valuation_dimensions", {})
    if isinstance(dimensions, dict):
        return _safe_float(dimensions.get(key))
    return 0.0


def _depth_balance_score(team: dict[str, Any]) -> float:
    """
    Score positional coverage from 0-100.

    This is intentionally conservative. It rewards teams that cover required
    starter slots at each position but does not over-reward excessive depth,
    because surplus analysis belongs in later trade/market modules.
    """
    position_depth = team.get("position_depth", {})
    if not isinstance(position_depth, dict):
        return 0.0

    scores: list[float] = []
    for position in POSITION_ORDER:
        row = position_depth.get(position, {}) or {}
        coverage_ratio = _safe_float(row.get("coverage_ratio"))
        if coverage_ratio <= 0:
            scores.append(0.0)
            continue
        capped = min(coverage_ratio, 1.25)
        scores.append((capped / 1.25) * 100)

    return _round(mean(scores)) if scores else 0.0


def _knowledge_readiness_score(knowledge_readiness: dict[str, Any]) -> float:
    """Read overall readiness across old and current readiness schemas."""
    if not isinstance(knowledge_readiness, dict):
        return 0.0

    direct = (
        knowledge_readiness.get("overall_readiness")
        or knowledge_readiness.get("overall_readiness_score")
        or knowledge_readiness.get("readiness")
        or knowledge_readiness.get("score")
    )
    if direct not in (None, ""):
        return _safe_float(direct)

    summary = knowledge_readiness.get("summary", {})
    if isinstance(summary, dict):
        return _safe_float(
            summary.get("overall_readiness_score")
            or summary.get("overall_readiness")
            or summary.get("readiness")
            or summary.get("score")
        )

    return 0.0


def _missing_direction_domains(knowledge_readiness: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not isinstance(knowledge_readiness, dict):
        return missing

    domains = knowledge_readiness.get("domains", {})

    if isinstance(domains, dict):
        for name, row in domains.items():
            if isinstance(row, dict):
                status = _safe_str(row.get("status")).lower()
                if status in {"missing", "partial"}:
                    missing.append(_safe_str(name))
        return [item for item in missing if item]

    if isinstance(domains, list):
        for row in domains:
            if not isinstance(row, dict):
                continue
            status = _safe_str(row.get("status")).lower()
            if status in {"missing", "partial"}:
                missing.append(_safe_str(row.get("domain") or row.get("name")))

    return [item for item in missing if item]


def _classify_direction(power_percentile: float, knowledge_score: float) -> str:
    """
    Produce cautious preliminary labels.

    We do not classify true contender/rebuilder states until the engine has
    contracts, age curve, transaction history, and draft-pick value online.
    """
    if power_percentile >= 80:
        return "preliminary_contender"
    if power_percentile >= 60:
        return "competitive"
    if power_percentile >= 35:
        return "middle_tier"
    if knowledge_score < 0.65:
        return "needs_enrichment"
    return "retool_watch"


def _direction_summary(direction: str) -> str:
    summaries = {
        "preliminary_contender": "Current production-backed roster value places this team near the top of the league.",
        "competitive": "Current production-backed roster value places this team above the league midpoint.",
        "middle_tier": "Current production-backed roster value places this team in the middle of the league.",
        "needs_enrichment": "Current value is below league median, but contracts, age, draft capital, and market behavior are required before assigning a stronger strategic label.",
        "retool_watch": "Current value and enriched strategic indicators suggest this team should be monitored for retooling signals.",
    }
    return summaries.get(direction, "Direction requires additional enrichment.")


def _build_direction_record(
    team: dict[str, Any],
    all_team_values: list[float],
    all_average_values: list[float],
    league_average_total: float,
    league_average_player_value: float,
    league_profile: dict[str, Any],
    analysis_profile: dict[str, Any],
    knowledge_readiness: dict[str, Any],
) -> dict[str, Any]:
    total_value = _safe_float(team.get("total_asset_value"))
    average_asset_value = _safe_float(team.get("average_asset_value"))
    current_average = _extract_dimension(team, "current_average")
    future_average = _extract_dimension(team, "future_average")
    scarcity_average = _extract_dimension(team, "scarcity_average")
    confidence = _safe_float(team.get("confidence"))
    evidence_completeness = _safe_float(team.get("evidence_completeness"))
    depth_balance = _depth_balance_score(team)
    knowledge_score = _knowledge_readiness_score(knowledge_readiness)

    total_percentile = _percentile_rank(total_value, all_team_values)
    average_percentile = _percentile_rank(average_asset_value, all_average_values)

    power_score = _round(
        (total_percentile * 0.55)
        + (average_percentile * 0.25)
        + (depth_balance * 0.20)
    )

    direction = _classify_direction(power_score, knowledge_score)

    value_delta = _round(total_value - league_average_total)
    average_player_delta = _round(average_asset_value - league_average_player_value)

    direction_confidence = _round(
        min(
            0.95,
            (confidence * 0.55)
            + (evidence_completeness * 0.20)
            + (knowledge_score * 0.25),
        )
    )

    missing_domains = _missing_direction_domains(knowledge_readiness)
    direction_limitations = [
        "Direction is preliminary because contracts, age curves, transaction history, manager behavior, and market pricing are not fully enriched yet.",
        "This module surfaces decision context; it does not prescribe autonomous roster moves.",
    ]

    evidence = [
        f"Total asset value {total_value} versus league average {league_average_total}.",
        f"Average player value {average_asset_value} versus league average {league_average_player_value}.",
        f"Power score {power_score} from total value percentile, average value percentile, and positional depth balance.",
        f"Team valuation confidence {confidence} and evidence completeness {evidence_completeness}.",
        f"Knowledge readiness score {knowledge_score}.",
    ]

    return {
        "team_id": team.get("team_id"),
        "team_name": team.get("team_name"),
        "league_id": _safe_str(league_profile.get("league_id")),
        "season": league_profile.get("season"),
        "sport": _safe_str(league_profile.get("sport")),
        "model_key": _safe_str(analysis_profile.get("model_key")),
        "direction": direction,
        "direction_summary": _direction_summary(direction),
        "power_score": power_score,
        "power_percentile": power_score,
        "total_asset_value": _round(total_value),
        "league_average_total_asset_value": _round(league_average_total),
        "value_delta_vs_league_average": value_delta,
        "average_asset_value": _round(average_asset_value),
        "league_average_player_value": _round(league_average_player_value),
        "average_player_delta_vs_league_average": average_player_delta,
        "depth_balance_score": depth_balance,
        "current_average": _round(current_average),
        "future_average": _round(future_average),
        "scarcity_average": _round(scarcity_average),
        "roster_size": _safe_int(team.get("roster_size")),
        "confidence": direction_confidence,
        "source_team_confidence": _round(confidence),
        "knowledge_readiness": _round(knowledge_score),
        "missing_direction_domains": missing_domains,
        "top_assets": team.get("top_assets", [])[:5],
        "evidence": evidence,
        "limitations": direction_limitations,
        "manager_discretion_required": True,
    }


def build_team_direction() -> list[dict[str, Any]]:
    log_header("Team Direction Intelligence Builder")

    team_profiles = _read_optional_json(TEAM_PROFILES_PATH, [])
    league_profile = _read_optional_json(LEAGUE_PROFILE_PATH, {})
    analysis_profile = _read_optional_json(ANALYSIS_PROFILE_PATH, {})
    knowledge_readiness = _read_optional_json(KNOWLEDGE_READINESS_PATH, {})

    if not isinstance(team_profiles, list):
        raise ValueError("team_profiles.json must contain a list of team profile records.")

    all_team_values = [_safe_float(team.get("total_asset_value")) for team in team_profiles]
    all_average_values = [_safe_float(team.get("average_asset_value")) for team in team_profiles]
    league_average_total = _average(all_team_values)
    league_average_player_value = _average(all_average_values)

    direction_records = [
        _build_direction_record(
            team=team,
            all_team_values=all_team_values,
            all_average_values=all_average_values,
            league_average_total=league_average_total,
            league_average_player_value=league_average_player_value,
            league_profile=league_profile,
            analysis_profile=analysis_profile,
            knowledge_readiness=knowledge_readiness,
        )
        for team in team_profiles
        if isinstance(team, dict)
    ]

    direction_records.sort(
        key=lambda row: (
            _safe_float(row.get("power_score")),
            _safe_float(row.get("total_asset_value")),
            _safe_str(row.get("team_name")),
        ),
        reverse=True,
    )

    write_json(OUTPUT_JSON, direction_records)
    write_team_direction_csv(OUTPUT_CSV, direction_records)

    counts: dict[str, int] = {}
    for record in direction_records:
        direction = _safe_str(record.get("direction"))
        counts[direction] = counts.get(direction, 0) + 1

    knowledge_score = _knowledge_readiness_score(knowledge_readiness)

    log(f"League: {_safe_str(league_profile.get('league_name') or league_profile.get('name'))} ({league_profile.get('season')})")
    log(f"Sport: {_safe_str(league_profile.get('sport'))}")
    log(f"Model Key: {_safe_str(analysis_profile.get('model_key'))}")
    log(f"Teams Classified: {len(direction_records)}")
    log(f"Knowledge Readiness: {knowledge_score}")
    log(f"Average Direction Confidence: {_average([_safe_float(row.get('confidence')) for row in direction_records])}")

    log_section("Direction Counts")
    for direction, count in sorted(counts.items()):
        log(f"  {direction}: {count}")

    log_section("League Power Map")
    for record in direction_records[:10]:
        log(
            f"  {record.get('team_name')}: "
            f"{record.get('direction')} | "
            f"power {record.get('power_score')} | "
            f"value {record.get('total_asset_value')} | "
            f"confidence {record.get('confidence')}"
        )

    log_section("Important Limitation")
    log("  Team direction is production-backed but still preliminary.")
    log("  Contracts, age curves, transactions, manager behavior, and market pricing remain future enrichments.")

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")

    return direction_records


def write_team_direction_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "team_id",
        "team_name",
        "league_id",
        "season",
        "sport",
        "model_key",
        "direction",
        "power_score",
        "total_asset_value",
        "league_average_total_asset_value",
        "value_delta_vs_league_average",
        "average_asset_value",
        "average_player_delta_vs_league_average",
        "depth_balance_score",
        "current_average",
        "future_average",
        "scarcity_average",
        "roster_size",
        "confidence",
        "knowledge_readiness",
        "manager_discretion_required",
    ]

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow({field: record.get(field) for field in fieldnames})


if __name__ == "__main__":
    build_team_direction()
