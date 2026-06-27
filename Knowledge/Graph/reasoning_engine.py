"""Epic 4C.3 graph reasoning engine for Athena.

The reasoning engine ranks graph evidence by relevance for a consumer query. It
sits above raw graph traversal and evidence chains: the graph stores connected
facts, the chain engine explains traceability, and this module decides which
paths are most relevant for a requested reasoning context.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from Core.json_utils import write_json
from Core.project_paths import OUTPUT_DIR
from Core.version import ATHENA_VERSION
from Knowledge.Graph.canonical_graph import CanonicalContextGraph, utc_now_iso
from Knowledge.Graph.chain_engine import (
    DEFAULT_NODE_TYPE_WEIGHTS,
    DEFAULT_RELATIONSHIP_WEIGHTS,
    build_evidence_chain,
)
from Knowledge.Graph.evidence_chain import load_graph

REASONING_VERSION = "4C.3-reasoning-engine"

DEFAULT_CONTEXT_PROFILES: Dict[str, Dict[str, Any]] = {
    "fantasy": {
        "relationship_preferences": {
            "has_contract": 1.18,
            "rostered_by": 1.14,
            "plays_for": 1.08,
            "member_of": 0.86,
            "uses_rules_from": 0.72,
        },
        "node_type_preferences": {
            "player": 1.0,
            "contract": 1.16,
            "team": 1.08,
            "league": 0.92,
            "knowledge_pack": 0.78,
        },
        "default_focus": ["production", "deployment", "availability", "schedule", "contract", "fantasy_value"],
    },
    "public": {
        "relationship_preferences": {
            "plays_for": 1.16,
            "member_of": 1.08,
            "uses_rules_from": 1.02,
            "has_contract": 0.84,
            "rostered_by": 0.72,
        },
        "node_type_preferences": {
            "player": 1.0,
            "team": 1.12,
            "league": 1.08,
            "knowledge_pack": 1.0,
            "contract": 0.8,
        },
        "default_focus": ["biography", "team", "rules", "achievements", "historical_context"],
    },
    "projection": {
        "relationship_preferences": {
            "plays_for": 1.12,
            "rostered_by": 1.06,
            "has_contract": 1.0,
            "member_of": 0.92,
            "uses_rules_from": 0.7,
        },
        "node_type_preferences": {
            "player": 1.0,
            "team": 1.1,
            "contract": 0.98,
            "league": 0.9,
            "knowledge_pack": 0.72,
        },
        "default_focus": ["trend", "usage", "schedule", "opponent", "availability", "production"],
    },
    "odds": {
        "relationship_preferences": {
            "plays_for": 1.1,
            "member_of": 1.0,
            "rostered_by": 0.82,
            "has_contract": 0.72,
            "uses_rules_from": 0.7,
        },
        "node_type_preferences": {
            "player": 1.0,
            "team": 1.12,
            "league": 0.98,
            "contract": 0.7,
            "knowledge_pack": 0.72,
        },
        "default_focus": ["market", "schedule", "opponent", "team_quality", "availability"],
    },
}

FOCUS_HINTS: Dict[str, Dict[str, float]] = {
    "contract": {"has_contract": 1.45, "contract": 1.45},
    "keeper": {"has_contract": 1.35, "contract": 1.35},
    "team": {"plays_for": 1.25, "rostered_by": 1.18, "team": 1.22},
    "roster": {"rostered_by": 1.35, "team": 1.15},
    "fantasy_value": {"rostered_by": 1.25, "has_contract": 1.18, "team": 1.1},
    "rules": {"uses_rules_from": 1.35, "governed_by": 1.3, "knowledge_pack": 1.35, "rule": 1.4},
    "schedule": {"scheduled_in": 1.45, "schedule": 1.45, "game": 1.3},
    "coach": {"coached_by": 1.45, "coach": 1.45},
    "achievement": {"earned": 1.45, "achievement": 1.45},
    "public": {"plays_for": 1.18, "member_of": 1.1, "knowledge_pack": 1.04},
}


@dataclass(frozen=True)
class ReasoningQuery:
    entity_id: str
    context_profile: str = "fantasy"
    focus: Tuple[str, ...] = ()
    max_depth: int = 3
    traversal: str = "weighted"
    limit: int = 8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "context_profile": self.context_profile,
            "focus": list(self.focus),
            "max_depth": self.max_depth,
            "traversal": self.traversal,
            "limit": self.limit,
        }


def _clamp(value: Any, default: float = 0.75) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0.0, min(1.0, numeric))


def _multiplier(value: Any, default: float = 1.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0.05, min(2.5, numeric))


def _profile(name: str) -> Dict[str, Any]:
    return DEFAULT_CONTEXT_PROFILES.get(str(name or "").strip().lower(), DEFAULT_CONTEXT_PROFILES["fantasy"])


def _normalize_focus(focus: Optional[Iterable[str]], context_profile: str) -> List[str]:
    supplied = [str(x or "").strip().lower() for x in (focus or []) if str(x or "").strip()]
    if supplied:
        return supplied
    return list(_profile(context_profile).get("default_focus") or [])


def _effective_weights(context_profile: str, focus: Iterable[str]) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, Any]]:
    profile = _profile(context_profile)
    relationship_weights = dict(DEFAULT_RELATIONSHIP_WEIGHTS)
    node_type_weights = dict(DEFAULT_NODE_TYPE_WEIGHTS)
    applied: Dict[str, Any] = {"context_profile": context_profile, "focus": list(focus), "focus_hints": {}}

    for rel_type, base in list(relationship_weights.items()):
        relationship_weights[rel_type] = _clamp(base * _multiplier(profile.get("relationship_preferences", {}).get(rel_type, 1.0)))
    for node_type, base in list(node_type_weights.items()):
        node_type_weights[node_type] = _clamp(base * _multiplier(profile.get("node_type_preferences", {}).get(node_type, 1.0)))

    for item in focus:
        hints = FOCUS_HINTS.get(str(item or "").lower(), {})
        if not hints:
            continue
        applied["focus_hints"][item] = hints
        for key, multiplier in hints.items():
            if key in relationship_weights:
                relationship_weights[key] = _clamp(relationship_weights[key] * _multiplier(multiplier))
            if key in node_type_weights:
                node_type_weights[key] = _clamp(node_type_weights[key] * _multiplier(multiplier))

    return relationship_weights, node_type_weights, applied


def _path_terminal_type(path: Dict[str, Any]) -> str:
    steps = path.get("steps") if isinstance(path.get("steps"), list) else []
    if not steps:
        return ""
    last = steps[-1]
    return str(last.get("to", {}).get("type") or "")


def _path_relationship_types(path: Dict[str, Any]) -> List[str]:
    return [str(step.get("relationship_type") or "") for step in path.get("steps", []) if isinstance(step, dict)]


def _focus_match_score(path: Dict[str, Any], focus: Iterable[str]) -> float:
    focus_items = set(str(x or "").lower() for x in focus)
    rel_types = set(_path_relationship_types(path))
    terminal_type = _path_terminal_type(path)
    score = 0.0
    for item in focus_items:
        hints = FOCUS_HINTS.get(item, {})
        if not hints:
            continue
        if any(key in rel_types for key in hints):
            score += 0.08
        if terminal_type in hints:
            score += 0.08
    return min(0.25, score)


def _traversal_rank_bonus(path: Dict[str, Any], traversal: str) -> float:
    depth = max(1, int(path.get("depth") or 1))
    if traversal == "breadth_first":
        return 0.12 / depth
    if traversal == "depth_first":
        return min(0.12, depth * 0.035)
    return 0.0


def _rank_paths(paths: List[Dict[str, Any]], focus: Iterable[str], traversal: str) -> List[Dict[str, Any]]:
    ranked = []
    for idx, path in enumerate(paths):
        confidence = _clamp(path.get("confidence"), 0.0)
        base_score = _clamp(path.get("score"), confidence)
        relevance = _clamp(base_score + _focus_match_score(path, focus) + _traversal_rank_bonus(path, traversal), base_score)
        item = dict(path)
        item["rank"] = idx + 1
        item["relevance_score"] = round(relevance, 4)
        item["reasoning_tags"] = sorted(set(_path_relationship_types(path) + [_path_terminal_type(path)]))
        ranked.append(item)
    if traversal == "depth_first":
        ranked.sort(key=lambda p: (int(p.get("depth") or 0), p.get("relevance_score", 0), p.get("confidence", 0)), reverse=True)
    elif traversal == "breadth_first":
        ranked.sort(key=lambda p: (-int(p.get("depth") or 999), p.get("relevance_score", 0), p.get("confidence", 0)), reverse=True)
    else:
        ranked.sort(key=lambda p: (p.get("relevance_score", 0), p.get("confidence", 0)), reverse=True)
    for idx, path in enumerate(ranked, start=1):
        path["rank"] = idx
    return ranked


def _known_gaps(chain: Dict[str, Any], ranked_paths: List[Dict[str, Any]], focus: Iterable[str]) -> List[str]:
    gaps = list(chain.get("known_limitations") or [])
    tags = {tag for path in ranked_paths for tag in path.get("reasoning_tags", [])}
    for item in focus:
        hints = set(FOCUS_HINTS.get(str(item or "").lower(), {}).keys())
        if hints and not (hints & tags):
            gaps.append(f"No direct graph evidence matched focus '{item}' within the requested traversal depth.")
    if not ranked_paths:
        gaps.append("No ranked reasoning paths were available for this query.")
    # deterministic de-duplication
    deduped: List[str] = []
    for gap in gaps:
        if gap not in deduped:
            deduped.append(gap)
    return deduped


def build_reasoning_package(
    entity_id: str,
    *,
    context_profile: str = "fantasy",
    focus: Optional[Iterable[str]] = None,
    max_depth: int = 3,
    traversal: str = "weighted",
    limit: int = 8,
    project_root: Path | None = None,
) -> Dict[str, Any]:
    """Return an ordered reasoning package for Scout and Intelligence consumers."""
    normalized_traversal = str(traversal or "weighted").strip().lower()
    if normalized_traversal not in {"weighted", "breadth_first", "depth_first"}:
        normalized_traversal = "weighted"
    normalized_profile = str(context_profile or "fantasy").strip().lower()
    focus_items = _normalize_focus(focus, normalized_profile)
    max_depth = max(1, min(5, int(max_depth or 3)))
    limit = max(1, min(50, int(limit or 8)))

    graph = load_graph(project_root)
    if entity_id not in graph.nodes:
        return {
            "status": "not_found",
            "athena_version": ATHENA_VERSION,
            "reasoning_version": REASONING_VERSION,
            "query": ReasoningQuery(entity_id, normalized_profile, tuple(focus_items), max_depth, normalized_traversal, limit).to_dict(),
            "confidence": 0.0,
            "question": "No reasoning package was built because the requested graph entity was not found.",
            "relevant_evidence": [],
            "reasoning_paths": [],
            "conclusion": "Requested entity is absent from the canonical context graph.",
            "known_gaps": ["No graph node exists for the requested entity."],
        }

    relationship_weights, node_type_weights, applied = _effective_weights(normalized_profile, focus_items)
    chain = build_evidence_chain(
        entity_id,
        max_depth=max_depth,
        project_root=project_root,
        relationship_weights=relationship_weights,
        node_type_weights=node_type_weights,
        limit=max(limit * 3, limit),
    )
    paths = chain.get("paths") if isinstance(chain.get("paths"), list) else []
    ranked_paths = _rank_paths(paths, focus_items, normalized_traversal)[:limit]
    confidence = round(sum(_clamp(p.get("relevance_score"), 0.0) for p in ranked_paths) / len(ranked_paths), 4) if ranked_paths else _clamp(chain.get("confidence"), 0.0)

    evidence_by_id: Dict[str, Dict[str, Any]] = {}
    for path in ranked_paths:
        for step in path.get("steps", []):
            for side in ("from", "to"):
                node = step.get(side, {}) if isinstance(step, dict) else {}
                node_id = node.get("id")
                if node_id and node_id in graph.nodes:
                    gnode = graph.nodes[node_id]
                    evidence_by_id[node_id] = {
                        "id": gnode.id,
                        "label": gnode.label,
                        "type": gnode.type,
                        "source": gnode.source,
                        "confidence": round(_clamp(gnode.confidence), 4),
                    }

    entity = chain.get("entity") or {"id": entity_id}
    top_path = ranked_paths[0] if ranked_paths else None
    if top_path:
        conclusion = f"Most relevant connected evidence for {entity.get('label', entity_id)} is ranked through {', '.join(_path_relationship_types(top_path))}."
    else:
        conclusion = f"{entity.get('label', entity_id)} exists in the graph, but no relevant evidence path was ranked."

    return {
        "status": "available",
        "athena_version": ATHENA_VERSION,
        "reasoning_version": REASONING_VERSION,
        "generated_at": utc_now_iso(),
        "query": ReasoningQuery(entity_id, normalized_profile, tuple(focus_items), max_depth, normalized_traversal, limit).to_dict(),
        "entity": entity,
        "question": "Which connected evidence paths are most relevant for this context?",
        "relevant_evidence": list(evidence_by_id.values()),
        "reasoning_paths": ranked_paths,
        "confidence": confidence,
        "conclusion": conclusion,
        "known_gaps": _known_gaps(chain, ranked_paths, focus_items),
        "developer": {
            "graph_metadata": getattr(graph, "metadata", {}),
            "chain_version": chain.get("chain_version"),
            "available_path_count": chain.get("developer", {}).get("available_path_count"),
            "selected_path_count": len(ranked_paths),
            "weighting": applied,
            "relationship_weights": relationship_weights,
            "node_type_weights": node_type_weights,
        },
    }


def write_reasoning_report(
    entity_id: str,
    *,
    context_profile: str = "fantasy",
    focus: Optional[Iterable[str]] = None,
    max_depth: int = 3,
    traversal: str = "weighted",
    project_root: Path | None = None,
) -> Dict[str, Any]:
    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"
    report = build_reasoning_package(
        entity_id,
        context_profile=context_profile,
        focus=focus,
        max_depth=max_depth,
        traversal=traversal,
        project_root=project_root,
    )
    safe_id = entity_id.replace(":", "_").replace("/", "_")
    write_json(output_dir / f"reasoning_package_{safe_id}.json", report)
    return report
