"""Live intelligence consumption helpers for Scout runtime acceptance.

This module turns the RSS/source registry added in v0.5.5.3.0 into query-ready
Scout evidence. It remains network-safe by default: live HTTP reads only happen
when callers explicitly opt in or ATHENA_LIVE_RSS_NETWORK=1 is set. When network
is disabled, the deterministic validation feed is still exposed so Scout can
prove that RSS/event consumption is wired instead of reporting that no feed
exists.
"""
from __future__ import annotations

import os
import re
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

from Knowledge.Identity.registry import seed_identity_registry

from Knowledge.Events.live_sources import (
    LIVE_EVENT_SOURCE_VERSION,
    acquire_live_rss_events,
    acquire_live_rss_sample,
    discover_current_news,
    live_event_source_summary,
    seed_live_feed_registry,
)

LIVE_INTELLIGENCE_CONSUMPTION_VERSION = "0.6.4.11.1"

RECENT_EVENT_TERMS = {
    "recent", "latest", "today", "tonight", "yesterday", "news", "events",
    "injury", "injuries", "trade", "trades", "signing", "signings", "suspension",
    "rumor", "rumour", "transaction", "transactions", "update", "updates",
}

SPORT_TERMS = {
    "nhl": "nhl",
    "hockey": "nhl",
}


def _nhl_team_entities() -> list[Any]:
    registry = seed_identity_registry()
    return [
        entity for entity in registry.all_entities()
        if entity.entity_type == "team" and entity.sport.lower() == "hockey" and entity.league.lower() == "nhl"
    ]


def _name_in_text(name: str, text: str) -> bool:
    cleaned = " ".join(_tokens(name))
    hay = " ".join(_tokens(text))
    if not cleaned or not hay:
        return False
    return bool(re.search(r"(?:^|\s)" + re.escape(cleaned) + r"(?:$|\s)", hay))


def _requested_team_records(question: str) -> list[Dict[str, Any]]:
    text = str(question or "").lower()
    records: list[Dict[str, Any]] = []
    for entity in _nhl_team_entities():
        names = [entity.canonical_name, *entity.aliases]
        matched = [name for name in names if len("".join(_tokens(name))) >= 4 and _name_in_text(name, text)]
        if not matched:
            continue
        aliases = sorted({" ".join(_tokens(name)) for name in names if len("".join(_tokens(name))) >= 4})
        # Preserve phrases/nicknames, not arbitrary canonical-name tokens such as
        # "new" or "york", which would create broad false-positive matches.
        canonical_tokens = _tokens(entity.canonical_name)
        if canonical_tokens:
            aliases.append(canonical_tokens[-1])
        records.append({
            "entity_id": entity.entity_id,
            "canonical_name": entity.canonical_name,
            "aliases": sorted(set(aliases)),
            "matched_names": matched,
        })
    return records


def _requested_team_terms(question: str) -> set[str]:
    return {term for record in _requested_team_records(question) for term in record["aliases"]}


def _requested_team_discovery_queries(question: str) -> list[str]:
    return [record["canonical_name"] for record in _requested_team_records(question)]


def _requested_team_entities(question: str) -> set[str]:
    return {record["entity_id"] for record in _requested_team_records(question)}


EVENT_TYPE_QUERY_TERMS = {
    "trade": {"trade", "trades", "traded", "acquire", "acquired", "deal", "dealt", "swap"},
    "injury": {"injury", "injuries", "injured", "day", "day-to-day", "hurt"},
    "signing": {"signing", "signings", "signed", "contract"},
    "suspension": {"suspension", "suspended"},
    "transaction": {"transaction", "transactions", "waiver", "waivers", "claim", "claimed", "moved", "movement"},
}

CONFIRMED_TRADE_VERBS = {"acquire", "acquires", "acquired", "land", "lands", "landed", "trade", "trades", "traded", "send", "sends", "sent", "deal", "deals", "dealt"}
TRADE_ASSET_TERMS = {"pick", "picks", "prospect", "prospects", "rights", "forward", "winger", "defenseman", "defenceman", "center", "centre", "goalie", "goaltender", "player", "players"}
TRADE_ARTICLE_TERMS = {"rumblings", "rumors", "rumours", "grades", "grade", "report cards", "mock", "preview", "latest intel", "buzz", "tracker", "winners", "losers"}


