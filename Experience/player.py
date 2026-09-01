"""Player Experience builders for Epic 6B.

The Player Experience converts the canonical AthenaResponse foundation into a
richer, tabbed player profile contract. It remains client-agnostic: Scout can
render these sections as tabs/cards without knowing graph, provider, or sport
internals.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from Experience.models import PlayerIdentity, StatBox, UISection

PLAYER_EXPERIENCE_VERSION = "0.6.2.1.0"
PLAYER_EXPERIENCE_SECTION_TYPE = "player_experience"

ANALYSIS_TAB_SECTIONS = [
    "Executive Summary",
    "Playing Style",
    "Current Season",
    "Career Trend",
    "Organizational Impact",
    "Risk Factors",
    "Future Outlook",
]

STAT_BOX_ORDER = ["Goals", "Assists", "Points", "P/GP", "+/-"]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any, limit: Optional[int] = None) -> List[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit] if limit is not None else list(value)


def _card_map(answer: Dict[str, Any]) -> Dict[str, str]:
    cards: Dict[str, str] = {}
    for card in answer.get("cards") or []:
        if not isinstance(card, dict):
            continue
        label = _text(card.get("label") or card.get("title") or card.get("name"))
        value = _text(card.get("value") or card.get("summary") or card.get("text"))
        if label and value:
            cards[label.lower()] = value
    return cards


def _sentence_from_facts(answer: Dict[str, Any], tokens: List[str]) -> str:
    for fact in _as_list(answer.get("observed_facts"), 16):
        text = _text(fact)
        lower = text.lower()
        if text and any(token in lower for token in tokens):
            return text
    return ""


def _public_text(answer: Dict[str, Any]) -> str:
    return _text(answer.get("public_comment") or answer.get("natural_language_response") or answer.get("response_text") or answer.get("scout_message") or answer.get("engine_conclusion"))


def _paragraphs(answer: Dict[str, Any]) -> List[str]:
    text = _public_text(answer)
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part and part.strip()]


def _ordinal_pick(value: str) -> str:
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return str(value).strip()
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _clean_player_copy(text: str) -> str:
    text = _text(text)
    if not text:
        return ""
    # Public profile copy should read like analyst prose, not raw template output.
    def repl_draft(match: re.Match[str]) -> str:
        return f"entered the NHL as the {_ordinal_pick(match.group(2))} overall pick in the {match.group(1)} NHL Draft by {match.group(3)}"
    text = re.sub(r"entered the NHL as the (\d{4}) NHL Draft, (\d+)(?:st|nd|rd|th)? overall, ([^,]+)", repl_draft, text)
    text = text.replace("..", ".")
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def _first_paragraph_matching(answer: Dict[str, Any], tokens: List[str], fallback_index: Optional[int] = None) -> str:
    paras = _paragraphs(answer)
    for para in paras:
        lower = para.lower()
        if any(token in lower for token in tokens):
            return _clean_player_copy(para)
    if fallback_index is not None and 0 <= fallback_index < len(paras):
        return _clean_player_copy(paras[fallback_index])
    return ""


def _extract_current_production(answer: Dict[str, Any]) -> Dict[str, str]:
    """Parse current production prose into normalized stat fields.

    This does not invent season history. It only converts already-present local
    evidence such as '138 points in 82 games, with a 48-90 goal-assist split,
    1.683 points per game' into the structured stat contract.
    """
    text = _public_text(answer)
    result: Dict[str, str] = {}
    m = re.search(r"(\d+(?:\.\d+)?)\s+points\s+in\s+(\d+)\s+games", text, flags=re.I)
    if m:
        result["points"] = m.group(1)
        result["gp"] = m.group(2)
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s+goal[- ]assist split", text, flags=re.I)
    if m:
        result["goals"] = m.group(1)
        result["assists"] = m.group(2)
    m = re.search(r"(\d+(?:\.\d+)?)\s+points per game", text, flags=re.I)
    if m:
        result["ppg"] = m.group(1)
    return result


def _current_season_row(answer: Dict[str, Any], cards: Dict[str, str]) -> List[Dict[str, str]]:
    existing = answer.get("season_statistics") if isinstance(answer.get("season_statistics"), list) else []
    if existing:
        return existing
    parsed = _extract_current_production(answer)
    if not parsed:
        return []
    player = answer.get("player") if isinstance(answer.get("player"), dict) else {}
    return [{
        "season": _text(answer.get("season") or cards.get("season") or "Current"),
        "team": _text(player.get("team") or answer.get("team") or cards.get("team")),
        "gp": parsed.get("gp", ""),
        "g": parsed.get("goals", ""),
        "a": parsed.get("assists", ""),
        "pts": parsed.get("points", ""),
        "ppg": parsed.get("ppg", ""),
        "plus_minus": _text(cards.get("+/-") or cards.get("plus minus") or ""),
        "note": "current evidence row",
    }]


def _public_limitations(items: List[Any]) -> List[str]:
    public: List[str] = []
    replacements = {
        "Player Intelligence 4B.1 does not yet evaluate line deployment, power-play role, injuries, schedule strength, or future projection curves.": "Line deployment, power-play role, injury context, schedule strength, and projection curves are not fully attached to this player view yet.",
        "PIF Build 004 does not yet ingest live injuries, teammate deployment, or current official game logs automatically.": "Live injuries, teammate deployment, and official game-log feeds are not fully attached to this answer path yet.",
    }
    for item in items:
        text = _text(item)
        if not text:
            continue
        text = replacements.get(text, text)
        text = re.sub(r"\b(Player Intelligence|PIF Build|Build \d+|drop\w+)\b[^.]*", "the current public evidence path", text).strip()
        if text and text not in public:
            public.append(text)
    return public


def _clean_badge(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9 +\-/]", "", value).strip().upper()


def _title_badge(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9 +\-/★]", "", _text(value)).strip()
    if not text:
        return ""
    upper_map = {
        "CORE ASSET": "Core Asset",
        "FRANCHISE": "Franchise",
        "ELITE": "Elite",
        "FRANCHISE SUPERSTAR": "★★★★★ Franchise Superstar",
        "PRIME": "Prime Window",
        "PRIME WINDOW": "Prime Window",
        "SUPERSTAR": "Superstar",
        "BREAKOUT": "Breakout",
        "EMERGING": "Emerging",
        "PROSPECT": "Prospect",
        "VETERAN": "Veteran",
        "DECLINING": "Declining",
        "INJURY RISK": "Injury Risk",
    }
    normalized = upper_map.get(text.upper())
    if normalized:
        return normalized
    return " ".join(part.capitalize() if not part.isupper() else part for part in text.split())


def _format_contract(value: str) -> str:
    text = _text(value)
    if not text:
        return ""
    if re.search(r"year|season|expir|ufa|rfa|cap", text, flags=re.I):
        return text
    if re.fullmatch(r"\d+(?:\.0)?", text):
        years = int(float(text))
        return f"{years} year{'s' if years != 1 else ''} remaining"
    return text


def _production_band(answer: Dict[str, Any], cards: Dict[str, str]) -> str:
    return _text(cards.get("production band") or cards.get("production") or answer.get("production_band"))


def _career_tier(cards: Dict[str, str]) -> str:
    return _text(cards.get("career tier") or cards.get("public value") or cards.get("asset tier"))


def _player_name(answer: Dict[str, Any]) -> str:
    player = answer.get("player") if isinstance(answer.get("player"), dict) else {}
    title = _text(answer.get("title"))
    if "—" in title:
        title = title.split("—", 1)[0].strip()
    return _text(player.get("full_name") or player.get("name") or answer.get("player_name") or answer.get("subject") or title or "This player")


def _article(value: str) -> str:
    return "an" if _text(value)[:1].lower() in {"a", "e", "i", "o", "u"} else "a"


def _executive_brief(answer: Dict[str, Any], cards: Dict[str, str]) -> str:
    name = _player_name(answer)
    team = _text((answer.get("player") if isinstance(answer.get("player"), dict) else {}).get("team") or answer.get("team") or cards.get("team"))
    role = _text(cards.get("role") or cards.get("asset tier"))
    tier = _career_tier(cards)
    band = _production_band(answer, cards)
    ppg = _text(cards.get("ppg") or cards.get("p/gp") or _extract_current_production(answer).get("ppg"))
    leadership = _text(cards.get("leadership") or cards.get("captaincy") or cards.get("captain"))
    peak_goals = _text(cards.get("peak goals"))
    pieces: List[str] = []
    if tier:
        pieces.append(f"{name} should be evaluated first as {_article(tier)} {tier.lower()}, not as a single current-season stat line.")
    elif role:
        pieces.append(f"{name} profiles as {_article(role)} {role.lower()} based on the current Athena evidence pack.")
    else:
        pieces.append(f"{name} should be evaluated through the combined lens of identity, production, role, and trajectory evidence.")
    context_bits: List[str] = []
    if band:
        context_bits.append(f"current production sits in the {band.lower()} band")
    if ppg:
        context_bits.append(f"a {ppg} points-per-game signal")
    if peak_goals:
        context_bits.append(f"against a demonstrated {peak_goals}-goal peak")
    if context_bits:
        if len(context_bits) == 1:
            pieces.append("The current read is anchored by " + context_bits[0] + ".")
        else:
            pieces.append("The current read is that " + ", ".join(context_bits) + ".")
    impact_bits: List[str] = []
    if leadership:
        impact_bits.append(leadership.lower())
    if team:
        impact_bits.append(f"central importance to {team}")
    if role:
        impact_bits.append(role.lower())
    if impact_bits:
        pieces.append("His organizational value is anchored by " + ", ".join(impact_bits) + ".")
    pieces.append("The main caveat is that live deployment, injury, schedule, and projection evidence are still being attached, so Athena treats this as a bounded executive assessment rather than a complete forecast.")
    return _clean_player_copy(" ".join(pieces))


def _coverage_categories(answer: Dict[str, Any]) -> Dict[str, List[str]]:
    facts = " ".join(_text(item).lower() for item in _as_list(answer.get("observed_facts"), 20))
    current = []
    if "identity" in facts or _text(answer.get("title")):
        current.append("Identity profile")
    if "production" in facts or "point" in _public_text(answer).lower():
        current.append("Current production")
    if "context" in facts or "captain" in _public_text(answer).lower() or "franchise" in _public_text(answer).lower():
        current.append("Organizational context")
    if "contract" in facts or "contract" in str(answer.get("cards") or "").lower():
        current.append("Contract status")
    if "availability" in facts:
        current.append("Availability")
    if "trajectory" in facts or "trend" in _public_text(answer).lower():
        current.append("Trajectory signal")
    if not current:
        current = ["Identity profile", "Available production evidence"]
    planned = ["Live deployment", "Injury integration", "Schedule context", "Projection curves"]
    return {"current": current, "planned": planned}


def deterministic_player_badges(answer: Dict[str, Any], cards: Dict[str, str] | None = None) -> List[str]:
    """Derive a compact, non-duplicative player badge set."""
    cards = cards or _card_map(answer)
    explicit = answer.get("assessment_badges")
    raw: List[str] = []
    if isinstance(explicit, list):
        raw.extend(_text(item) for item in explicit if _text(item))
    for key in ("career tier", "public value", "role", "prime window", "trajectory"):
        value = _text(cards.get(key))
        if value:
            raw.append(value)

    searchable = " ".join([
        _text(answer.get("title")),
        _text(answer.get("public_comment")),
        _text(answer.get("engine_conclusion")),
        " ".join(_text(item) for item in _as_list(answer.get("observed_facts"), 16)),
    ]).lower()
    if not raw:
        if "franchise" in searchable and "superstar" in searchable:
            raw.append("Franchise Superstar")
        elif "franchise" in searchable:
            raw.append("Franchise")
        if "core asset" in searchable or "core" in searchable:
            raw.append("Core Asset")
        if "prime" in searchable:
            raw.append("Prime Window")
        elif "elite" in searchable:
            raw.append("Elite")

    # Collapse duplicate meanings. Career tier outranks generic franchise/elite badges.
    titled = []
    for item in raw:
        badge = _title_badge(item)
        if badge and badge not in titled:
            titled.append(badge)
    has_franchise_superstar = any("Franchise Superstar" in b for b in titled)
    compact: List[str] = []
    for badge in titled:
        low = badge.lower()
        if has_franchise_superstar and low in {"franchise", "elite", "superstar"}:
            continue
        if low == "elite" and any("franchise" in b.lower() for b in titled):
            continue
        if badge not in compact:
            compact.append(badge)
    if not any("Prime" in b for b in compact) and ("prime" in searchable or has_franchise_superstar):
        compact.append("Prime Window")
    return compact[:3]


def build_extended_player_identity(answer: Dict[str, Any], cards: Dict[str, str]) -> Dict[str, Any]:
    player = answer.get("player") if isinstance(answer.get("player"), dict) else {}

    def pick(*values: Any) -> str:
        for value in values:
            text = _text(value)
            if text:
                return text
        return ""

    jersey = pick(
        player.get("jersey_number"),
        answer.get("jersey_number"),
        answer.get("player_number"),
        cards.get("jersey number"),
        cards.get("number"),
    ).lstrip("#")

    identity = PlayerIdentity(
        full_name=pick(player.get("full_name"), player.get("name"), answer.get("player_name"), answer.get("subject"), answer.get("title"), "Player"),
        jersey_number=jersey,
        team=pick(player.get("team"), answer.get("team"), cards.get("team")),
        position=pick(player.get("position"), answer.get("position"), cards.get("position")),
        photo_url=pick(player.get("photo_url"), answer.get("photo_url")),
        status=pick(player.get("status"), answer.get("status"), cards.get("status")),
        assessment_badges=deterministic_player_badges(answer, cards),
    )
    extended = identity.__dict__.copy()
    extended.update({
        "shoots": pick(player.get("shoots"), cards.get("shoots")),
        "height": pick(player.get("height"), cards.get("height")),
        "weight": pick(player.get("weight"), cards.get("weight")),
        "age": pick(player.get("age"), cards.get("age")),
        "birthplace": pick(player.get("birthplace"), cards.get("birthplace"), cards.get("birth place")),
        "draft": pick(player.get("draft"), cards.get("draft")),
        "captaincy": pick(player.get("captaincy"), cards.get("captaincy"), cards.get("captain"), cards.get("alternate captain")),
        "contract": _format_contract(pick(player.get("contract"), cards.get("contract"))),
        "experience": pick(player.get("experience"), cards.get("experience")),
    })
    return extended


def build_current_stat_boxes(answer: Dict[str, Any], cards: Dict[str, str]) -> List[Dict[str, Any]]:
    stat_source = answer.get("stats") if isinstance(answer.get("stats"), dict) else {}
    parsed = _extract_current_production(answer)
    lookup = {
        "Goals": ["goals", "g"],
        "Assists": ["assists", "a"],
        "Points": ["points", "pts"],
        "P/GP": ["ppg", "p/gp", "points per game", "points/game"],
        "+/-": ["+/-", "plus minus", "plus_minus"],
    }
    boxes: List[Dict[str, Any]] = []
    for label in STAT_BOX_ORDER:
        value = ""
        for key in lookup[label]:
            value = _text(stat_source.get(key)) or _text(cards.get(key)) or _text(parsed.get(key))
            if value:
                break
        # Render the full header contract. Missing values should be visibly
        # unavailable instead of causing the whole box to disappear.
        boxes.append(StatBox(label=label, value=value or "—", context="current_season").__dict__)
    return boxes


def _section_summary(answer: Dict[str, Any], cards: Dict[str, str], title: str) -> str:
    lower = title.lower()
    name = _player_name(answer)
    if lower == "executive summary":
        return _executive_brief(answer, cards)
    if lower == "playing style":
        return _clean_player_copy(
            _text(cards.get("playing style"))
            or _first_paragraph_matching(answer, ["playing profile", "speed", "release", "playmaking", "shot", "transition", "two-way"], 2)
            or _sentence_from_facts(answer, ["style", "driver", "play", "scoring", "two-way"])
        )
    if lower == "current season":
        parsed = _extract_current_production(answer)
        band = _production_band(answer, cards)
        if parsed:
            pieces = []
            if parsed.get("points") and parsed.get("gp"):
                pieces.append(f"{parsed['points']} points in {parsed['gp']} games")
            if parsed.get("goals") and parsed.get("assists"):
                pieces.append(f"{parsed['goals']} goals and {parsed['assists']} assists")
            if parsed.get("ppg"):
                pieces.append(f"{parsed['ppg']} points per game")
            sentence = f"Current-season evidence shows {name} at " + ", ".join(pieces) + "."
            if band:
                sentence += f" Athena classifies that current production band as {band.lower()}."
            return _clean_player_copy(sentence)
        return _clean_player_copy(_text(cards.get("current season")) or _sentence_from_facts(answer, ["current", "season", "production"]))
    if lower == "career trend":
        tier = _career_tier(cards)
        three_year = _text(cards.get("3-year ppg") or cards.get("three-year ppg"))
        peak_goals = _text(cards.get("peak goals"))
        if tier or three_year or peak_goals:
            pieces = []
            if tier:
                pieces.append(f"career tier: {tier}")
            if three_year:
                pieces.append(f"three-year scoring signal: {three_year} P/GP")
            if peak_goals:
                pieces.append(f"documented peak: {peak_goals} goals")
            return _clean_player_copy(f"{name}'s trend should be read from the career baseline first: " + "; ".join(pieces) + ".")
        return _clean_player_copy(_text(cards.get("career trend")) or _text(cards.get("trend")) or _sentence_from_facts(answer, ["trend", "career", "baseline", "historical"]))
    if lower == "organizational impact":
        role = _text(cards.get("role") or cards.get("asset tier"))
        team = _text((answer.get("player") if isinstance(answer.get("player"), dict) else {}).get("team") or answer.get("team") or cards.get("team"))
        leadership = _text(cards.get("leadership") or cards.get("captaincy") or cards.get("captain"))
        bits = []
        if role:
            bits.append(f"{role.lower()} classification")
        if leadership:
            bits.append(leadership.lower())
        if team:
            bits.append(f"central roster importance to {team}")
        if bits:
            return _clean_player_copy(f"Organizationally, {name}'s value comes from " + ", ".join(bits) + ".")
        return _clean_player_copy(_text(cards.get("organizational impact")) or _sentence_from_facts(answer, ["organization", "organizational", "roster", "line", "window", "cap"]))
    if lower == "risk factors":
        value = _text(cards.get("risk factors")) or _text(cards.get("risk")) or _sentence_from_facts(answer, ["risk", "injury", "limitation", "decline", "workload"])
        if value:
            return _clean_player_copy(value)
        return "The risk read is incomplete until live injury, deployment, workload, and recent usage evidence are attached."
    if lower == "future outlook":
        value = _text(cards.get("future outlook")) or _text(cards.get("outlook")) or _sentence_from_facts(answer, ["future", "outlook", "projection", "prime"])
        if value:
            return _clean_player_copy(value)
        return "Future outlook remains bounded until multi-season trend, deployment, and projection evidence are attached."
    return ""


def build_analysis_tab(answer: Dict[str, Any], cards: Dict[str, str]) -> UISection:
    children = [
        UISection(
            section_id=f"player_analysis_{title.lower().replace(' ', '_')}",
            section_type="player_analysis_section",
            title=title,
            summary=_section_summary(answer, cards, title),
            default_open=True,
        )
        for title in ANALYSIS_TAB_SECTIONS
    ]
    return UISection(
        section_id="player_analysis_tab",
        section_type="player_experience_tab",
        title="Analysis",
        summary="Executive player briefing organized by meaning, not raw data.",
        data={"default": True},
        children=children,
        default_open=True,
    )


def build_stats_tab(answer: Dict[str, Any], cards: Dict[str, str]) -> UISection:
    insight = _executive_brief(answer, cards)
    trend_summary = _section_summary(answer, cards, "Career Trend") or "Multi-season trend evidence will populate as historical rows are attached."
    current_assessment = {
        key: value
        for key, value in {
            "production_band": _production_band(answer, cards),
            "ppg": _text(cards.get("ppg") or cards.get("p/gp") or _extract_current_production(answer).get("ppg")),
            "three_year_ppg": _text(cards.get("3-year ppg") or cards.get("three-year ppg")),
            "peak_goals": _text(cards.get("peak goals")),
            "career_tier": _career_tier(cards),
        }.items()
        if value not in (None, "")
    }
    seasons = _current_season_row(answer, cards)
    career = answer.get("career_statistics") if isinstance(answer.get("career_statistics"), dict) else {}
    return UISection(
        section_id="player_stats_tab",
        section_type="player_experience_tab",
        title="Stats",
        summary="Statistics-first view with Athena context.",
        data={
            "athena_insight": insight,
            "trend_summary": trend_summary,
            "current_assessment": current_assessment,
            "season_statistics": seasons,
            "career_statistics": career,
        },
        default_open=False,
    )


def build_player_experience_section(answer: Dict[str, Any]) -> UISection:
    cards = _card_map(answer)
    identity = build_extended_player_identity(answer, cards)
    stat_boxes = build_current_stat_boxes(answer, cards)
    return UISection(
        section_id="player_experience",
        section_type=PLAYER_EXPERIENCE_SECTION_TYPE,
        title=identity.get("full_name") or _text(answer.get("title")) or "Player Experience",
        summary="Structured player profile with identity, assessment, analysis, statistics, and evidence hooks.",
        data={
            "experience_version": PLAYER_EXPERIENCE_VERSION,
            "identity": identity,
            "stat_boxes": stat_boxes,
            "header_required_fields": ["photo_url", "full_name", "jersey_number", "team", "position", "assessment_badges"],
            "tabs": ["Analysis", "Stats"],
            "coverage": _coverage_categories(answer),
        },
        children=[build_analysis_tab(answer, cards), build_stats_tab(answer, cards)],
        default_open=True,
    )
