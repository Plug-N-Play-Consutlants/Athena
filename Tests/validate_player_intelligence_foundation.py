"""Validate Sprint 4B.1 Player Intelligence Foundation."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION
from Intelligence.Player.player_intelligence import evaluate_player, build_player_evaluation
from Scout.conversation.router import route_question

passed = []
failed = []
warnings = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        passed.append((name, detail))
    else:
        failed.append((name, detail))


def main() -> int:
    public_eval = evaluate_player("Tell me about Sidney Crosby", mode="public", project_root=PROJECT_ROOT)
    check("public_player_eval_available", public_eval.get("status") == "available", f"status={public_eval.get('status')}; title={public_eval.get('title')}")
    check("public_eval_shape", all(k in public_eval for k in ["player", "profiles", "evidence_presence", "confidence", "evaluation"]), f"keys={sorted(public_eval.keys())[:8]}")
    check("production_profile_present", bool(public_eval.get("profiles", {}).get("production", {}).get("available")), str(public_eval.get("profiles", {}).get("production", {})))

    fantasy_eval = evaluate_player("Tell me about Auston Matthews", mode="fantasy", project_root=PROJECT_ROOT)
    check("fantasy_player_eval_available", fantasy_eval.get("status") == "available", f"status={fantasy_eval.get('status')}; title={fantasy_eval.get('title')}")
    check("fantasy_uses_fantrax_context", fantasy_eval.get("evidence_presence", {}).get("fantasy") is True, str(fantasy_eval.get("evidence_presence")))
    check("contract_profile_bounded", "contract" in fantasy_eval.get("profiles", {}), str(fantasy_eval.get("profiles", {}).get("contract")))

    no_match = evaluate_player("Tell me about Totally Fake Player", mode="public", project_root=PROJECT_ROOT)
    check("unsupported_player_bounded", no_match.get("status") == "no_match" and no_match.get("confidence", 1) <= 0.25, f"status={no_match.get('status')}; confidence={no_match.get('confidence')}")

    scout_answer = route_question("Tell me about Sidney Crosby", mode="fantasy")
    check("scout_player_binding", scout_answer.get("intent") == "player_analysis", f"intent={scout_answer.get('intent')}; title={scout_answer.get('title')}")
    check("scout_developer_trace", "player_evaluation" in scout_answer.get("developer", {}), "developer includes player_evaluation")

    report = build_player_evaluation("Sidney Crosby", mode="fantasy", project_root=PROJECT_ROOT)
    reports = report.get("reports", {})
    check("player_reports_written", Path(reports.get("json", "")).exists() and Path(reports.get("text", "")).exists(), str(reports))

    check("version_updated", ATHENA_VERSION == "0.5.0-drop4d1" and SCOUT_VERSION == "v0.5.0-drop4d1", f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}")

    print("Player Intelligence Foundation Validation Report")
    print("================================================")
    status = "PASS" if not failed else "FAIL"
    print(f"Overall status: {status}")
    print(f"Passed: {len(passed)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Failed: {len(failed)}")
    print()
    for name, detail in passed:
        print(f"[PASS] {name}: {detail}")
    for name, detail in warnings:
        print(f"[WARN] {name}: {detail}")
    for name, detail in failed:
        print(f"[FAIL] {name}: {detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
