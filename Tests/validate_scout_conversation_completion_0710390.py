"""Normal Scout composition contract regression tests."""
from Scout.conversation.composition import compose_answer_payload

def test_team_gap_gets_investigation_and_adjacent_options():
    result=compose_answer_payload({"intent":"public_team_profile","title":"Toronto Maple Leafs", "natural_language_response":"Current roster evidence unavailable.", "known_limitations":["Current roster unverified"]})
    assert result["suggested_prompts"]
    assert result["continuation_options"][0]["kind"] == "investigate"
    assert any(x["kind"] == "adjacent" for x in result["continuation_options"])
    assert result["public_comment"]

def test_completed_team_still_has_adjacent_exit():
    result=compose_answer_payload({"intent":"public_team_profile","title":"Toronto Maple Leafs", "natural_language_response":"A verified team assessment."})
    assert all(x["kind"] != "investigate" for x in result["continuation_options"])
    assert any(x["kind"] == "thematic" for x in result["continuation_options"])

def test_existing_domain_followups_preserved():
    result=compose_answer_payload({"intent":"public_nhl_cap_reasoning", "natural_language_response":"The cap figure remains unverified.", "suggested_prompts":["Check the current cap figure"]})
    assert result["suggested_prompts"][0] == "Check the current cap figure"

def test_long_plain_text_readability_and_diagnostics():
    text="Athena considers the roster implications carefully. "*24
    result=compose_answer_payload({"intent":"unknown", "natural_language_response":text,"observed_facts":["Verified source"]})
    assert "\n\n" in result["public_comment"]
    assert result["diagnostics"]["observed_facts"] == ["Verified source"]
