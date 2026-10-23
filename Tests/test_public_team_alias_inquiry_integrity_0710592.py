"""Short public team aliases must resolve without hijacking other inquiries."""
from __future__ import annotations
import unittest
from Knowledge.Intelligence.Routing.request_router import analyze_public_request
from Scout.conversation.router import route_question
from Tools.repository_safe_cleanup import CleanupReport, CleanupCandidate
from Tools.studio_doctor_summary import format_doctor_summary


class TestPublicTeamAliasInquiryIntegrity(unittest.TestCase):
    def test_avs_team_identity_in_public(self):
        for question in ("Tell me about the Avs", "Who are the Avs?", "Tell me about Colorado"):
            with self.subTest(question=question):
                route = analyze_public_request(question)
                self.assertEqual(route.route, "team_intelligence")
                self.assertEqual(route.entities[0].entity.entity_id, "nhl.team.colorado_avalanche")
                answer = route_question(question, mode="public")
                self.assertEqual(answer.get("intent"), "public_team_profile")
                self.assertIn("Colorado Avalanche", answer.get("title", ""))

    def test_avs_vs_leafs_distinct_teams(self):
        route = analyze_public_request("Compare the Avs and Leafs")
        self.assertEqual(route.route, "team_comparison")
        self.assertEqual({x.entity.entity_id for x in route.entities if x.entity}, {
            "nhl.team.colorado_avalanche", "nhl.team.toronto_maple_leafs"
        })
        answer = route_question("Compare the Avs and Leafs", mode="public")
        self.assertEqual(answer.get("intent"), "public_team_comparison")
        self.assertIn("Colorado Avalanche", answer.get("title", ""))
        self.assertIn("Toronto Maple Leafs", answer.get("title", ""))

    def test_doctor_startup_message_unambiguous(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
        self.assertIn("Automatic startup inspection: OBSERVE ONLY", source)
        self.assertIn("approval requested only for safe candidates", source)
        report = CleanupReport("v", "now", ".", False,
            [CleanupCandidate("old.patch", "legacy_patch", "manual review", "review")],
            [], [], [], [], "report.json")
        summary = " ".join(format_doctor_summary(report))
        self.assertIn("No safe cleanup candidates", summary)
        self.assertIn("no action or confirmation required", summary)
        self.assertIn("never deleted automatically", summary)

    def test_ove_is_not_improve(self):
        question = "Where could Waterbury Wolverines improve its roster?"
        answer = route_question(question, mode="public")
        self.assertEqual(answer.get("intent"), "fantasy_roster_diagnostic")
        self.assertIn("Waterbury Wolverines", answer.get("title", ""))
        self.assertNotIn("Ovechkin", answer.get("title", ""))
        ove = route_question("Who is Ovi?", mode="public")
        self.assertEqual(ove.get("intent"), "public_player_profile")
        self.assertIn("Ovechkin", ove.get("title", ""))


if __name__ == "__main__":
    unittest.main()
