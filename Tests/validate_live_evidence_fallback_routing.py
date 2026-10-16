"""Regression validator for canonical live-event routing and evidence safeguards."""
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.context import ScoutContext
from Scout.conversation import router
from Knowledge.Events.live_sources import acquire_live_rss_sample, classify_rss_event_type
from Knowledge.Events.live_intelligence import _event_to_dict, _linked_article_mentions_entity
from Athena import live_event_specialist
from unittest.mock import patch


def check(name, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return bool(condition)


def no_matching_leafs_live(*args, **kwargs):
    return {
        "league": "nhl", "network_enabled": True, "feed_count": 2,
        "event_count": 1, "selected_count": 0, "events": [],
        "ignored_count": 1,
        "ignored_events": [{"event_id": "wrong-team", "title": "Canadiens roster update", "reasons": ["entity_mismatch"]}],
        "requested_team_terms": ["leafs", "maple", "toronto"],
        "requested_entity_keys": ["nhl.team.toronto_maple_leafs"],
        "requested_event_types": [], "status": "configured_no_matching_events",
        "source_mode": "network", "limitations": [], "evidence_ledger": [],
    }



class _FakeHTTPResponse:
    def __init__(self, body: str):
        self.body = body.encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, _limit=-1):
        return self.body


def _article_match(body: str) -> bool:
    event = {"url": "https://example.test/story"}
    with patch("Knowledge.Events.live_intelligence.urllib.request.urlopen", return_value=_FakeHTTPResponse(body)):
        return _linked_article_mentions_entity(event, {"maple", "leafs", "toronto"})


def main():
    with patch.object(live_event_specialist, "select_live_evidence", no_matching_leafs_live):
        answer = router.route_question("Recent Maple Leafs news", ScoutContext(), mode="public")
    natural = str(answer.get("natural_language_response") or "")
    dev = answer.get("developer") if isinstance(answer.get("developer"), dict) else {}
    trace = dev.get("inquiry_execution_trace") if isinstance(dev, dict) else {}
    trace = trace if isinstance(trace, dict) else {}
    invocation = trace.get("invocation") if isinstance(trace, dict) else {}
    selection = trace.get("selection") if isinstance(trace.get("selection"), dict) else {}
    live = dev.get("live_evidence") if isinstance(dev, dict) else {}
    live = live if isinstance(live, dict) else {}
    ignored = live.get("ignored_events") if isinstance(live, dict) else []
    ignored = ignored if isinstance(ignored, list) else []
    sample = acquire_live_rss_sample()
    sample_event = _event_to_dict(sample.events[0], source_mode="sample") if sample.events else {}
    ok = [
        check("version", ATHENA_VERSION == "0.7.10.20.0", ATHENA_VERSION),
        check("rss_url_preserved", bool(sample_event.get("url")), sample_event.get("url")),
        check("rss_date_preserved", bool(sample_event.get("published_at")), sample_event.get("published_at")),
        check("rss_feed_provenance", sample_event.get("feed_id") == "rss_nhl_news", sample_event.get("feed_id")),
        check("classification_not_false_injury", classify_rss_event_type("A hockey team coming to Austin or Houston?", "What you need to know about NHL expansion") == "news", classify_rss_event_type("A hockey team coming to Austin or Houston?", "What you need to know about NHL expansion")),
        check("linked_article_incidental_mention_rejected", not _article_match("<html><main><article><h1>Islanders update</h1><p>Mathew Barzal returned to practice.</p></article></main><aside>Related: Maple Leafs roster news</aside></html>"), "related-story mention must not attribute the event to Toronto"),
        check("linked_article_primary_entity_accepted", _article_match("<html><main><article><h1>Maple Leafs update</h1><p>The Toronto Maple Leafs changed their lineup.</p></article></main></html>"), "primary article content identifies Toronto"),
        check("release_name", RELEASE_NAME == "Athena Epic 4 Execution and Evidence Corrections", RELEASE_NAME),
        check("route", answer.get("intent") == "live_event_intelligence", answer.get("intent")),
        check("athena_specialist_invoked", invocation.get("owner") == "athena_registered_specialist" and invocation.get("completed") is True, invocation),
        check("no_matching_evidence_reported", live.get("status") == "configured_no_matching_events" and live.get("selected_count") == 0 and not live.get("events"), live.get("status")),
        check("requested_entity_provenance", "nhl.team.toronto_maple_leafs" in (live.get("requested_entity_keys") or []), live.get("requested_entity_keys")),
        check("mismatched_candidate_rejected", any("entity_mismatch" in (item.get("reasons") or []) for item in ignored), ignored),
        check("no_unrelated_substitution", "Canadiens" not in natural and "Montreal" not in natural, natural),
        check("missing_evidence_explained", "do not have a confirmed Maple Leafs event item" in natural, natural),
        check("execution_trace_matches_route", selection.get("route") == "live_event_intelligence", selection),
    ]
    print(f"Overall status: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1

if __name__ == "__main__":
    raise SystemExit(main())
