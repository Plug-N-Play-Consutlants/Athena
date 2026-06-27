"""
Knowledge Readiness Builder

Audits the current Sports Intelligence Engine knowledge layer and identifies
which domains are ready, partial, or missing for downstream intelligence.

This module does not create analysis or recommendations. It documents the
state of available canonical knowledge so the next enrichment steps are clear.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR, RAW_DIR, CONFIGURATION_DIR


OUTPUT_JSON = OUTPUT_DIR / "knowledge_readiness.json"
OUTPUT_CSV = OUTPUT_DIR / "knowledge_readiness.csv"


REQUIRED_OUTPUTS = {
    "league_profile": OUTPUT_DIR / "league_profile.json",
    "league_archetype": OUTPUT_DIR / "league_archetype.json",
    "analysis_profile": OUTPUT_DIR / "analysis_profile.json",
    "player_master": OUTPUT_DIR / "player_master.json",
    "player_profiles": OUTPUT_DIR / "player_profiles.json",
    "player_values": OUTPUT_DIR / "player_values.json",
    "team_profiles": OUTPUT_DIR / "team_profiles.json",
    "player_production": OUTPUT_DIR / "player_production.json",
    "player_identity_map": OUTPUT_DIR / "player_identity_map.json",
    "player_bio": OUTPUT_DIR / "player_bio.json",
    "player_contracts": OUTPUT_DIR / "player_contracts.json",
}

OPTIONAL_RAW_INPUTS = {
    "transactions": RAW_DIR / "transactions.json",
    "historical_transactions": RAW_DIR / "historical_transactions.json",
    "player_stats": RAW_DIR / "player_stats.json",
    "nhl_skater_summary": RAW_DIR / "nhl_skater_summary.json",
    "historical_player_stats": RAW_DIR / "historical_player_stats.json",
    "schedule": RAW_DIR / "schedule.json",
    "injuries": RAW_DIR / "injuries.json",
    "contracts": RAW_DIR / "contracts.json",
    "draft_picks": RAW_DIR / "draft_picks.json",
}

OPTIONAL_OUTPUTS = {
    "draft_picks": OUTPUT_DIR / "draft_picks.json",
    "transaction_history": OUTPUT_DIR / "transaction_history.json",
    "manager_profiles": OUTPUT_DIR / "manager_profiles.json",
    "league_market_profile": OUTPUT_DIR / "league_market_profile.json",
    "player_trends": OUTPUT_DIR / "player_trends.json",
    "relationship_graph": OUTPUT_DIR / "relationship_graph.json",
}


KNOWLEDGE_DOMAINS = [
    {
        "domain": "league_rules",
        "required": ["league_profile", "league_archetype", "analysis_profile"],
        "description": "League format, scoring model, roster continuity, competition model, and selected analysis profile.",
        "impact": "Controls model selection and valuation weighting.",
    },
    {
        "domain": "player_identity",
        "required": ["player_master", "player_profiles", "player_identity_map"],
        "description": "Canonical player identity, position, roster ownership, and scarcity context.",
        "impact": "Supports player valuation, roster construction, and team profiles.",
    },
    {
        "domain": "team_context",
        "required": ["team_profiles"],
        "description": "Aggregated team roster facts and current preliminary organizational value.",
        "impact": "Supports team direction, competitive window, surplus/deficit, and trade fit.",
    },

    {
        "domain": "player_bio",
        "required": ["player_bio", "player_identity_map"],
        "description": "Canonical player age, birthdate, physical profile, handedness, NHL team, and active status.",
        "impact": "Supports dynasty age-curve valuation, risk scoring, team age profile, and future-window analysis.",
    },
    {
        "domain": "player_production",
        "required": ["player_production", "nhl_skater_summary", "player_identity_map"],
        "description": "Current and historical player production, including points, goals, assists, and scoring rates.",
        "impact": "Differentiates actual player value rather than structural placeholders.",
    },
    {
        "domain": "contracts",
        "required": ["player_contracts"],
        "description": "Fantasy contract years, expiry pressure, keeper eligibility, and salary/cap data where applicable.",
        "impact": "Enables contract dynasty valuation, expiry risk, keeper planning, and cap/scenario work.",
    },
    {
        "domain": "draft_assets",
        "required": ["draft_picks"],
        "description": "Canonical future pick ownership and original/current pick owners.",
        "impact": "Supports draft capital valuation, market behavior, trade analysis, and rebuild/contend models.",
    },
    {
        "domain": "transaction_history",
        "required": ["transactions", "historical_transactions"],
        "description": "Trades, waivers, free-agent additions, drops, draft selections, and keeper decisions over time.",
        "impact": "Supports manager behavior, league market intelligence, value tendencies, and engagement analysis.",
    },
    {
        "domain": "manager_behavior",
        "required": ["manager_profiles"],
        "description": "Observable manager tendencies inferred from transactions and roster decisions.",
        "impact": "Supports realistic trade partner identification and decision-support options.",
    },
    {
        "domain": "league_market",
        "required": ["league_market_profile"],
        "description": "League-specific pricing behavior, pick inflation, prospect premium, veteran discount, liquidity, and trade polarization.",
        "impact": "Turns generic valuation into league-specific market intelligence.",
    },
    {
        "domain": "historical_player_trends",
        "required": ["historical_player_stats", "schedule"],
        "description": "Player-vs-opponent trends, recent-vs-historical splits, scoring frequency, and upcoming matchup context.",
        "impact": "Supports weekly start/sit, matchup impact, article generation, and event-driven updates.",
    },
    {
        "domain": "relationship_graph",
        "required": ["relationship_graph"],
        "description": "Player-player, player-coach, player-team, line, power-play, and organizational relationships.",
        "impact": "Supports chemistry, deployment, coaching-change impact, and real-world scenario analysis.",
    },
    {
        "domain": "injury_availability",
        "required": ["injuries"],
        "description": "Current injury status, IR context, availability, and short-term risk.",
        "impact": "Supports lineup, trade risk, replacement value, and event impact analysis.",
    },
]


def _exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def _safe_read(path: Path) -> Any:
    if not _exists(path):
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def _count_records(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("records", "items", "players", "teams", "transactions", "draft_picks"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
        return 1
    return 0


def _source_path_for_key(key: str) -> Path | None:
    if key in REQUIRED_OUTPUTS:
        return REQUIRED_OUTPUTS[key]
    if key in OPTIONAL_RAW_INPUTS:
        return OPTIONAL_RAW_INPUTS[key]
    if key in OPTIONAL_OUTPUTS:
        return OPTIONAL_OUTPUTS[key]
    return None


def _evidence_average(data: Any, evidence_field: str = "evidence_completeness") -> float:
    rows: list[dict[str, Any]] = []
    if isinstance(data, list):
        rows = [row for row in data if isinstance(row, dict)]
    elif isinstance(data, dict):
        for key in ("records", "items", "players", "contracts", "data"):
            value = data.get(key)
            if isinstance(value, list):
                rows = [row for row in value if isinstance(row, dict)]
                break

    if not rows:
        return 0.0

    values = []
    for row in rows:
        try:
            values.append(float(row.get(evidence_field) or 0.0))
        except (TypeError, ValueError):
            values.append(0.0)

    return round(sum(values) / len(values), 3) if values else 0.0


def _source_quality(key: str, path: Path | None) -> dict[str, Any]:
    exists = bool(path and _exists(path))
    data = _safe_read(path) if exists and path else None
    records = _count_records(data) if exists else 0

    # Some enrichment files intentionally exist as placeholders/templates even
    # when the real source data is not available yet. Those should not make a
    # domain appear ready. Contracts are the first example: player_contracts.py
    # creates one placeholder row per player, but evidence_completeness remains 0.
    if key == "player_contracts":
        avg_evidence = _evidence_average(data)
        effective_available = exists and records > 0 and avg_evidence > 0.0
        return {
            "available": effective_available,
            "exists": exists,
            "record_count": records,
            "quality_score": avg_evidence,
            "quality_note": "contract evidence completeness must be greater than 0",
        }

    return {
        "available": exists,
        "exists": exists,
        "record_count": records,
        "quality_score": 1.0 if exists else 0.0,
        "quality_note": "file existence check",
    }


def evaluate_domain(domain: dict[str, Any]) -> dict[str, Any]:
    required = domain["required"]
    source_results = []

    available_count = 0
    total_count = len(required)
    record_count = 0

    for key in required:
        path = _source_path_for_key(key)
        quality = _source_quality(key, path)
        exists = quality["exists"]
        available = quality["available"]
        if available:
            available_count += 1
        record_count += int(quality.get("record_count") or 0)

        source_results.append(
            {
                "source": key,
                "path": str(path) if path else "unknown",
                "exists": exists,
                "available": available,
                "record_count": quality.get("record_count", 0),
                "quality_score": quality.get("quality_score", 0.0),
                "quality_note": quality.get("quality_note", ""),
            }
        )

    readiness_score = round(available_count / total_count, 3) if total_count else 0.0

    if readiness_score >= 1.0:
        status = "ready"
    elif readiness_score > 0.0:
        status = "partial"
    else:
        status = "missing"

    return {
        "domain": domain["domain"],
        "status": status,
        "readiness_score": readiness_score,
        "available_sources": available_count,
        "required_sources": total_count,
        "record_count": record_count,
        "description": domain["description"],
        "impact": domain["impact"],
        "sources": source_results,
    }


def build_knowledge_readiness() -> dict[str, Any]:
    log_header("Knowledge Readiness Builder")

    results = [evaluate_domain(domain) for domain in KNOWLEDGE_DOMAINS]

    ready = [item for item in results if item["status"] == "ready"]
    partial = [item for item in results if item["status"] == "partial"]
    missing = [item for item in results if item["status"] == "missing"]

    readiness = {
        "summary": {
            "domains_total": len(results),
            "domains_ready": len(ready),
            "domains_partial": len(partial),
            "domains_missing": len(missing),
            "overall_readiness_score": round(
                sum(item["readiness_score"] for item in results) / len(results), 3
            )
            if results
            else 0.0,
        },
        "domains": results,
        "next_recommended_enrichment": [
            "contracts",
            "transaction_history",
            "draft_assets",
            "historical_player_trends",
        ],
    }

    write_json(OUTPUT_JSON, readiness)
    write_readiness_csv(OUTPUT_CSV, results)

    log(f"Domains Ready: {len(ready)}")
    log(f"Domains Partial: {len(partial)}")
    log(f"Domains Missing: {len(missing)}")
    log(f"Overall Readiness: {readiness['summary']['overall_readiness_score']}")

    log_section("Ready Domains")
    for item in ready:
        log(f"  - {item['domain']}")

    log_section("Partial / Missing Domains")
    for item in partial + missing:
        log(f"  - {item['domain']}: {item['status']} ({item['readiness_score']})")

    log_section("Recommended Next Enrichment")
    for item in readiness["next_recommended_enrichment"]:
        log(f"  - {item}")

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")

    return readiness


def write_readiness_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "domain",
        "status",
        "readiness_score",
        "available_sources",
        "required_sources",
        "record_count",
        "description",
        "impact",
    ]

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


if __name__ == "__main__":
    build_knowledge_readiness()
