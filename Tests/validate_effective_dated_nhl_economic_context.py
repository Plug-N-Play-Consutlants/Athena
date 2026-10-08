"""Acceptance validation for the v0.7.0 effective-dated economic context foundation."""
from __future__ import annotations
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Economics.league_season_context import resolve_league_season_context
from Athena.intent_planner import plan_capability
from Athena.execution_registry import SPECIALISTS, execute_specialist


def main() -> int:
    checks=[]
    def check(name, ok, detail=""):
        checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    check("version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 7, 0, 0, 1), ATHENA_VERSION)
    check("release_metadata_available", bool(RELEASE_NAME.strip()), RELEASE_NAME)
    pre = resolve_league_season_context(as_of="2026-09-15")
    post = resolve_league_season_context(as_of="2026-09-16")
    check("2026_27_final_range", post.upper_limit == 104_000_000 and post.midpoint == 90_400_000 and post.lower_limit == 76_900_000, str(post.to_dict()))
    check("temporal_cba_boundary", pre.cba_environment_id == "nhl_cba_2013_extended" and post.cba_environment_id == "nhl_cba_2026", f"{pre.cba_environment_id} -> {post.cba_environment_id}")
    old = resolve_league_season_context(as_of="2025-10-01")
    check("prior_year_not_projected_backward", old.upper_limit == 95_500_000 and old.upper_limit != post.upper_limit, str(old.upper_limit))
    plan = plan_capability("What is the NHL salary cap for 2026-27?", "public")
    check("athena_plans_context", getattr(plan, "route", None) == "public_nhl_economic_context", getattr(plan, "route", None))
    check("registered", "public_nhl_economic_context" in SPECIALISTS)
    ctx = SimpleNamespace(files_loaded=[])
    answer = execute_specialist("public_nhl_economic_context", ctx, "What is the NHL salary cap for 2026-27?", mode="public")
    econ = (answer or {}).get("developer", {}).get("league_season_context", {})
    check("athena_consumes_context", econ.get("upper_limit") == 104_000_000 and "$104.0M" in (answer or {}).get("natural_language_response", ""), str(econ.get("upper_limit")))
    check("no_false_team_ledger", "not a team cap calculation" in (answer or {}).get("natural_language_response", "").lower())
    print(f"Overall status: {'PASS' if all(checks) else 'FAIL'}")
    return 0 if all(checks) else 1

if __name__ == "__main__": raise SystemExit(main())
