"""Regression validator for v0.6.4.1.3 live evidence relevance and fallback routing."""
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.context import ScoutContext
from Scout.conversation import router
from Knowledge.Events.live_sources import acquire_live_rss_sample, classify_rss_event_type
from Knowledge.Events.live_intelligence import _event_to_dict, _linked_article_mentions_entity
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
    original = router.select_live_evidence
    try:
        router.select_live_evidence = no_matching_leafs_live
        answer = router.route_question("Recent Maple Leafs news", ScoutContext(), mode="public")
    finally:
        router.select_live_evidence = original
    natural = str(answer.get("natural_language_response") or "")
    dev = answer.get("developer") if isinstance(answer.get("developer"), dict) else {}
    runtime = dev.get("investigation_runtime") if isinstance(dev, dict) else {}
    selection = runtime.get("evidence_selection") if isinstance(runtime, dict) else {}
    items = selection.get("items") if isinstance(selection, dict) else []
    sample = acquire_live_rss_sample()
    sample_event = _event_to_dict(sample.events[0], source_mode="sample") if sample.events else {}
    ok = [
        check("version", ATHENA_VERSION == "0.6.4.1.3", ATHENA_VERSION),
        check("rss_url_preserved", bool(sample_event.get("url")), sample_event.get("url")),
        check("rss_date_preserved", bool(sample_event.get("published_at")), sample_event.get("published_at")),
        check("rss_feed_provenance", sample_event.get("feed_id") == "rss_nhl_news", sample_event.get("feed_id")),
        check("classification_not_false_injury", classify_rss_event_type("A hockey team coming to Austin or Houston?", "What you need to know about NHL expansion") == "news", classify_rss_event_type("A hockey team coming to Austin or Houston?", "What you need to know about NHL expansion")),
        check("linked_article_incidental_mention_rejected", not _article_match("<html><main><article><h1>Islanders update</h1><p>Mathew Barzal returned to practice.</p></article></main><aside>Related: Maple Leafs roster news</aside></html>"), "related-story mention must not attribute the event to Toronto"),
        check("linked_article_primary_entity_accepted", _article_match("<html><main><article><h1>Maple Leafs update</h1><p>The Toronto Maple Leafs changed their lineup.</p></article></main></html>"), "primary article content identifies Toronto"),
        check("release_name", RELEASE_NAME == "Current Information and Fantrax Connection Patch", RELEASE_NAME),
        check("route", answer.get("intent") == "live_event_intelligence", answer.get("intent")),
        check("news_strategy", runtime.get("strategy") == "news_update", runtime.get("strategy")),
        check("concise_strategy", runtime.get("depth") == "concise", runtime.get("depth")),
        check("fallback_tier", selection.get("tier") == "context_fallback", selection.get("tier")),
        check("same_entity_only", bool(items) and all("nhl.team.toronto_maple_leafs" in (i.get("entity_keys") or []) for i in items), items),
        check("no_unrelated_substitution", "Canadiens" not in natural and "Montreal" not in natural, natural),
        check("old_cold_stop_removed", "I do not have a confirmed Maple Leafs event item" not in natural, natural),
        check("freshness_disclosed", "background context, not recent news" in natural.lower(), natural),
        check("useful_fallback", "Toronto Maple Leafs context" in natural, natural),
        check("discovery_path", "Discovery:" in natural, natural),
    ]
    print(f"Overall status: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1

if __name__ == "__main__":
    raise SystemExit(main())
