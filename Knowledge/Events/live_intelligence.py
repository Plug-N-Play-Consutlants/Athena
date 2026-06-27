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
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

from Knowledge.Events.live_sources import (
    LIVE_EVENT_SOURCE_VERSION,
    acquire_live_rss_events,
    acquire_live_rss_sample,
    live_event_source_summary,
    seed_live_feed_registry,
)

LIVE_INTELLIGENCE_CONSUMPTION_VERSION = "0.5.5.5.16"

RECENT_EVENT_TERMS = {
    "recent", "latest", "today", "tonight", "yesterday", "news", "events",
    "injury", "injuries", "trade", "trades", "signing", "signings", "suspension",
    "rumor", "rumour", "transaction", "transactions", "update", "updates",
}

SPORT_TERMS = {
    "nhl": "nhl",
    "hockey": "nhl",
    "leafs": "nhl",
    "maple leafs": "nhl",
    "oilers": "nhl",
    "edmonton": "nhl",
    "toronto": "nhl",
}

TEAM_QUERY_TERMS = {
    "maple_leafs": {"maple", "leafs", "toronto"},
    "oilers": {"oilers", "edmonton"},
    "canadiens": {"canadiens", "montreal", "habs"},
}

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


def _requested_team_terms(question: str) -> set[str]:
    text = (question or "").lower()
    found: set[str] = set()
    for terms in TEAM_QUERY_TERMS.values():
        if any(term in text for term in terms):
            found.update(terms)
    return found


def _requested_event_types(question: str) -> set[str]:
    token_set = set(_tokens(question))
    requested: set[str] = set()
    for event_type, terms in EVENT_TYPE_QUERY_TERMS.items():
        if token_set & terms or any(term in (question or "").lower() for term in terms if "-" in term):
            requested.add(event_type)
    return requested


def _event_matches_filters(event: Mapping[str, Any], team_terms: set[str], type_terms: set[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    text = " ".join(str(event.get(k, "")) for k in ("title", "summary", "subject", "source_id")).lower()
    event_type = str(event.get("event_type") or "news").lower()
    if team_terms and not any(term in text for term in team_terms):
        reasons.append("entity_mismatch")
    if type_terms and event_type not in type_terms:
        if not (event_type == "trade" and "transaction" in type_terms):
            reasons.append("event_type_mismatch")
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
    team_words = any(term in text for term in ("nhl", "hockey", "leafs", "maple leafs", "oilers", "canadiens", "mcdavid", "matthews"))
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
    title = str(data.get("title") or data.get("subject") or "Untitled event")
    summary = str(data.get("summary") or title)
    return {
        "event_id": data.get("event_id") or data.get("id") or title.lower().replace(" ", "_")[:80],
        "event_type": data.get("event_type") or "news",
        "sport": data.get("sport") or "nhl",
        "league": data.get("league") or "nhl",
        "source_id": data.get("source_id") or "trusted_newswire",
        "title": title,
        "summary": summary,
        "url": data.get("url") or "",
        "published_at": data.get("published_at") or data.get("event_time") or "",
        "freshness_score": 0.72 if source_mode == "sample" else 0.88,
        "source_rank": 0.80,
        "source_mode": source_mode,
    }


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
    # Only apply strict entity/type filtering when the prompt actually named an
    # entity or event type. Broad prompts such as "recent NHL events" keep the
    # full recent-event sample/network set.
    candidate_events = filtered if (team_terms or requested_types) else deduped
    selected = sorted(candidate_events, key=lambda item: (float(item.get("relevance_score") or 0), float(item.get("freshness_score") or 0)), reverse=True)[: max(1, int(limit or 5))]
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
        "events": selected,
        "confirmed_transaction_count": sum(1 for event in selected if str(event.get("event_type") or "").lower() == "trade" and _is_confirmed_trade_item(event)),
        "ignored_count": max(len(deduped) - len(selected), 0),
        "ignored_events": ignored[:10],
        "requested_team_terms": sorted(team_terms),
        "requested_event_types": sorted(requested_types),
        "status": "available" if selected else ("configured_no_matching_events" if (team_terms or requested_types) else "configured_no_events"),
        "source_mode": source_mode,
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
