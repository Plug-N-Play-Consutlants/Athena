"""Registered execution contract and Scout ownership regression."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from unittest.mock import patch
from Athena.inquiry_execution import investigate, capability_catalog
from Athena.execution_registry import SPECIALISTS
from Athena.intent_resolution import select_executable_route

ROOT = Path(__file__).resolve().parents[1]
router = (ROOT / "Scout/conversation/router.py").read_text(encoding="utf-8")
assert "from Athena.inquiry_execution import answer as athena_answer" in router
route_block = router.split("def route_question(", 1)[1]
assert "orchestration_plan = scout_intent_plan(" not in route_block
assert "return _live_events_answer(ctx, raw_question, selected_mode)" not in route_block
catalog = capability_catalog()
assert len(catalog) == len(SPECIALISTS)
assert {r["route"] for r in catalog} == set(SPECIALISTS)

questions = [
 ("Is Matthews a generational player, considering his historical achievements, injuries and two-way impact?", "public", "public_player_historical_stature"),
 ("Is Auston Matthews a generational player? Evaluate the evidence for and against that classification, including his historical achievements, two-way play, injuries and comparable NHL players", "public", "public_player_historical_stature"),
 ("Compare Auston Matthews and Connor McDavid for the JHLPAA. Which player offers greater fantasy value?", "public", "league_player_comparison"),
 ("What is the latest NHL injury news?", "public", "live_event_intelligence"),
]
for question, mode, expected in questions:
    route, _ = select_executable_route(question, mode)
    assert route == expected, (question, route, expected)
    with patch("Athena.inquiry_execution.execute_specialist", return_value={"intent": expected}) as executor:
        outcome = investigate(question, object(), mode=mode)
        assert outcome["result"]["intent"] == expected
        assert outcome["capability_ledger"][0]["state"] == "executed"
        executor.assert_called_once()

outcome = investigate("Who are the most active managers?", object(), mode="fantasy")
assert outcome["status"] == "legacy_fallback"
assert outcome["result"] is None
print("Athena inquiry execution boundary PASS")
