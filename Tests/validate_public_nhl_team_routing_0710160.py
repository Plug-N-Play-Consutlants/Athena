"""Regression guard for current-season NHL investigation identity/routing."""
from Athena.intent_resolution import select_executable_route
from Athena.public_team_performance import resolve_nhl_team_subject
from Scout.conversation.router import _is_team_performance_inquiry

QUESTIONS = (
    ("How do the Toronto Maple Leafs compare with the rest of the NHL in scoring, goal prevention and goaltending this season? What does that suggest management should investigate first?", "TOR"),
    ("Compare the Boston Bruins' offensive and defensive performance against NHL league averages. Are there verified weaknesses, or are the results too early to justify a roster change?", "BOS"),
)

def main():
    for question, expected in QUESTIONS:
        assert _is_team_performance_inquiry(question), question
        resolved = resolve_nhl_team_subject(question)
        assert resolved is not None and resolved[0] == expected, (question, resolved)
        route, owner = select_executable_route(question, "public")
        assert route == "public_current_season_team_investigation", (question, route, owner)
        assert owner == "canonical_nhl_team_investigation", (question, route, owner)
    print('PASS: canonical Toronto/Boston identity and Athena team-investigation route')

if __name__ == '__main__':
    main()
