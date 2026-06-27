"""Manual query helper for Sprint 4B.2 context intelligence."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Intelligence.Player.player_intelligence import evaluate_player
from Intelligence.Context.context_intelligence import infer_evaluation_profile, build_context_evaluation

QUESTION = "Auston Matthews anytime goal odds tonight"

profile = infer_evaluation_profile(QUESTION, default="fantasy")
player = evaluate_player(QUESTION, mode="fantasy", project_root=PROJECT_ROOT)
result = build_context_evaluation(player, profile=profile, question=QUESTION, project_root=PROJECT_ROOT)
ctx = result.get("context_profile", {})
print("Context Intelligence Query")
print("==========================")
print(f"Question: {QUESTION}")
print(f"Profile: {ctx.get('profile_label')} ({ctx.get('profile')})")
print(f"Context readiness: {ctx.get('context_readiness')}")
print(f"Available: {', '.join(ctx.get('available_dimensions', [])) or 'none'}")
print(f"Missing: {', '.join(ctx.get('missing_dimensions', [])) or 'none'}")
print(f"Evaluation: {result.get('contextual_evaluation')}")
print(f"JSON: {result.get('context_reports', {}).get('json')}")
print(f"Text: {result.get('context_reports', {}).get('text')}")
raise SystemExit(0)
