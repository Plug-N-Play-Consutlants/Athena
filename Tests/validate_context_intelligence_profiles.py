"""Validate Sprint 4B.2 Context Intelligence & Evaluation Profiles."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Core.version import ATHENA_VERSION, SCOUT_VERSION
from Intelligence.Player.player_intelligence import evaluate_player
from Intelligence.Context.context_intelligence import (
    EVALUATION_PROFILES,
    infer_evaluation_profile,
    evaluate_context,
    apply_context_profile,
    build_context_evaluation,
)
from Scout.conversation.router import player_intelligence_answer


def _seed(root: Path) -> None:
    out = root / "Output"
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "player_master.json", [
        {"player_id": "34", "player_name": "Auston Matthews", "position": "C", "nhl_team": "TOR"},
        {"player_id": "87", "player_name": "Sidney Crosby", "position": "C", "nhl_team": "PIT"},
    ])
    write_json(out / "player_production.json", [
        {"player_id": "34", "nhl_player_name": "Auston Matthews", "position": "C", "nhl_team": "TOR", "points": 69, "goals": 33, "assists": 36, "games_played": 67, "points_per_game": 1.0299, "production_percentile": 0.82, "source": "test_nhl_skater_summary"},
        {"player_id": "87", "nhl_player_name": "Sidney Crosby", "position": "C", "nhl_team": "PIT", "points": 74, "goals": 29, "assists": 45, "games_played": 68, "points_per_game": 1.0882, "production_percentile": 0.7776, "source": "test_nhl_skater_summary"},
    ])
    write_json(out / "player_profiles.json", [
        {"player_id": "34", "player_name": "Auston Matthews", "fantasy_team": "Alien Agenda", "keeper_relevance": "high"},
    ])
    write_json(out / "player_contracts.json", [
        {"player_id": "34", "player_name": "Auston Matthews", "years_remaining": 3, "contract_band": "full_runway"},
    ])
    write_json(out / "player_status.json", [
        {"player_id": "34", "player_name": "Auston Matthews", "availability_status": "active", "roster_slot": "starter"},
    ])
    write_json(out / "player_identity_map.json", [])
    write_json(out / "knowledge_readiness.json", {})
    write_json(out / "manager_behavior.json", {"records": []})
    write_json(out / "league_market.json", {})


class DummyContext:
    files_loaded = {}


def main() -> int:
    results = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _seed(root)

        check("profiles_defined", all(k in EVALUATION_PROFILES for k in ["public", "fantasy", "projection", "odds"]), f"profiles={list(EVALUATION_PROFILES)}")
        check("odds_profile_inferred", infer_evaluation_profile("Matthews anytime goal odds tonight", default="public") == "odds", infer_evaluation_profile("Matthews anytime goal odds tonight"))
        check("projection_profile_inferred", infer_evaluation_profile("Can Matthews bounce back next season?", default="public") == "projection", infer_evaluation_profile("Can Matthews bounce back next season?"))
        check("fantasy_profile_inferred", infer_evaluation_profile("Should I keep Matthews in fantasy?", default="public") == "fantasy", infer_evaluation_profile("Should I keep Matthews in fantasy?"))

        player_eval = evaluate_player("Tell me about Auston Matthews", mode="fantasy", project_root=root)
        check("base_player_eval_available", player_eval.get("status") == "available", f"status={player_eval.get('status')}")

        fantasy_context = evaluate_context(player_eval, profile="fantasy", question="Should I keep Matthews in fantasy?")
        check("fantasy_context_uses_fantasy_and_contract", "fantasy_context" in fantasy_context.get("available_dimensions", []) and "contract" in fantasy_context.get("available_dimensions", []), str(fantasy_context.get("available_dimensions")))

        odds_context = evaluate_context(player_eval, profile="odds", question="Matthews anytime goal odds tonight")
        check("odds_context_missing_required_context", odds_context.get("profile") == "odds" and "opponent_context" in odds_context.get("missing_dimensions", []) and "line_synergy" in odds_context.get("missing_dimensions", []), str(odds_context.get("missing_dimensions")))
        check("odds_disclaimer_present", any("not gambling advice" in item.lower() for item in odds_context.get("limitations", [])), str(odds_context.get("limitations", [])))

        applied = apply_context_profile(player_eval, profile="projection", question="Will Matthews bounce back next season?")
        check("context_attached_to_player_eval", applied.get("evaluation_profile") == "projection" and applied.get("context_profile"), f"profile={applied.get('evaluation_profile')}")
        check("contextual_evaluation_added", "projection context" in applied.get("contextual_evaluation", "").lower(), applied.get("contextual_evaluation", "")[:120])

        built = build_context_evaluation(player_eval, profile="odds", question="Matthews anytime goal odds tonight", project_root=root)
        reports = built.get("context_reports", {})
        check("context_reports_written", Path(reports.get("json", "")).exists() and Path(reports.get("text", "")).exists(), str(reports))

        routed = player_intelligence_answer(DummyContext(), "Auston Matthews anytime goal odds tonight", mode="fantasy")
        # Router uses default project root in normal runtime; validate answer shape/module binding through direct applied object instead of temp outputs.
        check("router_imports_context_module", "Intelligence.Context.apply_context_profile" in routed.get("developer", {}).get("modules_executed", []), str(routed.get("developer", {}).get("modules_executed", [])))

        check("version_updated", ATHENA_VERSION.endswith("drop4d1") and SCOUT_VERSION.endswith("drop4d1"), f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print("Context Intelligence & Evaluation Profiles Validation Report")
    print("============================================================")
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    print(f"Passed: {passed}")
    print("Warnings: 0")
    print(f"Failed: {failed}")
    print()
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    raise SystemExit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
