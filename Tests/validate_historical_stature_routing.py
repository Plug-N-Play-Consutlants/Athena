"""Regression: historical player inquiry cannot fall into generic live injury news."""
from Athena.intent_planner import plan_capability
from Athena.intent_resolution import select_executable_route
from Athena.execution_registry import SPECIALISTS

question = "Is Auston Matthews a generational player? Evaluate the evidence for and against that classification, including his historical achievements, two-way play, injuries and comparable NHL players"
plan = plan_capability(question, "public")
assert plan.route == "public_player_historical_stature", plan
route, reason = select_executable_route(question, "public")
assert route == "public_player_historical_stature", (route, reason)
assert route in SPECIALISTS
assert SPECIALISTS[route].function == "execute_historical_stature"
assert select_executable_route("What's the biggest NHL injury news today?", "public")[0] != route
print("Historical stature specialist routing PASS")
