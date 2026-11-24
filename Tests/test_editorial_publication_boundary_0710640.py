"""Phase 1: canonical editor-to-publication handoff guards both Scout roles."""
from pathlib import Path
from Scout.conversation.journalist_composition import (
    audit_publication, compose_editorial_publication, compose_journalist_report,
)


def research():
    return {
        "schema": "athena.league_period_research.v2", "league_name": "JHLPAA",
        "period": 7, "findings": [{"kind": "scoring_leader", "team": "Alpha",
                                    "period_points": 42, "top_score": True}],
        "editorial": {"trades": [{"transaction_id": "trade-1",
                                  "received": {"Alpha": ["Player A"], "Beta": ["Player B"]}}],
                      "trade_count": 1},
        "period_scoring_audit": {"status": "partial", "reconciled_teams": 2,
                                 "team_count": 14},
    }


def test_publication_matches_audited_draft():
    evidence = research()
    edition = compose_editorial_publication(research=evidence)
    assert edition["status"] == "pass"
    assert edition["report"] == compose_journalist_report(research=evidence)
    assert edition["audit"] == audit_publication(evidence, edition["report"])
    assert "Player A" in edition["report"] and "Player B" in edition["report"]
    assert evidence["editorial"]["trade_count"] == 1  # input untouched


def test_publication_fails_closed_on_inventory_count_disagreement():
    evidence = research()
    evidence["editorial"]["trade_count"] = 2
    edition = compose_editorial_publication(research=evidence)
    assert edition["status"] == "fail"
    assert "trade_inventory_count_mismatch" in edition["issues"]
    assert "Player A" not in edition["report"]
    assert edition["audit"]["expected_trades"] == 2


def test_router_uses_same_publication_boundary_for_journalist_and_auditor():
    source = (Path(__file__).resolve().parents[1] / "Scout" / "conversation" / "router.py").read_text()
    assert "from Scout.conversation.journalist_composition import compose_editorial_publication" in source
    assert "edition = compose_editorial_publication(research=athena_research)" in source
    assert "conclusion = edition[\"report\"]" in source
    assert 'edition["report"]' in source
    # The old unguarded auditor-side direct render must stay absent.
    assert ' + compose_journalist_report(research=athena_research)' not in source
