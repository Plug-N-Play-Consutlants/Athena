from __future__ import annotations

import unittest
from unittest.mock import patch

from Athena.request_execution import AthenaRequest, execute_request
from Athena.public_team_performance import assess_team_performance
from Athena.team_comparative_evaluation import evaluate_team, narrative
from Athena.intent_resolution import select_executable_route
from Knowledge.Identity.registry import SEED_IDENTITY_ENTITIES
from Scout.conversation.composition import compose_answer_payload
from Scout.conversation.context import ScoutContext
from Scout.conversation.router import route_question


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
            "route": "public_current_season_team_investigation",
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

    def test_immutable_context_consumes_request_evidence_without_duplicate_acquisition(self) -> None:
        question = "Compare the Toronto Maple Leafs' scoring this season."
        assessment = {
            "conclusion": "Request-owned assessment.",
            "evidence": {
                "team": "TOR",
                "season": "20262027",
                "sources": ["nhl_official_current_standings"],
                "missing": [],
            },
            "confidence": 0.6,
        }
        with patch(
            "Athena.public_team_performance.assess_team_performance",
            return_value=assessment,
        ) as acquire:
            answer = execute_request(
                AthenaRequest(question=question, mode="public", context=object())
            )

        acquire.assert_called_once()
        trace = answer["developer"]["inquiry_execution_trace"]
        self.assertEqual(
            trace["evidence"]["transport"],
            "read_through_context_adapter",
        )
        self.assertTrue(trace["result"]["evidence_consumption_verified"])
        self.assertEqual(
            trace["result"]["evidence_consumption"]["owner"],
            "Athena.request_execution",
        )

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

    def test_scout_executes_both_team_questions_with_deterministic_provider_evidence(self) -> None:
        teams = [
            entity.entity_id.rsplit(".", 1)[-1].upper()
            for entity in SEED_IDENTITY_ENTITIES
            if entity.entity_type == "team" and entity.league == "NHL"
        ]
        self.assertEqual(len(teams), 32)

        class NHLClientFixture:
            missing_goalie_benchmark = False

            def get_club_stats(self, abbreviation: str, season: str) -> dict:
                goalie_saves = 900 if abbreviation == "TOR" else 925
                return {
                    "skaters": [{
                        "firstName": "Fixture",
                        "lastName": "Scorer",
                        "gamesPlayed": 8,
                        "goals": 4,
                        "assists": 5,
                        "points": 9,
                    }],
                    "goalies": [{
                        "firstName": "Fixture",
                        "lastName": "Goalie",
                        "gamesPlayed": 8,
                        "saves": goalie_saves,
                        "shotsAgainst": 1000,
                        "savePctg": goalie_saves / 1000,
                    }],
                }

            def get_team_standings_now(self) -> dict:
                rows = []
                for abbreviation in teams:
                    gf, ga = (20, 32) if abbreviation == "TOR" else (30, 20) if abbreviation == "BOS" else (24, 24)
                    rows.append({
                        "teamAbbrev": {"default": abbreviation},
                        "gamesPlayed": 8,
                        "wins": 4,
                        "losses": 3,
                        "otLosses": 1,
                        "points": 9,
                        "pointPctg": 0.5625,
                        "goalFor": gf,
                        "goalAgainst": ga,
                    })
                return {"standings": rows}

            def get_goalie_summary(self, season: str) -> dict:
                if self.missing_goalie_benchmark:
                    return {"data": []}
                return {"data": [{"saves": 9100, "shotsAgainst": 10000} for _ in range(60)]}

            def get_team_schedule_now(self, abbreviation: str) -> dict:
                return {"games": [
                    {
                        "gameState": "FINAL",
                        "gameDate": f"2026-10-{day:02d}",
                        "homeTeam": {"abbrev": abbreviation, "score": 3},
                        "awayTeam": {"abbrev": "NJD", "score": 2},
                    }
                    for day in range(1, 6)
                ]}

            def get_current_roster(self, abbreviation: str) -> dict:
                return {"forwards": [], "defensemen": [], "goalies": []}

        questions = (
            (
                "How do the Toronto Maple Leafs compare with the rest of the NHL in scoring, "
                "goal prevention and goaltending this season? What does that suggest management "
                "should investigate first?",
                "TOR",
                "investigate_goaltending_and_goal_prevention",
            ),
            (
                "Compare the Boston Bruins' offensive and defensive performance against NHL league "
                "averages. Are there verified weaknesses, or are the results too early to justify "
                "a roster change?",
                "BOS",
                "investigate_sustainability",
            ),
        )
        with (
            patch("Providers.NHL.nhl_client.NHLClient", NHLClientFixture),
            patch("Knowledge.Intelligence.Public.player_evidence._target_season_id", return_value="20262027"),
        ):
            for question, abbreviation, expected_priority in questions:
                with self.subTest(team=abbreviation):
                    context = ScoutContext()
                    answer = route_question(question, context, mode="public")
                    self.assertEqual(answer["intent"], "public_current_season_team_investigation")
                    developer = answer["developer"]
                    self.assertEqual(
                        developer["athena_request"]["selected_route"],
                        "public_current_season_team_investigation",
                    )
                    self.assertEqual(
                        developer["athena_request"]["execution_owner"],
                        "athena_registered_specialist",
                    )
                    evidence = developer["team_performance_evidence"]
                    evaluation = evidence["comparative_evaluation"]
                    signals = {signal["id"] for signal in evaluation["signals"]}
                    self.assertTrue({
                        "team_goal_balance",
                        "league_relative_goal_rates",
                        "league_relative_goalie_save_percentage",
                    }.issubset(signals))
                    self.assertEqual(evaluation["investigation_priority"], expected_priority)
                    self.assertEqual(evidence["league_benchmark"]["teams"], len(teams))
                    self.assertIn("nhl_official_standings_league_benchmark", evidence["sources"])
                    self.assertIn("nhl_official_goalie_summary", evidence["sources"])
                    self.assertIn("provisional", answer["natural_language_response"].lower())
                    self.assertIn("shots against", answer["natural_language_response"].lower())
                    self.assertIn("shot quality", answer["natural_language_response"].lower())
                    trace = developer["inquiry_execution_trace"]
                    self.assertTrue(trace["result"]["evidence_consumption_verified"])
                    self.assertEqual(trace["evidence"]["specialist_evidence"]["consumption"]["owner"], "Athena.request_execution")
                    coverage = {
                        objective["id"]: objective
                        for objective in developer["inquiry_objective_coverage"]["objectives"]
                    }
                    self.assertEqual(coverage["comparison"]["evidence_coverage"], "observations_available")
                    self.assertIn("league_relative_goal_rates", coverage["comparison"]["evidence_refs"])
                    composed = compose_answer_payload(answer)
                    self.assertIn("league average", composed["public_comment"].lower())
                    self.assertIn("investigate", composed["public_comment"].lower())

    def test_missing_goalie_benchmark_preserves_scoring_and_prevention_findings(self) -> None:
        teams = [
            entity.entity_id.rsplit(".", 1)[-1].upper()
            for entity in SEED_IDENTITY_ENTITIES
            if entity.entity_type == "team" and entity.league == "NHL"
        ]

        class NHLClientFixture:
            def get_club_stats(self, abbreviation: str, season: str) -> dict:
                return {"skaters": [], "goalies": []}

            def get_team_standings_now(self) -> dict:
                return {"standings": [{
                    "teamAbbrev": {"default": abbreviation},
                    "gamesPlayed": 8,
                    "wins": 4,
                    "losses": 3,
                    "otLosses": 1,
                    "points": 9,
                    "pointPctg": 0.5625,
                    "goalFor": 20 if abbreviation == "TOR" else 24,
                    "goalAgainst": 32 if abbreviation == "TOR" else 24,
                } for abbreviation in teams]}

            def get_goalie_summary(self, season: str) -> dict:
                return {"data": []}

            def get_team_schedule_now(self, abbreviation: str) -> dict:
                return {"games": []}

        question = "Compare Toronto Maple Leafs scoring, goal prevention and goaltending this season."
        with (
            patch("Providers.NHL.nhl_client.NHLClient", NHLClientFixture),
            patch("Knowledge.Intelligence.Public.player_evidence._target_season_id", return_value="20262027"),
        ):
            answer = route_question(question, object(), mode="public")
        evidence = answer["developer"]["team_performance_evidence"]
        signal_ids = {signal["id"] for signal in evidence["comparative_evaluation"]["signals"]}
        self.assertIn("league_relative_goal_rates", signal_ids)
        self.assertNotIn("league_relative_goalie_save_percentage", signal_ids)
        self.assertIn("league_goalie_comparison", evidence["missing"])
        self.assertIn("goals per game", answer["natural_language_response"].lower())
        self.assertIn("not acquired", answer["natural_language_response"].lower())
        comparison_coverage = next(
            item for item in answer["developer"]["inquiry_objective_coverage"]["objectives"]
            if item["id"] == "comparison"
        )
        self.assertEqual(comparison_coverage["evidence_coverage"], "partially_available")
        self.assertIn("league_goalie_comparison", comparison_coverage["evidence_blockers"])

    def test_economic_support_executes_and_reuses_request_owned_state(self) -> None:
        teams = [
            entity.entity_id.rsplit(".", 1)[-1].upper()
            for entity in SEED_IDENTITY_ENTITIES
            if entity.entity_type == "team" and entity.league == "NHL"
        ]

        class NHLClientFixture:
            def get_club_stats(self, abbreviation: str, season: str) -> dict:
                return {"skaters": [], "goalies": []}

            def get_team_standings_now(self) -> dict:
                return {"standings": [{
                    "teamAbbrev": {"default": abbreviation},
                    "gamesPlayed": 8,
                    "wins": 4,
                    "losses": 3,
                    "otLosses": 1,
                    "points": 9,
                    "pointPctg": 0.5625,
                    "goalFor": 24,
                    "goalAgainst": 24,
                } for abbreviation in teams]}

            def get_goalie_summary(self, season: str) -> dict:
                return {"data": [{"saves": 9100, "shotsAgainst": 10000} for _ in range(60)]}

            def get_team_schedule_now(self, abbreviation: str) -> dict:
                return {"games": []}

            def get_current_roster(self, abbreviation: str) -> dict:
                return {"forwards": [], "defensemen": [], "goalies": []}

        question = (
            "Compare the Toronto Maple Leafs' scoring and goal prevention this season, "
            "and explain how available salary-cap evidence constrains options."
        )
        from Knowledge.Teams.team_economic_state import resolve_team_economic_state
        with (
            patch("Providers.NHL.nhl_client.NHLClient", NHLClientFixture),
            patch("Knowledge.Intelligence.Public.player_evidence._target_season_id", return_value="20262027"),
            patch(
                "Knowledge.Teams.team_economic_state.resolve_team_economic_state",
                wraps=resolve_team_economic_state,
            ) as resolve_state,
        ):
            answer = route_question(question, object(), mode="public")

        self.assertEqual(
            answer["developer"]["athena_request"]["selected_route"],
            "public_current_season_team_investigation",
        )
        coordination = answer["developer"]["capability_coordination"]
        self.assertEqual(coordination["supporting_executed"], 1)
        self.assertTrue(coordination["multi_capability_synthesis_verified"])
        self.assertEqual(len(coordination["supporting_results"]), 1)
        finding = coordination["supporting_results"][0]
        self.assertEqual(finding["route"], "public_nhl_cap_reasoning")
        self.assertEqual(finding["state"], "evidence_available")
        self.assertEqual(finding["subject"], "TOR")
        self.assertTrue(finding["presentation_merged"])
        self.assertEqual(resolve_state.call_count, 1)
        self.assertIn("Financial constraints", answer["natural_language_response"])
        economics_coverage = next(
            item for item in answer["developer"]["inquiry_objective_coverage"]["objectives"]
            if item["id"] == "economics"
        )
        self.assertEqual(economics_coverage["evidence_coverage"], "partially_available")
        self.assertIn("complete_verified_team_cap_ledger", economics_coverage["evidence_blockers"])

    def test_scout_diagnostics_do_not_route_to_hockey_rules_retrieval(self) -> None:
        question = "Athena appears to route this evidence question to NHL rules instead of its execution trace."
        route, selected_by = select_executable_route(question, "public")
        self.assertEqual(route, "athena_runtime_diagnostics")
        self.assertEqual(selected_by, "athena_diagnostic_intent")
        with patch(
            "Knowledge.Sources.public_hockey_retrieval.retrieve_public_hockey_knowledge",
            side_effect=AssertionError("diagnostics must not retrieve hockey rules"),
        ):
            answer = route_question(question, ScoutContext(), mode="public")
        self.assertEqual(answer["developer"]["athena_request"]["selected_route"], "athena_runtime_diagnostics")
        self.assertIn("prior-turn execution trace", answer["natural_language_response"])
        self.assertIn("prior_turn_execution_trace_unavailable", answer["known_limitations"])

    def test_scout_routes_publicly_named_fantasy_league_through_athena_registry(self) -> None:
        question = "Analyze the JHLPAA trade implications"
        route, _ = select_executable_route(question, "public")
        self.assertEqual(route, "league_recap")
        expected = {"intent": "league_recap", "engine_conclusion": "Existing fantasy analysis preserved.", "developer": {}}
        with patch("Scout.conversation.router.analyze_league", return_value=expected) as handler:
            answer = route_question(question, ScoutContext(), mode="public")
        handler.assert_called_once()
        self.assertEqual(answer["developer"]["athena_request"]["selected_route"], "league_recap")
        self.assertEqual(answer["developer"]["athena_request"]["execution_owner"], "athena_registered_specialist")
        self.assertEqual(answer["engine_conclusion"], expected["engine_conclusion"])


if __name__ == "__main__":
    unittest.main()
