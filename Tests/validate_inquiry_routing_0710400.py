"""Focused acceptance for the regressions observed in Scout turns 198-205."""
from Athena.intent_planner import plan_capability
from Athena.intent_resolution import select_executable_route
from Athena.execution_registry import SPECIALISTS

cases = [
    "Toronto needs more scoring, but I don't want to weaken our left wing or give up our best young players. What trade options make sense, and what would we realistically have to sacrifice?",
    "Actually, I'm willing to give up a first-round pick if the player improves our chances over the next three seasons. But I still don't want to weaken left wing. Does that change your recommendations?",
    "Which Toronto players are approaching important contract decisions over the next two seasons? Who should management prioritize, and how would those decisions affect the team's cap flexibility and development pipeline?",
    "Revisit the Marchenko–Knies trade. What did each team gain and sacrifice at the time, what concerns did observers raise, and what plausible longer-term objectives might explain the decision? Separate confirmed evidence from speculation and subsequent outcomes.",
    "Suppose Toronto loses two regular forwards to injury for six weeks. How should management handle replacements using the Marlies, waivers, contracts, and any available cap relief? What would you need to verify before recommending specific moves?",
]
for q in cases:
    p = plan_capability(q, "public")
    assert p is not None and p.route == "public_nhl_decision_inquiry", (q, p)
    route, reason = select_executable_route(q, "public")
    assert route == "public_nhl_decision_inquiry", (q, route, reason)
assert SPECIALISTS["public_nhl_decision_inquiry"].mode == "public"
print(f"PASS: {len(cases)} professional routing cases; fantasy contract isolation")
