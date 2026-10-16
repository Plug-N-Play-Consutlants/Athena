from __future__ import annotations

import unittest
from unittest.mock import patch

from Athena.request_execution import AthenaRequest, execute_request
from Athena.public_team_performance import assess_team_performance
from Athena.team_comparative_evaluation import evaluate_team, narrative
from Knowledge.Identity.registry import SEED_IDENTITY_ENTITIES
from Scout.conversation.composition import compose_answer_payload
from Scout.conversation.context import ScoutContext


class TeamInvestigationPathTests(unittest.TestCase):
    def test_team_metrics_use_athena_route_and_one_shared_acquisition(self) -> None:
        questions = (
            "How do the Toronto Maple Leafs compare with the rest of the NHL in scoring, "
            "goal prevention and goaltending this season? What does that suggest management "
            "should investigate first?",
            "Compare the Boston Bruins' offensive and defensive performance against NHL league "
            "averages. Are there verified weaknesses, or are the results too early to justify "
            "a roster change?",
        )
        for question in questions:
            with self.subTest(question=question):
                subject = "TOR" if "Toronto" in question else "BOS"
                evidence = {
                    "team": subject,
                    "season": "20262027",
                    "sources": ["nhl_club_stats_season", "nhl_official_current_standings"],
                    "missing": ["league_goalie_comparison"],
                    "leaders": [{"name": "Example Player", "points": 8, "gp": 7}],
                    "standings": {"gamesPlayed": 7, "goalFor": 20, "goalAgainst": 19},
                }
                assessment = {
                    "conclusion": (
                        f"{subject} scores 2.86 goals per game and allows 2.71 through seven games. "
                        "This is provisional. Investigate goal prevention first; goalie comparison "
                        "is unavailable, so no goaltending conclusion is warranted."
                    ),
                    "evidence": evidence,
                    "confidence": 0.6,
                }
                context = ScoutContext()
                with patch(
                    "Athena.public_team_performance.assess_team_performance",
                    return_value=assessment,
                ) as acquire:
                    answer = execute_request(
                        AthenaRequest(question=question, mode="public", context=context)
                    )
                acquire.assert_called_once()
                self.assertEqual(
                    answer["developer"]["athena_request"]["selected_route"],
                    "public_current_season_team_investigation",
                )
                self.assertEqual(
                    answer["developer"]["athena_request"]["execution_owner"],
                    "athena_registered_specialist",
                )
                trace = answer["developer"]["inquiry_execution_trace"]
                self.assertEqual(
                    trace["evidence"]["sources"],
                    ["nhl_club_stats_season", "nhl_official_current_standings"],
                )
                self.assertEqual(trace["evidence"]["missing"], ["league_goalie_comparison"])
                self.assertIn("no goaltending conclusion is warranted", answer["engine_conclusion"])
                self.assertEqual(answer["developer"]["team_performance_evidence"], evidence)
                public_answer = compose_answer_payload(answer)
                self.assertIn("Investigate goal prevention first", public_answer["public_comment"])

    def test_legacy_team_evidence_is_not_reacquired_when_athena_bundle_exists(self) -> None:
        context = ScoutContext()
        context.request_evidence = {
            "team": "BOS",
            "team_performance_assessment": {
                "conclusion": "A pre-acquired assessment.",
                "evidence": {"team": "BOS", "season": "20262027", "sources": [], "missing": []},
                "confidence": 0.5,
            },
        }
        with patch(
            "Athena.public_team_performance.assess_team_performance",
            side_effect=AssertionError("duplicate team acquisition"),
        ):
            from Athena.public_team_performance import execute_team_investigation

            answer = execute_team_investigation(
                context, "What are the Boston Bruins' biggest roster weaknesses?"
            )
        self.assertEqual(answer["engine_conclusion"], "A pre-acquired assessment.")

    def test_live_acquisition_uses_complete_league_and_goalie_denominators(self) -> None:
        teams = [
            entity.entity_id.rsplit(".", 1)[-1].upper()
            for entity in SEED_IDENTITY_ENTITIES
            if entity.entity_type == "team" and entity.league == "NHL"
        ]

        class NHLClientFixture:
            def get_club_stats(self, abbreviation: str, season: str) -> dict:
                return {
                    "skaters": [],
                    "goalies": [{
                        "firstName": "Fixture",
                        "lastName": "Goalie",
                        "gamesPlayed": 8,
                        "saves": 920,
                        "shotsAgainst": 1000,
                        "savePctg": 0.92,
                    }],
                }

            def get_team_standings_now(self) -> dict:
                rows = []
                for abbreviation in teams:
                    rows.append({
                        "teamAbbrev": {"default": abbreviation},
                        "gamesPlayed": 8,
                        "wins": 4,
                        "losses": 3,
                        "otLosses": 1,
                        "points": 9,
                        "pointPctg": 0.5625,
                        "goalFor": 24,
                        "goalAgainst": 32 if abbreviation == "TOR" else 24,
                    })
                return {"standings": rows}

            def get_goalie_summary(self, season: str) -> dict:
                return {"data": [
                    {"saves": 9100, "shotsAgainst": 10000}
                    for _ in range(60)
                ]}

            def get_team_schedule_now(self, abbreviation: str) -> dict:
                return {"games": []}

        with (
            patch("Providers.NHL.nhl_client.NHLClient", NHLClientFixture),
            patch("Knowledge.Intelligence.Public.player_evidence._target_season_id", return_value="20262027"),
        ):
            assessment = assess_team_performance(
                "How do the Toronto Maple Leafs compare in scoring and goaltending this season?",
                "TOR",
                "Toronto Maple Leafs",
            )

        evidence = assessment["evidence"]
        self.assertEqual(evidence["league_benchmark"]["teams"], len(teams))
        self.assertEqual(evidence["league_goalie_benchmark"]["shots_against"], 600000)
        self.assertEqual(evidence["team_goalie_save_percentage"]["shots_against"], 1000)
        evaluation = evaluate_team(evidence)
        self.assertIn("league_relative_goal_rates", [signal["id"] for signal in evaluation["signals"]])
        self.assertIn(
            "league_relative_goalie_save_percentage",
            [signal["id"] for signal in evaluation["signals"]],
        )
        self.assertEqual(evaluation["investigation_priority"], "investigate_goal_prevention")
        self.assertIn("investigate goal prevention first", narrative(evaluation).lower())


if __name__ == "__main__":
    unittest.main()