def _is_confirmed_trade_item(event: Mapping[str, Any]) -> bool:
    """Return True only for concrete transaction items, not trade-rumor/grade articles."""
    title = str(event.get("title") or "")
    summary = str(event.get("summary") or "")
    text = f"{title} {summary}".lower()
    if any(term in text for term in TRADE_ARTICLE_TERMS):
        return False
    tokens = set(_tokens(text))
    has_trade_verb = bool(tokens & CONFIRMED_TRADE_VERBS)
    has_asset_context = bool(tokens & TRADE_ASSET_TERMS) or any(term in text for term in [" in exchange for ", " from ", " for no. ", " for the no. ", " for a ", " for "])
    has_two_sides = any(term in text for term in [" from ", " with ", " to ", " in exchange for ", " for "])
    return has_trade_verb and has_asset_context and has_two_sides


def _requested_event_types(question: str) -> set[str]:
    token_set = set(_tokens(question))
    requested: set[str] = set()
    for event_type, terms in EVENT_TYPE_QUERY_TERMS.items():
        if token_set & terms or any(term in (question or "").lower() for term in terms if "-" in term):
            requested.add(event_type)
    return requested


def _event_matches_filters(event: Mapping[str, Any], team_terms: set[str], type_terms: set[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    title = str(event.get("title") or "").lower()
    text = " ".join(str(event.get(k, "")) for k in ("title", "summary", "subject", "source_id")).lower()
    event_type = str(event.get("event_type") or "news").lower()
    matching_terms = {term for term in team_terms if _name_in_text(term, text)}
    if team_terms and not matching_terms:
        reasons.append("entity_mismatch")
    elif matching_terms:
        # A former/ex-team affiliation is historical context, not current-team news,
        # unless the requested team is independently mentioned elsewhere in the headline.
        historical_hits = sum(len(re.findall(rf"\b(?:former|ex)[ -]+(?:[^ ]+ ){{0,3}}{re.escape(term)}\b", title)) for term in matching_terms)
        title_hits = sum(len(re.findall(rf"\b{re.escape(term)}\b", title)) for term in matching_terms)
        if historical_hits and title_hits <= historical_hits:
            reasons.append("historical_affiliation_only")
    if type_terms and event_type not in type_terms:
        # RSS discovery items often carry the broad "news" label. A matching
        # headline is relevant evidence, but remains a reported news item.
        topical_news = event_type == "news" and bool(_requested_event_types(title) & type_terms)
        if not topical_news and not (event_type == "trade" and "transaction" in type_terms):
            reasons.append("event_type_mismatch")
        if topical_news and "trade" in type_terms and not _is_confirmed_trade_item(event):
            reasons.append("not_confirmed_transaction_item")
        if topical_news and "transaction" in type_terms and re.search(r"\b(?:a fit for|could join|should claim|may claim)\b", title):
            reasons.append("speculative_transaction_context")
    if not reasons and event_type == "trade" and ("trade" in type_terms or "transaction" in type_terms):
        if not _is_confirmed_trade_item(event):
            reasons.append("not_confirmed_transaction_item")
    return not reasons, reasons



def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def is_recent_event_query(question: str) -> bool:
    text = (question or "").lower()
    token_set = set(_tokens(text))
    event_words = token_set & RECENT_EVENT_TERMS
    team_words = bool(_requested_team_records(question)) or any(term in text for term in ("nhl", "hockey", "mcdavid", "matthews"))
    if event_words and team_words:
        return True
    if token_set & {"events", "news", "injuries", "trades", "transactions", "updates"}:
        return True
    if "last" in token_set and token_set & {"trade", "trades", "transaction", "transactions", "signing", "injury"}:
        return True
    return False


def _query_league(question: str) -> str:
    text = (question or "").lower()
    for term, league in SPORT_TERMS.items():
        if term in text:
            return league
    return "nhl"


def _event_to_dict(event: Any, *, source_mode: str) -> Dict[str, Any]:
    data = event.to_dict() if hasattr(event, "to_dict") else dict(event) if isinstance(event, Mapping) else {"title": str(event)}
    raw = data.get("raw_payload") if isinstance(data.get("raw_payload"), Mapping) else {}
    evidence = data.get("evidence") if isinstance(data.get("evidence"), list) else []
    first_evidence = evidence[0] if evidence and isinstance(evidence[0], Mapping) else {}
    title = str(data.get("title") or data.get("subject") or raw.get("title") or "Untitled event")
    summary = str(data.get("summary") or raw.get("summary") or title)
    url = str(data.get("url") or raw.get("url") or first_evidence.get("url") or "")
    published_at = str(data.get("published_at") or data.get("occurred_at") or raw.get("published_at") or first_evidence.get("observed_at") or "")
    feed_id = str(data.get("feed_id") or raw.get("feed_id") or "")
    source_display_name = str(data.get("source_display_name") or raw.get("source_display_name") or "")
    return {
        "event_id": data.get("event_id") or data.get("id") or title.lower().replace(" ", "_")[:80],
        "event_type": data.get("event_type") or "news",
        "sport": data.get("sport") or "nhl",
        "league": data.get("league") or "nhl",
        "source_id": data.get("source_id") or (data.get("source_ids") or ["trusted_newswire"])[0],
        "feed_id": feed_id,
        "source_display_name": source_display_name,
        "title": title,
        "summary": summary,
        "url": url,
        "published_at": published_at,
        "freshness_score": 0.72 if source_mode == "sample" else (0.88 if published_at else 0.58),
        "source_rank": 0.80,
        "source_mode": source_mode,
    }


def _linked_article_mentions_entity(event: Mapping[str, Any], team_terms: set[str], *, timeout_seconds: int = 4) -> bool:
    """Require the requested team to be central to a trusted linked article.

    A passing mention in a league-wide article or former-player story must not
    resurrect an RSS item already rejected for entity mismatch. Generic feed
    metadata may be enriched only when the article heading or opening context
    establishes the requested team as a primary subject.
    """
    url = str(event.get("url") or "").strip()
    if not url.lower().startswith(("https://", "http://")) or not team_terms:
        return False
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AthenaEngine/0.6.4.9.0 Evidence Enrichment"})
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            raw = response.read(750_000)
        html = raw.decode("utf-8", errors="replace")
        html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
        html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.I | re.S)
        headings = " ".join(re.findall(r"<(?:h1|title)\b[^>]*>(.*?)</(?:h1|title)>", html, flags=re.I | re.S))
        regions = re.findall(r"<(?:article|main)\b[^>]*>(.*?)</(?:article|main)>", html, flags=re.I | re.S)
        evidence_html = " ".join(regions) if regions else html
        heading_text = " ".join(re.sub(r"<[^>]+>", " ", headings).lower().split())
        body_text = " ".join(re.sub(r"<[^>]+>", " ", evidence_html).lower().split())
        opening = body_text[:2200]
        distinctive = {term for term in team_terms if term not in {"toronto", "edmonton", "montreal"}}
        canonical_phrases = {frozenset({"maple", "leafs", "toronto"}): "toronto maple leafs",frozenset({"oilers", "edmonton"}): "edmonton oilers",frozenset({"canadiens", "montreal", "habs"}): "montreal canadiens"}
        phrase = canonical_phrases.get(frozenset(team_terms))
        heading_match = bool((phrase and phrase in heading_text) or any(term in heading_text for term in distinctive))
        opening_mentions = sum(opening.count(term) for term in distinctive) + (opening.count(phrase) if phrase else 0)
        return heading_match or opening_mentions >= 2
    except Exception:
        return False


def _score_event(event: Mapping[str, Any], question: str) -> float:
    q = set(_tokens(question))
    hay = set(_tokens(" ".join(str(event.get(k, "")) for k in ("title", "summary", "event_type", "league"))))
    overlap = len(q & hay)
    recency_bonus = 0.2 if any(term in q for term in RECENT_EVENT_TERMS) else 0.0
    type_bonus = 0.15 if str(event.get("event_type") or "") in q else 0.0
    return round(min(1.0, 0.45 + overlap * 0.06 + recency_bonus + type_bonus), 4)


def _dedupe(events: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for event in events:
        key = str(event.get("url") or event.get("event_id") or event.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(dict(event))
    return result


STORY_CLUSTER_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "from", "at", "by", "is", "are", "was", "were",
    "nhl", "news", "report", "reports", "maple", "leafs", "toronto", "oilers", "edmonton", "canadiens", "montreal",
    "forward", "defenseman", "defenceman", "goalie", "team", "teams", "season", "next", "former", "among",
}


def _story_terms(event: Mapping[str, Any]) -> set[str]:
    text = " ".join(str(event.get(k, "")) for k in ("title", "summary"))
    return {token for token in _tokens(text) if len(token) >= 4 and token not in STORY_CLUSTER_STOPWORDS and not token.isdigit()}


def _same_story(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    a = _story_terms(left)
    b = _story_terms(right)
    if not a or not b:
        return False
    common = a & b
    # Two distinctive shared terms is enough for syndicated/reported variants
    # such as multiple outlets covering the same player transaction. Requiring
    # distinctive terms prevents the requested team name itself from clustering
    # unrelated stories.
    return len(common) >= 2 and (len(common) / max(1, min(len(a), len(b)))) >= 0.34


def _publisher_authority(event: Mapping[str, Any]) -> float:
    name = str(event.get("publisher") or event.get("source_display_name") or "").strip().casefold()
    if any(x in name for x in ("nhl.com", "sportsnet", "tsn", "espn", "associated press", "reuters", "the athletic", "new york times", "globe and mail")):
        return 0.95
    if any(x in name for x in ("journal", "gazette", "post", "news & observer", "dallas news", "toronto star")):
        return 0.88
    if any(x in name for x in ("hockey news", "hockey writers", "daily faceoff", "oilersnation", "mayorsmanor", "florida hockey now", "forever blueshirts")):
        return 0.78
    if any(x in name for x in ("rumors", "rumours", "heavy.com", "flohockey")):
        return 0.52
    return float(event.get("source_rank") or 0.68)

def _query_freshness(event: Mapping[str, Any], question: str) -> float:
    base = float(event.get("freshness_score") or 0.5)
    q = str(question or "").casefold()
    if not any(term in q for term in ("news", "latest", "recent", "today", "tonight", "update")):
        return base
    raw = str(event.get("published_at") or "").strip()
    if not raw:
        return base
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400.0)
    except Exception:
        return base
    if age_days <= 2: return max(base, 0.96)
    if age_days <= 7: return min(base, 0.82)
    if age_days <= 21: return min(base, 0.58)
    if age_days <= 45: return min(base, 0.35)
    return min(base, 0.15)

def _evidence_quality(event: Mapping[str, Any], question: str) -> float:
    relevance=float(event.get("relevance_score") or 0)
    freshness=_query_freshness(event, question)
    authority=_publisher_authority(event)
    return round(relevance*0.52 + freshness*0.30 + authority*0.18, 4)

def _select_story_diversity(events: Iterable[Mapping[str, Any]], limit: int, question: str = "") -> tuple[List[Dict[str, Any]], int]:
    prepared=[]
    for raw in events:
        item=dict(raw)
        item["query_freshness_score"]=_query_freshness(item, question)
        item["source_authority_score"]=_publisher_authority(item)
        item["evidence_quality_score"]=_evidence_quality(item, question)
        prepared.append(item)
    ranked = sorted(prepared, key=lambda item: float(item.get("evidence_quality_score") or 0), reverse=True)
    clusters: List[List[Dict[str, Any]]] = []
    for event in ranked:
        cluster = next((group for group in clusters if _same_story(event, group[0])), None)
        if cluster is None:
            clusters.append([event])
        else:
            cluster.append(event)
    selected: List[Dict[str, Any]] = []
    for cluster in clusters[: max(1, int(limit or 5))]:
        representative = dict(cluster[0])
        corroborating = cluster[1:]
        if corroborating:
            representative["corroborating_count"] = len(corroborating)
            representative["corroborating_sources"] = [
                {"title": item.get("title"), "url": item.get("url"), "source_display_name": item.get("source_display_name")}
                for item in corroborating
            ]
        selected.append(representative)
    return selected, sum(max(0, len(cluster) - 1) for cluster in clusters)


def _evidence_sufficiency(events: Iterable[Mapping[str, Any]], *, target_stories: int = 6, question: str = "") -> Dict[str, Any]:
    diversified, _ = _select_story_diversity(events, max(target_stories, 12), question)
    source_keys = {str(event.get("source_display_name") or event.get("source_id") or "").strip().lower() for event in diversified}
    source_keys.discard("")
    unique_stories = len(diversified)
    source_diversity = len(source_keys)
    sufficient = unique_stories >= max(3, target_stories) and source_diversity >= 2
    return {
        "sufficient": sufficient,
        "unique_story_count": unique_stories,
        "source_diversity": source_diversity,
        "target_story_count": max(3, target_stories),
        "reason": "adequate_unique_story_and_source_coverage" if sufficient else "insufficient_unique_story_or_source_coverage",
    }


def select_live_evidence(question: str, mode: str = "public", *, allow_network: Optional[bool] = None, limit: int = 5) -> Dict[str, Any]:
    """Return query-aware live event evidence for Scout/Reasoning.

    The function never raises for runtime usage. It returns explicit feed status,
    event counts, selected events and limitations so Scout can answer clearly.
    """
    question = str(question or "")
    league = _query_league(question)
    network_enabled = bool(allow_network) if allow_network is not None else os.environ.get("ATHENA_LIVE_RSS_NETWORK", "").strip().lower() in {"1", "true", "yes", "on"}
    feed_registry = seed_live_feed_registry()
    configured_feeds = [feed for feed in feed_registry.by_sport(league, league) if getattr(feed, "connector_type", "") == "live_rss"]
    events: List[Dict[str, Any]] = []
    source_mode = "network" if network_enabled else "sample"
    acquisition_errors: List[str] = []

    if network_enabled:
        for feed in configured_feeds:
            try:
                result = acquire_live_rss_events(feed.feed_id, allow_network=True)
                events.extend(_event_to_dict(event, source_mode="network") for event in result.events)
            except Exception as exc:  # noqa: BLE001 - live feeds must degrade gracefully
                acquisition_errors.append(f"{feed.feed_id}: {type(exc).__name__}: {exc}")
    team_terms = _requested_team_terms(question)
    requested_entities = _requested_team_entities(question)
    requested_types = _requested_event_types(question)
    strict_query = bool(team_terms or requested_types)
    allow_strict_sample = os.environ.get("ATHENA_LIVE_USE_SAMPLE_FOR_STRICT", "").strip().lower() in {"1", "true", "yes", "on"}
    if not events and (not strict_query or allow_strict_sample):
        try:
            sample = acquire_live_rss_sample()
            events.extend(_event_to_dict(event, source_mode="sample") for event in sample.events)
        except Exception as exc:  # noqa: BLE001
            acquisition_errors.append(f"sample_feed: {type(exc).__name__}: {exc}")

    deduped = _dedupe(events)
    filtered: List[Dict[str, Any]] = []
    ignored: List[Dict[str, Any]] = []
    for event in deduped:
        event["relevance_score"] = _score_event(event, question)
        matched, reasons = _event_matches_filters(event, team_terms, requested_types)
        if matched:
            filtered.append(event)
        else:
            ignored.append({"event_id": event.get("event_id"), "title": event.get("title"), "reasons": reasons})
    acquisition_escalation = "none"
    enriched_matches = 0
    if team_terms and network_enabled and not filtered:
        # RSS titles/summaries can be generic even when the linked article covers
        # the requested team. Escalate only through URLs supplied by the trusted
        # configured feeds and preserve strict same-entity matching.
        for event in deduped[:8]:
            matched, reasons = _event_matches_filters(event, set(), requested_types)
            if not matched:
                continue
            if _linked_article_mentions_entity(event, team_terms):
                event["entity_match_via"] = "trusted_linked_article"
                event["relevance_score"] = max(float(event.get("relevance_score") or 0), 0.82)
                filtered.append(event)
                enriched_matches += 1
        if enriched_matches:
            acquisition_escalation = "trusted_linked_article"

    discovery_matches = 0
    discovery_queries = _requested_team_discovery_queries(question)
    pre_discovery_sufficiency = _evidence_sufficiency(filtered, target_stories=min(6, max(3, int(limit or 5))), question=question)
    if team_terms and network_enabled and not pre_discovery_sufficiency["sufficient"] and discovery_queries:
        # Configured RSS is a source capability, not the boundary of current
        # information awareness. Escalate to current-news discovery for the
        # requested entity, then run the same entity/type relevance gates.
        for discovery_query in discovery_queries[:2]:
            try:
                discovered = discover_current_news(
                    f'"{discovery_query}" {league}',
                    sport=league,
                    league=league,
                    allow_network=True,
                    limit=max(36, int(limit or 5) * 4),
                )
            except Exception as exc:  # noqa: BLE001 - discovery must degrade gracefully
                acquisition_errors.append(f"current_news_discovery: {type(exc).__name__}: {exc}")
                continue
            for event in discovered:
                event["relevance_score"] = _score_event(event, question)
                matched, reasons = _event_matches_filters(event, team_terms, requested_types)
                if matched:
                    event["entity_match_via"] = "current_news_discovery"
                    filtered.append(event)
                    discovery_matches += 1
                else:
                    ignored.append({"event_id": event.get("event_id"), "title": event.get("title"), "reasons": reasons})
        if discovery_matches:
            acquisition_escalation = "current_news_discovery"

    post_discovery_sufficiency = _evidence_sufficiency(filtered, target_stories=min(6, max(3, int(limit or 5))), question=question)

    # Only apply strict entity/type filtering when the prompt actually named an
    # entity or event type. Broad prompts such as "recent NHL events" keep the
    # full recent-event sample/network set.
    candidate_events = filtered if (team_terms or requested_types) else deduped
    selected, corroborating_event_count = _select_story_diversity(candidate_events, max(1, int(limit or 5)), question)
    summary = live_event_source_summary()
    limitations: List[str] = []
    if not network_enabled:
        limitations.append("Live RSS network acquisition is disabled by default; set ATHENA_LIVE_RSS_NETWORK=1 or call with allow_network=True to fetch live feeds.")
    if strict_query and not network_enabled:
        limitations.append("Specific team/event lookups do not use validation sample events because sample data can create false matches.")
    if strict_query and network_enabled and not selected:
        limitations.append("Live feed acquisition ran, but no configured RSS item matched both the requested team/entity and event type.")
    if acquisition_errors:
        limitations.extend(acquisition_errors[:4])
    if not configured_feeds:
        limitations.append(f"No configured RSS feeds matched league {league}.")
    return {
        "version": LIVE_INTELLIGENCE_CONSUMPTION_VERSION,
        "source_version": LIVE_EVENT_SOURCE_VERSION,
        "question": question,
        "mode": mode,
        "league": league,
        "network_enabled": network_enabled,
        "feed_count": int(summary.get("live_rss_feed_count") or len(configured_feeds)),
        "configured_feeds": [getattr(feed, "feed_id", "") for feed in configured_feeds],
        "event_count": len(deduped),
        "selected_count": len(selected),
        "events_used": len(selected),
        "corroborating_event_count": corroborating_event_count,
        "events": selected,
        "confirmed_transaction_count": sum(1 for event in selected if str(event.get("event_type") or "").lower() == "trade" and _is_confirmed_trade_item(event)),
        "ignored_count": max(len(deduped) - len(selected), 0),
        "ignored_events": ignored[:10],
        "requested_team_terms": sorted(team_terms),
        "requested_entity_keys": sorted(requested_entities),
        "requested_event_types": sorted(requested_types),
        "status": "available" if selected else ("configured_no_matching_events" if (team_terms or requested_types) else "configured_no_events"),
        "source_mode": source_mode,
        "acquisition_escalation": acquisition_escalation,
        "enriched_match_count": enriched_matches,
        "discovery_match_count": discovery_matches,
        "discovery_queries": discovery_queries,
        "evidence_sufficiency": post_discovery_sufficiency,
        "limitations": limitations,
        "evidence_ledger": [
            {"source": "live_events", "evidence_count": len(selected), "contribution": 1.0 if selected else 0.0, "rationale": "Selected live/cached RSS event evidence for a time-sensitive Scout prompt."}
        ] if selected else [],
    }


def live_intelligence_diagnostics() -> Dict[str, Any]:
    summary = live_event_source_summary()
    selected = select_live_evidence("What recent NHL events are available?", mode="public", allow_network=False)
    return {
        "version": LIVE_INTELLIGENCE_CONSUMPTION_VERSION,
        "status": "pass" if selected.get("feed_count", 0) >= 1 and selected.get("selected_count", 0) >= 1 else "warn",
        "feed_count": selected.get("feed_count", 0),
        "selected_count": selected.get("selected_count", 0),
        "network_safe_by_default": summary.get("network_safe_by_default"),
        "network_enabled": selected.get("network_enabled"),
        "events": selected.get("events", []),
        "limitations": selected.get("limitations", []),
    }


__all__ = [
    "LIVE_INTELLIGENCE_CONSUMPTION_VERSION",
    "is_recent_event_query",
    "select_live_evidence",
    "live_intelligence_diagnostics",
]
