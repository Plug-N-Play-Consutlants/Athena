"""Provider-neutral player lifecycle and current-identity reconciliation.

A player's identity persists while lifecycle state changes. This module keeps
historical/developmental observations intact and lets newer, higher-authority
professional evidence establish the current organizational state.
"""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from Core.project_paths import OUTPUT_DIR, RAW_DIR
from Core.json_utils import read_optional_json
from Knowledge.Events.live_sources import discover_current_news
from Knowledge.Identity.registry import seed_identity_registry

LIFECYCLE_VERSION = "0.6.4.12.1"

LIFECYCLE_ORDER = {
    "prospect": 10,
    "draft_eligible": 20,
    "drafted": 30,
    "organizational_prospect": 40,
    "professional_player": 50,
    "nhl_roster_player": 60,
    "established_nhl_player": 70,
}

@dataclass
class LifecycleEvidence:
    source: str
    observed_at: str
    authority: float
    lifecycle_state: str = ""
    team: str = ""
    position: str = ""
    draft: str = ""
    summary: str = ""
    url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source, "observed_at": self.observed_at,
            "authority": self.authority, "lifecycle_state": self.lifecycle_state,
            "team": self.team, "position": self.position, "draft": self.draft,
            "summary": self.summary, "url": self.url, "metadata": dict(self.metadata),
        }


