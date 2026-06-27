from Reasoning.primitives.player_context_builder import PlayerContextBuilder
ctx=PlayerContextBuilder().build([
{"type":"historical","statement":"Elite history"},
{"type":"temporal","statement":"Trending up"}
])
assert ctx["historical"]
assert ctx["temporal"]
print("Player Context PASS")
