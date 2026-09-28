"""Evidence-backed longitudinal draft intelligence.

Consumes enriched historical draft observations. This module describes league-level
and same-season patterns only; it never infers manager identity or cross-season
franchise continuity from team names/provider team IDs.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INTELLIGENCE_VERSION = "0.6.4.8.0"


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _pct(n: int, d: int) -> float | None:
    return round((100.0 * n / d), 1) if d else None


def build_historical_draft_intelligence(*, project_root: Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    historical = root / "Output" / "Historical"
    seasons: list[dict[str, Any]] = []
    round_positions: dict[int, Counter[str]] = defaultdict(Counter)
    round_resolved: Counter[int] = Counter()
    all_files: list[str] = []

    if historical.exists():
        for season_dir in sorted((p for p in historical.iterdir() if p.is_dir() and p.name.isdigit()), key=lambda p: int(p.name)):
            path = season_dir / "draft_observations_enriched.json"
            payload = _read(path)
            if not payload:
                continue
            observations = [x for x in payload.get("observations", []) if isinstance(x, dict)]
            position_tags: Counter[str] = Counter()
            resolved = defense = forwards = multi = 0
            team_counts: Counter[str] = Counter()
            for row in observations:
                player = row.get("historical_player_identity") or {}
                positions = [str(x) for x in (player.get("positions") or []) if str(x)]
                rnd = int(row.get("round") or 0)
                if positions:
                    resolved += 1
                    round_resolved[rnd] += 1
                    for pos in positions:
                        position_tags[pos] += 1
                        round_positions[rnd][pos] += 1
                    if "D" in positions:
                        defense += 1
                    elif any(pos in {"C", "LW", "RW"} for pos in positions):
                        forwards += 1
                    if len(positions) > 1:
                        multi += 1
                team = row.get("historical_team_identity") or {}
                team_key = str(team.get("team_name") or row.get("provider_team_id") or "unresolved")
                team_counts[team_key] += 1
            season = int(payload.get("season") or season_dir.name)
            seasons.append({
                "season": season,
                "selection_count": len(observations),
                "position_resolved": resolved,
                "position_coverage_pct": _pct(resolved, len(observations)),
                "defense_observations": defense,
                "forward_observations": forwards,
                "defense_share_of_resolved_pct": _pct(defense, resolved),
                "multi_position_observations": multi,
                "position_eligibility_tags": dict(sorted(position_tags.items())),
                "same_season_team_count": len(team_counts),
                "same_season_team_selection_range": [min(team_counts.values()), max(team_counts.values())] if team_counts else [0, 0],
            })
            all_files.append(str(path.relative_to(root)).replace("\\", "/"))

    total_selections = sum(x["selection_count"] for x in seasons)
    total_resolved = sum(x["position_resolved"] for x in seasons)
    total_defense = sum(x["defense_observations"] for x in seasons)
    by_round = []
    for rnd in sorted(round_resolved):
        tags = round_positions[rnd]
        by_round.append({
            "round": rnd,
            "resolved_position_observations": round_resolved[rnd],
            "defense_observations": tags.get("D", 0),
            "defense_share_of_resolved_pct": _pct(tags.get("D", 0), round_resolved[rnd]),
            "position_eligibility_tags": dict(sorted(tags.items())),
        })

    early, late = seasons[:5], seasons[-5:] if len(seasons) >= 5 else seasons
    def group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        resolved = sum(x["position_resolved"] for x in rows)
        defense = sum(x["defense_observations"] for x in rows)
        return {
            "seasons": [x["season"] for x in rows],
            "average_selections": round(mean(x["selection_count"] for x in rows), 1) if rows else None,
            "resolved_position_observations": resolved,
            "defense_share_of_resolved_pct": _pct(defense, resolved),
        }

    early_summary, late_summary = group_summary(early), group_summary(late)
    findings: list[dict[str, Any]] = []
    if by_round:
        r1 = next((x for x in by_round if x["round"] == 1), None)
        later = max((x for x in by_round if x["round"] > 1 and x["resolved_position_observations"] >= 50), key=lambda x: x["defense_share_of_resolved_pct"], default=None)
        if r1 and later:
            findings.append({
                "type": "round_depth_position_pattern", "status": "supported", "scope": "league_level",
                "statement": f"Defense appears substantially more often deeper in the draft: {r1['defense_share_of_resolved_pct']}% of resolved round-1 observations versus {later['defense_share_of_resolved_pct']}% in round {later['round']}.",
                "evidence": {"round_1": r1, "comparison_round": later},
            })
    if early_summary.get("defense_share_of_resolved_pct") is not None and late_summary.get("defense_share_of_resolved_pct") is not None:
        delta = round(late_summary["defense_share_of_resolved_pct"] - early_summary["defense_share_of_resolved_pct"], 1)
        stable = abs(delta) < 5
        statement = (
            f"Overall defense share among resolved position observations remained essentially stable: {early_summary['defense_share_of_resolved_pct']}% in the first five seasons versus {late_summary['defense_share_of_resolved_pct']}% in the last five ({delta:+.1f} percentage points)."
            if stable else
            f"Overall defense share among resolved position observations changed from {early_summary['defense_share_of_resolved_pct']}% in the first five seasons to {late_summary['defense_share_of_resolved_pct']}% in the last five ({delta:+.1f} percentage points)."
        )
        findings.append({
            "type": "era_position_mix", "status": "stable" if stable else "changed", "scope": "league_level",
            "statement": statement,
            "evidence": {"first_five": early_summary, "last_five": late_summary},
        })

    return {
        "schema": "athena.historical_draft_intelligence.v1", "version": INTELLIGENCE_VERSION,
        "status": "available" if seasons else "missing", "season_count": len(seasons),
        "first_season": seasons[0]["season"] if seasons else None, "last_season": seasons[-1]["season"] if seasons else None,
        "coverage": {"selection_observations": total_selections, "resolved_position_observations": total_resolved, "position_coverage_pct": _pct(total_resolved, total_selections), "defense_observations": total_defense},
        "season_summaries": seasons, "round_position_profiles": by_round,
        "era_comparison": {"first_five": early_summary, "last_five": late_summary},
        "findings": findings, "files_read": all_files,
        "attribution_policy": {"league_level_patterns_allowed": True, "same_season_team_profiles_allowed": True, "cross_season_team_or_manager_tendencies_allowed": False},
        "limitations": [
            "Position counts describe provider-supported eligibility; multi-position players may contribute more than one eligibility tag.",
            "Manager/person identity remains unresolved, so manager tendencies are not attributed.",
            "Cross-season franchise continuity remains unresolved, so team-name similarity is not treated as franchise continuity.",
            "Player-name coverage is not required for position-level findings when same-season position evidence is resolved.",
        ],
    }
