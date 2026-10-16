"""Regression: Athena.request_execution -> specialist -> evidence -> league booster."""
from Athena.request_execution import AthenaRequest, execute_request

QUESTION = (
    "Compare Auston Matthews and Connor McDavid for the JHLPAA. "
    "Use their NHL performance, historical trends, playing styles, health and "
    "deployment considerations, then apply our league's scoring, roster and "
    "keeper rules. Which player offers greater fantasy value, and why?"
)

fantasy = execute_request(AthenaRequest(QUESTION, mode="fantasy"))
assert fantasy["intent"] == "league_player_comparison", fantasy["intent"]
meta = fantasy["developer"]["athena_request"]
assert meta["execution_owner"] == "athena_registered_specialist", meta
assert meta["selected_route"] == "league_player_comparison", meta
assert meta["evidence_readiness"] in {"ready", "partial"}, meta
application = fantasy["developer"]["league_application"]
assert application["scoring_detail"] == "points_only", application
assert application["competition_model"] == "total_points", application
assert len(application["verified_rates"]) == 2, application
assert application["verified_rates"]["Connor McDavid"] > application["verified_rates"]["Auston Matthews"]
text = fantasy["natural_language_response"]
assert "Connor McDavid has the stronger historical production case" in text
assert "3 active C slots" in text and "11 keeper slots" in text
assert "full keeper or trade valuation" in text
assert "Verified NHL statistical comparison" in text

public = execute_request(AthenaRequest("Compare Auston Matthews and Connor McDavid in the NHL.", mode="public"))
assert public["intent"] == "public_player_comparison", public["intent"]
assert "league_application" not in public.get("developer", {})

public_to_fantasy = execute_request(AthenaRequest(QUESTION, mode="public"))
assert public_to_fantasy["intent"] == "league_player_comparison", public_to_fantasy["intent"]
assert public_to_fantasy["developer"]["athena_request"]["selected_route"] == "league_player_comparison"
assert public_to_fantasy["developer"]["league_application"]["scoring_detail"] == "points_only"
assert "Verified NHL statistical comparison" in public_to_fantasy["natural_language_response"]

print("[PASS] Athena specialist routing, official NHL evidence, league lens and public isolation")
