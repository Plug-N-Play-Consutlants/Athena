from __future__ import annotations

import unittest

from Athena.diagnostic_intent import is_diagnostic_inquiry
from Athena.intent_resolution import select_executable_route
from Scout.conversation.router import route_question


class DiagnosticRoutingTests(unittest.TestCase):
    def test_plain_execution_questions_are_diagnostic_without_engine_name(self) -> None:
        for question in (
            "What intelligence modules executed?",
            "Which capabilities were used?",
            "What evidence did you use?",
        ):
            with self.subTest(question=question):
                self.assertTrue(is_diagnostic_inquiry(question))
                self.assertEqual(
                    select_executable_route(question, "public")[0],
                    "athena_runtime_diagnostics",
                )

    def test_hockey_evidence_question_keeps_diagnostic_ownership(self) -> None:
        question = "What evidence did you use to answer about NHL icing?"
        self.assertEqual(
            select_executable_route(question, "public")[0],
            "athena_runtime_diagnostics",
        )
        answer = route_question(question, mode="public")
        developer = answer.get("developer") or {}
        self.assertEqual(answer.get("intent"), "athena_runtime_diagnostics")
        self.assertIn("Athena.execution_registry", developer.get("knowledge_used", []))
        self.assertFalse(
            any(
                "rulebook" in str(source).lower() or "nhlpa" in str(source).lower()
                for source in developer.get("knowledge_used", [])
            )
        )

    def test_public_and_fantasy_contexts_return_athena_trace_without_prior_turn_claim(self) -> None:
        for mode in ("public", "fantasy"):
            with self.subTest(mode=mode):
                answer = route_question("What intelligence modules executed?", mode=mode)
                developer = answer.get("developer") or {}
                trace = developer.get("inquiry_execution_trace") or {}

                self.assertEqual(answer.get("intent"), "athena_runtime_diagnostics")
                self.assertEqual(
                    (developer.get("athena_request") or {}).get("selected_route"),
                    "athena_runtime_diagnostics",
                )
                self.assertEqual(trace.get("schema"), "athena.inquiry_trace.v1")
                self.assertEqual(
                    (trace.get("selection") or {}).get("route"),
                    "athena_runtime_diagnostics",
                )
                self.assertTrue((trace.get("invocation") or {}).get("completed"))
                evidence = trace.get("evidence") or {}
                self.assertIsInstance(evidence.get("sources"), list)
                self.assertIsInstance(evidence.get("missing"), list)
                self.assertIn(
                    "prior_turn_execution_trace_unavailable",
                    answer.get("known_limitations", []),
                )
                self.assertNotIn("runtime_trace", developer)
                self.assertIn("Athena.execution_registry", developer.get("knowledge_used", []))
                self.assertFalse(
                    any(
                        "rulebook" in str(source).lower() or "nhlpa" in str(source).lower()
                        for source in developer.get("knowledge_used", [])
                    )
                )


if __name__ == "__main__":
    unittest.main()
