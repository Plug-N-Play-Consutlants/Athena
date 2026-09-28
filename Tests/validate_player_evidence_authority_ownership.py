from Knowledge.Intelligence.Public.player_evidence import authoritative_statistical_view
from Athena.player_assessment import assess_player


def main():
    evidence = {
        "position": "C", "target_season": "2025-26",
        "career_games": 1, "career_points": 0, "career_goals": 0,
        "season_history": [{"season":"1999-00","gp":82,"points":1}],
        "statistical_evidence": {
            "contract":"canonical_player_statistical_evidence", "source":"nhl_player_landing", "target_season":"2025-26",
            "season_series":[
                {"season":"2025-26","gp":82,"points":138},
                {"season":"2024-25","gp":67,"points":100},
                {"season":"2023-24","gp":76,"points":132}],
            "career":{"games":700,"points":1100,"goals":400},
            "freshness":{"status":"current_or_recent","stale_for_current_rating":False,"latest_season":"2025-26"}
        }
    }
    view = authoritative_statistical_view(evidence)
    checks = {
        "canonical_authority": view["authority"] == "canonical_statistical_evidence",
        "canonical_window": [r["season"] for r in view["recent_window"]] == ["2025-26","2024-25","2023-24"],
        "canonical_career_overrides_legacy": view["career"]["games"] == 700 and view["career"]["points"] == 1100,
    }
    assessment = assess_player(evidence)
    checks["assessment_uses_authority"] = assessment.get("evidence_authority") == "canonical_statistical_evidence" and assessment["recent_points"] == 370
    for name, ok in checks.items(): print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not all(checks.values()): raise SystemExit(1)
    print("Player Evidence Authority Ownership Validation: PASS")

if __name__ == "__main__": main()
