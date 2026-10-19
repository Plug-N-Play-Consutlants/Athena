from Athena.intent_resolution import select_executable_route
from Athena.entry_policy import select_entry_route
from Athena.request_execution import _continued_question

trade = "What realistic trade options do the Toronto Maple Leafs have to strengthen their roster without sacrificing too much left-wing depth? Consider salary-cap implications, organizational assets and the next three seasons."
assert select_executable_route(trade, "public")[0] == "public_nhl_decision_inquiry"
follow = "Actually, I'm willing to give up a first-round pick if the player improves our chances over the next three seasons. But I still don't want to weaken left wing. Does that change your recommendations?"
assert select_executable_route(follow, "public")[0] == "public_nhl_decision_inquiry"
context = {"origin_intent": "public_nhl_decision_inquiry", "subject": "Toronto Maple Leafs"}
continued, status = _continued_question(follow, "public", context)
assert "Toronto Maple Leafs" in continued and status == "continued_nhl_decision_subject"
assert select_executable_route(continued, "public")[0] == "public_nhl_decision_inquiry"
assert _continued_question("What about the Oilers?", "public", context)[0] == "What about the Oilers?"
period = "In the JHLPAA, what is our current scoring period, when did it lock, and when does the next one begin? If a player was traded on Wednesday, explain which team receives his points for the rest of this week, when the acquiring team can use him, and how that transaction should appear in your weekly league report."
assert select_entry_route(period, "fantasy").route == "league_period_timing"
assert select_executable_route(period, "fantasy")[0] == "league_period_timing"
assert select_executable_route(period, "public")[0] == "league_period_timing"
assert select_entry_route("What's been happening in the JHLPAA recently? Give a league recap", "fantasy").route == "league_recap"
print("PASS question-first routing and bounded continuation")
