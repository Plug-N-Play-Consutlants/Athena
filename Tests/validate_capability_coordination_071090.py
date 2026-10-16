"""Hermetic regression for bounded coordination and duplicate-key cleanup."""
from pathlib import Path
from Athena.inquiry_objectives import decompose_inquiry
from Athena.capability_coordination import coordinate_capabilities

def run():
    plan = decompose_inquiry("How could Toronto improve its roster while staying within the cap?")
    ledger = coordinate_capabilities(plan, "public_current_season_team_investigation", "public")
    assert ledger["primary_route"] == "public_current_season_team_investigation"
    assert ledger["supporting_executed"] == 0
    assert not ledger["multi_capability_synthesis_verified"]
    assert {"public_nhl_cap_reasoning", "public_nhl_transaction_scenario"} <= {x["route"] for x in ledger["supporting_candidates"]}
    for item in ledger["supporting_candidates"]:
        assert item["execution"] == "not_invoked"
    for name in ("request_execution.py", "inquiry_execution.py", "completion_assessment.py"):
        source = (Path(__file__).resolve().parents[1] / "Athena" / name).read_text()
        assert '"inquiry_objectives": objectives, "inquiry_objectives": objectives' not in source
    print("PASS: bounded capability coordination")
if __name__ == "__main__": run()
