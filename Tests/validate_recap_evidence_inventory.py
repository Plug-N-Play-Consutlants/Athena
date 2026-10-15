"""Verify that evidence inventory finds real canonical files without inflating coverage."""
import json
import tempfile
from pathlib import Path
from Athena.Investigation.recap_evidence_plan import audit_recap_evidence


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "player_production.json").write_text(json.dumps([
            {"season": 20252026, "goals": 30, "assists": 50}]), encoding="utf-8")
        (root / "player_pool_master.json").write_text(json.dumps({
            "fetched_at": "2026-10-14T00:00:00Z", "active_season": 2026,
            "records": [{"player_name": "Example"}]}), encoding="utf-8")
        report = audit_recap_evidence(root, 2)
        assert report["player_production"]["status"] == "candidate_present_unverified"
        assert report["roster"]["status"] == "candidate_present_unverified"
        assert report["player_production"]["candidate_metadata"][0]["seasons"] == ["20252026"]
        assert report["draft_assets"]["status"] == "not_available_in_output"
        assert "period attribution" in report["player_production"]["reason"]
    print("PASS: canonical artifact discovery and non-inflated period coverage")


if __name__ == "__main__":
    main()
