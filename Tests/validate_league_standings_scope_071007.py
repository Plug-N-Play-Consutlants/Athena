"""Regression: league standings must not fall through to arbitrary team valuation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Scout.conversation.router import route_question
from Scout.conversation.context import ScoutContext


def run():
    ctx = ScoutContext()
    q = "Show me the JHLPAA standings at the end of Weeks 1 and 2. Identify which teams moved up or down, compare their scoring between periods, and explain the most significant changes."
    for mode in ("fantasy", "public"):
        result = route_question(q, ctx, mode=mode)
        assert result["intent"] == "league_period_standings", (mode, result.get("intent"))
        assert result["developer"]["requested_periods"] == [1, 2]
        assert "Alien Agenda" not in result.get("engine_conclusion", "")
        assert result.get("known_limitations")
    print("PASS: league standings inquiry scope preserved in fantasy/public modes")


if __name__ == "__main__":
    run()
