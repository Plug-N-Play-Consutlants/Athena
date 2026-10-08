import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Athena.Inquiry.state import build_inquiry_state
from Athena.intent_planner import plan_capability
from Core.version import VERSION, RELEASE_HOTFIX

assert tuple(map(int, VERSION.split("."))) >= (0, 7, 7, 3, 4), VERSION

cases = [
    ("Could the Leafs get McDavid without trading Matthews?", "public_nhl_transaction_scenario", False),
    ("Could Toronto acquire McDavid without moving Matthews?", "public_nhl_transaction_scenario", False),
    ("How could the Leafs trade for McDavid without giving up Matthews?", "public_nhl_transaction_scenario", False),
    ("Is there a realistic way for Toronto to acquire McDavid without Matthews?", "public_nhl_organizational_plausibility", True),
]

for prompt, expected_route, plausibility in cases:
    state = build_inquiry_state(prompt, "public")
    plan = plan_capability(prompt, "public")
    assert state.operation == "transaction", (prompt, state.to_dict())
    assert state.organizations == ["Toronto Maple Leafs"], (prompt, state.to_dict())
    assert "Connor McDavid" in state.subjects, (prompt, state.to_dict())
    assert "Auston Matthews" in state.protected_assets, (prompt, state.to_dict())
    assert state.plausibility_requested is plausibility, (prompt, state.to_dict())
    assert plan and plan.route == expected_route, (prompt, plan, state.to_dict())

waived = "Pretend the salary cap is not an issue, how would the Leafs get Connor McDavid without trading Matthews?"
state = build_inquiry_state(waived, "public")
plan = plan_capability(waived, "public")
assert "salary_cap" in state.constraints_waived, state.to_dict()
assert plan and plan.route == "public_nhl_transaction_scenario", plan

print("PASS: Inquiry State owns transaction semantics across paraphrases; planner consumes normalized state.")
