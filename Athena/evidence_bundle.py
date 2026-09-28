"""Question-scoped evidence acquisition owned by Athena's request boundary.

Scout selects presentation sections. Athena decides what evidence a request needs,
acquires what is currently available, and records explicit gaps before specialist
execution. Specialists may reason over this bundle but should not silently replace
missing evidence with unrelated sources.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict


def _is_cap_question(question: str) -> bool:
    q = question.casefold()
    return any(term in q for term in ("salary cap", "salary-cap", "cap hit", "cap space", "ltir", "retained salary"))


def _player_bundle(question: str, entity: Any = None) -> Dict[str, Any] | None:
    from Athena.public_identity import resolve_public_player
    from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
    from Knowledge.Intelligence.Public.player_evidence import player_evidence

    match = resolve_public_player(question) if entity is None else None
    resolved_entity = entity if entity is not None else (match.entity if match is not None else None)
    profile = profile_for_entity(resolved_entity) if resolved_entity is not None else None
    if profile is None:
        return None
    evidence = player_evidence(
        profile.display_name,
        team=profile.team,
        position=profile.position,
        birth_date=str(getattr(resolved_entity, "birth_date", "") or ""),
    )
    news = []
    news_status = "not_requested"
    q = question.casefold()
    wants_current = any(term in q for term in ("camp", "preseason", "pre-season", "recent", "latest", "injury", "current", "outlook", "uncertaint"))
    if wants_current:
        news_status = "no_identity_matched_items"
        try:
            from Knowledge.Events.live_sources import discover_current_news
            network = os.environ.get("ATHENA_LIVE_RSS_NETWORK", "").strip().lower() in {"1", "true", "yes", "on"}
            items = discover_current_news(f'"{profile.display_name}" NHL', sport="nhl", league="nhl", allow_network=network, limit=12)
            name_parts = [part.casefold() for part in profile.display_name.split() if len(part) > 2]
            for item in items:
                text = " ".join(str(item.get(key) or "") for key in ("title", "summary", "subject")).casefold()
                if name_parts and all(re.search(r"(?<!\w)" + re.escape(part) + r"(?!\w)", text) for part in name_parts):
                    news.append(item)
            if news:
                news_status = "available"
        except Exception as exc:  # live acquisition must remain bounded
            news_status = f"acquisition_error:{type(exc).__name__}"
    missing = []
    if not evidence:
        missing.append("official_nhl_player_record")
    if wants_current and not news:
        missing.append("dated_identity_matched_player_news")
    return {
        "subject": {"entity_id": resolved_entity.entity_id, "name": profile.display_name, "type": "player"},
        "official_player_record": evidence,
        "dated_news": news[:5],
        "news_status": news_status,
        "missing": missing,
    }


def build_request_evidence(question: str, *, mode: str, route: str | None) -> Dict[str, Any]:
    bundle: Dict[str, Any] = {
        "owner": "Athena.request_execution",
        "question": question,
        "route": route or "",
        "status": "not_required",
        "sources": [],
        "missing": [],
    }
    if mode != "public":
        return bundle

    if route == "public_player_comparison":
        from Knowledge.Intelligence.Entities.entity_registry import entities_by_type, searchable_names
        matched = []
        for entity in entities_by_type("player"):
            if any(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", question, re.I) for name in searchable_names(entity) if len(name) >= 4):
                if entity.entity_id not in {item.entity_id for item in matched}:
                    matched.append(entity)
        players = [item for entity in matched[:2] if (item := _player_bundle(question, entity)) is not None]
        if players:
            bundle["players"] = players
            for player in players:
                if player["official_player_record"] and "official_nhl_player_record" not in bundle["sources"]:
                    bundle["sources"].append("official_nhl_player_record")
                if player["dated_news"] and "dated_identity_matched_player_news" not in bundle["sources"]:
                    bundle["sources"].append("dated_identity_matched_player_news")
                bundle["missing"].extend(x for x in player["missing"] if x not in bundle["missing"])
            bundle["status"] = "ready" if len(players) >= 2 and not bundle["missing"] else "partial"
        return bundle

    if route in {"public_player_identity", "public_player_investigation", "public_player_temporal_comparison"}:
        player = _player_bundle(question)
        if player is not None:
            bundle.update({"status": "ready" if not player["missing"] else "partial", "player": player})
            bundle["sources"].append("official_nhl_player_record") if player["official_player_record"] else None
            bundle["sources"].append("dated_identity_matched_player_news") if player["dated_news"] else None
            bundle["missing"].extend(player["missing"])
        return bundle

    if _is_cap_question(question):
        from Knowledge.Sources.public_hockey_retrieval import retrieve_public_hockey_knowledge
        rules = retrieve_public_hockey_knowledge(question, mode="public_sports", limit=5, auto_build=False)
        bundle.update({
            "status": "partial",
            "salary_cap": {
                "rules": rules,
                "current_payroll": {"status": "unavailable", "reason": "No canonical current public payroll/cap ledger is registered."},
                "current_roster": {"status": "unavailable", "reason": "No canonical current public roster-to-cap composition is registered."},
            },
        })
        if rules.get("evidence"):
            bundle["sources"].append("public_hockey_knowledge_packs")
        bundle["missing"].extend(["current_public_payroll_cap_ledger", "current_public_roster_cap_composition"])
    return bundle