def _norm(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _iso_age_key(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            return 0.0


def _team_aliases() -> List[tuple[str, str, str]]:
    rows: List[tuple[str, str, str]] = []
    for entity in seed_identity_registry().all_entities():
        if entity.entity_type != "team" or entity.league.lower() != "nhl":
            continue
        abbr = ""
        for ext in entity.external_ids:
            if ext.namespace == "nhl:team":
                abbr = ext.value.upper()
        for name in (entity.canonical_name, *entity.aliases):
            if len(_norm(name)) >= 3:
                rows.append((_norm(name), abbr, entity.canonical_name))
    return sorted(rows, key=lambda row: len(row[0]), reverse=True)


def _team_from_text(text: str) -> tuple[str, str]:
    hay = f" {_norm(text)} "
    for alias, abbr, canonical in _team_aliases():
        if f" {alias} " in hay:
            return abbr, canonical
    return "", ""


def local_player_name_candidates(fragment: str) -> List[str]:
    """Return unique local player names matching a surname/name fragment.

    This is identity assistance only: it does not choose among multiple matches.
    Callers may use a sole candidate as a contextual assumption and should keep
    material ambiguity visible to the user.
    """
    wanted = _norm(fragment)
    if not wanted:
        return []
    names: Dict[str, str] = {}
    for filename in ("player_master.json", "player_profiles.json"):
        payload = read_optional_json(OUTPUT_DIR / filename) or []
        if isinstance(payload, Mapping):
            payload = payload.get("players") or payload.get("records") or []
        for row in payload if isinstance(payload, list) else []:
            if not isinstance(row, Mapping):
                continue
            row_name = str(row.get("player_name") or row.get("name") or row.get("full_name") or "").strip()
            norm_name = _norm(row_name)
            if row_name and (wanted == norm_name or wanted in norm_name.split()):
                names.setdefault(norm_name, row_name)
    csv_path = RAW_DIR / "Fantrax-Players-JHLPAA.csv"
    if csv_path.exists():
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    row_name = str(row.get("Player") or row.get("player") or row.get("Name") or row.get("name") or "").strip()
                    norm_name = _norm(row_name)
                    if row_name and (wanted == norm_name or wanted in norm_name.split()):
                        names.setdefault(norm_name, row_name)
        except Exception:
            pass
    return sorted(names.values())


def contextual_local_player_candidate(fragment: str) -> str:
    """Return a strong local default for an abbreviated player name, or empty.

    Multiple surname matches remain ambiguous unless one has a materially stronger
    current-interest signal in attached player evidence. This supports a correctable
    conversational assumption without turning a surname into a hard-coded identity.
    """
    candidates = local_player_name_candidates(fragment)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) < 2:
        return ""
    ranked: List[tuple[float, str]] = []
    for name in candidates:
        best = 0.0
        for item in _local_player_rows(name):
            meta = item.metadata if isinstance(item.metadata, dict) else {}
            raw = str(meta.get("Ros") or meta.get("Rostered") or "").strip().replace("%", "")
            try:
                best = max(best, float(raw))
            except ValueError:
                pass
        ranked.append((best, name))
    ranked.sort(reverse=True)
    if ranked[0][0] >= 20.0 and ranked[0][0] - ranked[1][0] >= 20.0:
        return ranked[0][1]
    return ""


def _local_player_rows(name: str) -> List[LifecycleEvidence]:
    wanted = _norm(name)
    evidence: List[LifecycleEvidence] = []
    for filename, authority in [("player_master.json", 0.76), ("player_profiles.json", 0.72)]:
        payload = read_optional_json(OUTPUT_DIR / filename) or []
        if isinstance(payload, Mapping):
            payload = payload.get("players") or payload.get("records") or []
        for row in payload if isinstance(payload, list) else []:
            if not isinstance(row, Mapping):
                continue
            row_name = row.get("player_name") or row.get("name") or row.get("full_name")
            if _norm(str(row_name or "")) != wanted:
                continue
            team = str(row.get("nhl_team") or row.get("team") or "").upper()
            position = str(row.get("position") or row.get("pos") or "")
            state = "nhl_roster_player" if team and team not in {"N/A", "(N/A)", "FA"} else "prospect"
            evidence.append(LifecycleEvidence(filename, "", authority, state, team, position, summary=f"Local player evidence for {row_name}.", metadata=dict(row)))
    csv_path = RAW_DIR / "Fantrax-Players-JHLPAA.csv"
    if csv_path.exists():
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    row_name = row.get("Player") or row.get("player") or row.get("Name") or row.get("name")
                    if _norm(str(row_name or "")) != wanted:
                        continue
                    team = str(row.get("Team") or row.get("team") or "").strip().upper()
                    position = str(row.get("Position") or row.get("position") or row.get("Pos") or "").strip()
                    state = "nhl_roster_player" if team and team not in {"N/A", "(N/A)", "FA"} else "prospect"
                    evidence.append(LifecycleEvidence("fantrax_player_export", "", 0.56, state, team, position, summary="Fantasy-provider identity/development observation.", metadata=dict(row)))
        except Exception:
            pass
    return evidence


def _news_evidence(name: str, *, allow_network: bool) -> List[LifecycleEvidence]:
    if not allow_network:
        return []
    stories: List[Mapping[str, Any]] = []
    seen_story_keys = set()
    # Broad identity discovery establishes current state. A second, player-performance
    # discovery pass gives the composer a fair chance to find camp/preseason/deployment
    # evidence instead of letting newer but less analytical contract/business stories
    # monopolize the current-player evidence set.
    for query in (f'"{name}" NHL', f'"{name}" camp preseason NHL'):
        try:
            discovered = discover_current_news(query, sport="nhl", league="nhl", allow_network=True, limit=18)
        except Exception:
            continue
        for story in discovered or []:
            if not isinstance(story, Mapping):
                continue
            key = str(story.get("url") or story.get("title") or "").strip().lower()
            if not key or key in seen_story_keys:
                continue
            seen_story_keys.add(key)
            stories.append(story)
    if not stories:
        return []
    wanted = _norm(name)
    evidence: List[LifecycleEvidence] = []
    for story in stories:
        text = " ".join(str(story.get(k) or "") for k in ("title", "summary"))
        if wanted not in _norm(text):
            continue
        team, canonical_team = _team_from_text(text)
        lower = text.lower()
        draft = ""
        draft_match = re.search(r"(?:selected|drafted|pick(?:ed)?)[^.;]{0,60}?\b(\d+)(?:st|nd|rd|th)?\s+overall", lower)
        if draft_match:
            pick = int(draft_match.group(1))
            suffix = "th" if 10 <= pick % 100 <= 20 else {1:"st",2:"nd",3:"rd"}.get(pick % 10,"th")
            draft = f"{pick}{suffix} overall"
        elif "first overall" in lower or "1st overall" in lower:
            draft = "1st overall"
        state = ""
        if team:
            state = "nhl_roster_player" if any(term in lower for term in ("roster", "season preview", "opening night", "lineup", "new faces", "maple leafs", "oilers", "nhl")) else "organizational_prospect"
        if draft and not state:
            state = "drafted"
        evidence.append(LifecycleEvidence(
            "current_news_discovery", str(story.get("published_at") or ""), 0.78,
            state, team, "", draft, str(story.get("title") or ""), str(story.get("url") or ""),
            {"canonical_team": canonical_team, "publisher": story.get("source_display_name") or "", "story": story},
        ))
    return evidence


def _score(item: LifecycleEvidence) -> tuple[float, float, int]:
    return (_iso_age_key(item.observed_at), float(item.authority), LIFECYCLE_ORDER.get(item.lifecycle_state, 0))


def resolve_player_lifecycle(name: str, *, allow_network: Optional[bool] = None) -> Dict[str, Any]:
    """Resolve a player's current lifecycle state without erasing older states."""
    cleaned = " ".join(str(name or "").strip().split())
    if not cleaned:
        return {"status": "no_query", "version": LIFECYCLE_VERSION, "name": "", "evidence": []}
    # Entity evidence must begin with a plausible person-name query. A matching
    # news headline is supporting evidence, never sufficient proof that an
    # arbitrary question string is a player identity.
    lowered = cleaned.casefold()
    question_starters = ("what ", "what's ", "who ", "who's ", "why ", "how ", "when ", "where ", "which ", "explain ", "define ", "tell me ")
    if lowered.startswith(question_starters) or cleaned.endswith("?"):
        return {"status": "not_person_query", "version": LIFECYCLE_VERSION, "name": cleaned, "evidence": []}
    if allow_network is None:
        allow_network = os.getenv("ATHENA_LIVE_RSS_NETWORK", "0").strip().lower() in {"1", "true", "yes", "on"}
    evidence = _local_player_rows(cleaned)
    evidence.extend(_news_evidence(cleaned, allow_network=bool(allow_network)))
    if not evidence:
        return {"status": "not_found", "version": LIFECYCLE_VERSION, "name": cleaned, "evidence": []}

    current_candidates = [item for item in evidence if item.lifecycle_state]
    # A recent headline containing a team name is not evidence that an
    # established roster player reverted to a prospect. Preserve the strongest
    # supported career state while reconciling current affiliation separately.
    current = max(current_candidates, key=lambda item: (LIFECYCLE_ORDER.get(item.lifecycle_state, 0), *_score(item))) if current_candidates else max(evidence, key=_score)
    team_candidates = [item for item in evidence if item.team]
    team_source = max(team_candidates, key=_score) if team_candidates else None
    position_candidates = [item for item in evidence if item.position]
    position_source = max(position_candidates, key=_score) if position_candidates else None
    draft_candidates = [item for item in evidence if item.draft]
    draft_source = max(draft_candidates, key=_score) if draft_candidates else None
    recent_news = sorted([item for item in evidence if item.source == "current_news_discovery"], key=_score, reverse=True)

    return {
        "status": "available",
        "version": LIFECYCLE_VERSION,
        "name": cleaned,
        "lifecycle_state": current.lifecycle_state or "prospect",
        "team": team_source.team if team_source else "",
        "position": position_source.position if position_source else "",
        "draft": draft_source.draft if draft_source else "",
        "current_identity_source": current.source,
        "evidence": [item.to_dict() for item in sorted(evidence, key=_score, reverse=True)],
        "recent_news": [item.to_dict() for item in recent_news[:6]],
        "developmental_evidence": [item.to_dict() for item in evidence if item.source != "current_news_discovery"],
        "limitations": [
            "Current identity is reconciled from available evidence; official roster/player feeds remain preferred when attached.",
            "Developmental statistics are included only when present in attached provider/output evidence; missing junior/college statistics are not invented.",
        ],
    }
