"""Evidence path and repository-noise audit for AthenaEngine.

This tool is intentionally read-only by default. It inventories the current repo,
summarizes Scout route/evidence paths, and identifies cleanup candidates without
moving files or changing runtime behavior.

Usage:
    python Tools/audit_evidence_paths.py
    python Tools/audit_evidence_paths.py --json
    python Tools/audit_evidence_paths.py --write-report
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RUNTIME_ROUTE_FILES = [
    "Scout/app.py",
    "Scout/conversation/router.py",
    "Knowledge/Intelligence/Routing/request_router.py",
    "Knowledge/Intelligence/Intent/intent_classifier.py",
    "Knowledge/Intelligence/Public/public_answers.py",
    "Knowledge/Events/live_intelligence.py",
    "Reasoning/team_reasoning_engine.py",
    "Intelligence/Runtime/orchestrator.py",
]

CANONICAL_STAGES = [
    "Studio/Scout entry",
    "Scout API /api/ask",
    "Context loading",
    "Scout conversation router",
    "Public intent router",
    "Entity resolution",
    "Evidence retrieval",
    "Reasoning",
    "Composition",
    "Renderer",
    "Diagnostics/session log",
]

PROMPT_TRACE_TEMPLATES = [
    {
        "prompt_family": "public_team_overview",
        "example": "Who are the Maple Leafs?",
        "expected_route": "public_team_profile",
        "canonical_path": [
            "Scout/app.py:/api/ask",
            "Scout.conversation.router.route_question",
            "Knowledge.Intelligence.Routing.analyze_public_request",
            "Knowledge.Intelligence.Public.team_profile_answer",
            "Reasoning.team_reasoning_engine.assess_public_team",
            "Knowledge.Intelligence.Public._compose_public_team_copy",
            "Scout/app.py frontend renderAnswer",
        ],
        "known_gap": "Narrative still depends heavily on seeded team profile fields; live roster/cap/event evidence is not attached to the answer path.",
    },
    {
        "prompt_family": "targeted_team_weakness",
        "example": "What is the Leafs weakness?",
        "expected_route": "public_team_profile / targeted risk lens",
        "canonical_path": [
            "Scout.conversation.router.route_question",
            "Knowledge.Intelligence.Routing.analyze_public_request",
            "Knowledge.Intelligence.Public.team_profile_answer",
            "Knowledge.Intelligence.Public._compose_public_team_copy",
        ],
        "known_gap": "Targeted analytical sub-intent is not yet represented as a typed route contract; it is handled by copy composition and seed risk fields.",
    },
    {
        "prompt_family": "team_draft_question",
        "example": "Leafs upcoming draft",
        "expected_route": "draft_intelligence_gap",
        "canonical_path": [
            "Scout.conversation.router.route_question",
            "Knowledge.Intelligence.Routing.analyze_public_request",
            "Knowledge.Intelligence.Public.gap_answer",
        ],
        "known_gap": "Draft/pick/prospect feeds are not attached; answer is now user-facing but still cannot evaluate verified pick inventory.",
    },
    {
        "prompt_family": "recent_trade_events",
        "example": "Tell me about this week's trades",
        "expected_route": "live_event_intelligence",
        "canonical_path": [
            "Scout.conversation.router._live_events_answer",
            "Knowledge.Events.live_intelligence.live_events_for_question",
            "Scout.conversation.router._compose_live_event_narrative",
        ],
        "known_gap": "RSS evidence is filtered but not transformed into a full transaction object with teams/assets/picks/date/source confidence.",
    },
    {
        "prompt_family": "public_player_profile",
        "example": "Tell me about Auston Matthews",
        "expected_route": "public_player_profile",
        "canonical_path": [
            "Scout.conversation.router.route_question",
            "Knowledge.Intelligence.Routing.analyze_public_request",
            "Knowledge.Intelligence.Public.player_profile_answer",
            "Knowledge.Intelligence.Public._compose_public_player_copy",
        ],
        "known_gap": "Historical achievements and live public accomplishments are not consistently sourced into the player evidence packet.",
    },
]

CONSOLIDATION_TARGETS = [
    {
        "area": "Root release history",
        "symptom": "Large number of CHANGE_MANIFEST files at repository root.",
        "candidate_action": "Move historical manifests into docs/history or Archive/release_history after validating no tools expect root-level manifests.",
        "risk": "low",
    },
    {
        "area": "Runtime artifacts",
        "symptom": "Raw, Output, Reports, and Logs are present in the repository snapshot.",
        "candidate_action": "Keep folders gitignored and decide whether seed/demo data should live under samples/ instead of runtime paths.",
        "risk": "medium",
    },
    {
        "area": "Archive/runtime_quarantine",
        "symptom": "Quarantined nested-runtime files duplicate canonical Athena package names.",
        "candidate_action": "Keep archive outside active import path; consider compressing archive history after release stabilization.",
        "risk": "low",
    },
    {
        "area": "Engine / Intelligence / Reasoning",
        "symptom": "Multiple namespaces contain engines, models, confidence, evidence, and reasoning concepts.",
        "candidate_action": "Do not move yet; first convert one vertical slice to a typed evidence contract.",
        "risk": "high",
    },
    {
        "area": "Scout router",
        "symptom": "Scout/conversation/router.py is a large deterministic multiplexer.",
        "candidate_action": "Split by route family only after route contracts are documented and tests cover each path.",
        "risk": "high",
    },
]

def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def _all_files() -> List[Path]:
    return [p for p in PROJECT_ROOT.rglob("*") if p.is_file()]

def _python_loc(files: Iterable[Path]) -> int:
    total = 0
    for path in files:
        if path.suffix == ".py":
            try:
                total += sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    return total

def _top_level(path: Path) -> str:
    rel = path.relative_to(PROJECT_ROOT)
    return rel.parts[0] if len(rel.parts) > 1 else "."

def _parse_symbols(path: Path) -> List[Dict[str, Any]]:
    text = _safe_read(path)
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [{"type": "syntax_error", "name": str(exc), "line": getattr(exc, "lineno", 0) or 0}]
    symbols: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            symbols.append({"type": "class", "name": node.name, "line": node.lineno})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append({"type": "function", "name": node.name, "line": node.lineno})
    return symbols

def build_audit() -> Dict[str, Any]:
    files = _all_files()
    py_files = [p for p in files if p.suffix == ".py"]
    extension_counts = Counter(p.suffix or "<noext>" for p in files)
    top_counts = Counter(_top_level(p) for p in files)
    top_python_counts = Counter(_top_level(p) for p in py_files)

    duplicate_basenames: Dict[str, List[str]] = defaultdict(list)
    for path in files:
        duplicate_basenames[path.name].append(str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
    duplicate_basenames = {
        name: paths for name, paths in sorted(duplicate_basenames.items())
        if len(paths) > 1 and name not in {"__init__.py"}
    }

    route_symbols = {}
    missing_route_files = []
    for rel in RUNTIME_ROUTE_FILES:
        path = PROJECT_ROOT / rel
        if path.exists():
            route_symbols[rel] = _parse_symbols(path)
        else:
            missing_route_files.append(rel)

    root_files = [p for p in files if p.parent == PROJECT_ROOT]
    root_manifest_count = len([p for p in root_files if p.name.startswith("CHANGE_MANIFEST")])
    root_readme_count = len([p for p in root_files if p.name.startswith("README")])
    pycache_files = [str(p.relative_to(PROJECT_ROOT)).replace("\\", "/") for p in files if "__pycache__" in p.parts or p.suffix == ".pyc"]

    return {
        "created": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT_ROOT),
        "inventory": {
            "total_files": len(files),
            "python_files": len(py_files),
            "python_loc": _python_loc(files),
            "top_level_file_counts": dict(top_counts.most_common()),
            "top_level_python_counts": dict(top_python_counts.most_common()),
            "extension_counts": dict(extension_counts.most_common()),
            "root_manifest_count": root_manifest_count,
            "root_readme_count": root_readme_count,
            "pycache_files": pycache_files,
            "duplicate_basenames": duplicate_basenames,
        },
        "canonical_stages": CANONICAL_STAGES,
        "runtime_route_files": RUNTIME_ROUTE_FILES,
        "missing_route_files": missing_route_files,
        "route_symbols": route_symbols,
        "prompt_trace_templates": PROMPT_TRACE_TEMPLATES,
        "consolidation_targets": CONSOLIDATION_TARGETS,
        "next_vertical_slice": {
            "prompt": "What is the Leafs weakness?",
            "goal": "Trace one route from user prompt to evidence packet to reasoning to final public answer.",
            "required_contract": [
                "intent",
                "entity",
                "question_focus",
                "evidence_requested",
                "evidence_available",
                "evidence_retrieved",
                "evidence_discarded",
                "reasoning_outputs",
                "public_answer",
            ],
        },
    }

def render_markdown(audit: Dict[str, Any]) -> str:
    inv = audit["inventory"]
    lines: List[str] = []
    lines.append("# Evidence Traceability Audit — v0.5.5.5.20")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This is an audit-first checkpoint. It does not add a new intelligence module. It documents the current Scout evidence path, identifies repository noise, and marks consolidation candidates before structural reorganization.")
    lines.append("")
    lines.append("## Repository inventory")
    lines.append("")
    lines.append(f"- Total files: {inv['total_files']}")
    lines.append(f"- Python files: {inv['python_files']}")
    lines.append(f"- Python LOC: {inv['python_loc']}")
    lines.append(f"- Root change manifests: {inv['root_manifest_count']}")
    lines.append(f"- Root README-style files: {inv['root_readme_count']}")
    lines.append(f"- Python cache files present: {len(inv['pycache_files'])}")
    lines.append("")
    lines.append("## Top-level file concentration")
    lines.append("")
    lines.append("| Area | Files | Python files |")
    lines.append("|---|---:|---:|")
    py_counts = inv["top_level_python_counts"]
    for area, count in list(inv["top_level_file_counts"].items())[:20]:
        lines.append(f"| `{area}` | {count} | {py_counts.get(area, 0)} |")
    lines.append("")
    lines.append("## Canonical evidence path being audited")
    lines.append("")
    for idx, stage in enumerate(audit["canonical_stages"], start=1):
        lines.append(f"{idx}. {stage}")
    lines.append("")
    lines.append("## Prompt trace templates")
    lines.append("")
    for item in audit["prompt_trace_templates"]:
        lines.append(f"### {item['prompt_family']}")
        lines.append("")
        lines.append(f"- Example: `{item['example']}`")
        lines.append(f"- Expected route: `{item['expected_route']}`")
        lines.append("- Current path:")
        for step in item["canonical_path"]:
            lines.append(f"  - `{step}`")
        lines.append(f"- Known gap: {item['known_gap']}")
        lines.append("")
    lines.append("## Consolidation targets")
    lines.append("")
    lines.append("| Area | Symptom | Candidate action | Risk |")
    lines.append("|---|---|---|---|")
    for target in audit["consolidation_targets"]:
        lines.append(f"| {target['area']} | {target['symptom']} | {target['candidate_action']} | {target['risk']} |")
    lines.append("")
    lines.append("## Do not reorganize yet")
    lines.append("")
    lines.append("The next work should trace one vertical slice before moving files. The best candidate remains `What is the Leafs weakness?` because it exercises entity resolution, targeted analytical intent, team evidence, reasoning, composition, and public rendering.")
    lines.append("")
    lines.append("## Next required contract")
    lines.append("")
    for field in audit["next_vertical_slice"]["required_contract"]:
        lines.append(f"- `{field}`")
    lines.append("")
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON instead of markdown.")
    parser.add_argument("--write-report", action="store_true", help="Write JSON and markdown reports under Reports/evidence_path_audit.")
    args = parser.parse_args()

    audit = build_audit()
    if args.write_report:
        out_dir = PROJECT_ROOT / "Reports" / "evidence_path_audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        (out_dir / f"evidence_traceability_audit_{stamp}.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        (out_dir / f"evidence_traceability_audit_{stamp}.md").write_text(render_markdown(audit), encoding="utf-8")
        print(f"Wrote evidence path audit reports to {out_dir}")
        return 0

    if args.json:
        print(json.dumps(audit, indent=2))
    else:
        print(render_markdown(audit))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
