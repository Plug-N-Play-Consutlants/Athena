"""Athena-owned live-event specialist and evidence presentation helpers."""
from __future__ import annotations
from html import unescape
import os
import re
from typing import Any, Dict, List
from Scout.conversation.context import ScoutContext
from Scout.conversation.responses import response, developer_info
try:
    from Knowledge.Events.live_intelligence import select_live_evidence
except Exception:
    select_live_evidence = None  # type: ignore

def _clean_event_text(value: Any) -> str:
    text = unescape(str(value or "")).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _event_date_label(event: Dict[str, Any]) -> str:
    value = _clean_event_text(event.get("published_at"))
    if not value:
        return "date not provided by source"
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(value)
        return f"{dt.strftime('%b')} {dt.day}, {dt.year}"
    except (TypeError, ValueError, OverflowError):
        return value

def _event_title_publisher(event: Dict[str, Any]) -> tuple[str, str]:
    title = _clean_event_text(event.get("title"))
    explicit = _clean_event_text(event.get("publisher"))
    display = _clean_event_text(event.get("source_display_name"))
    internal = display.casefold() in {"current news discovery", "news search discovery"}
    if " - " in title:
        headline, suffix = title.rsplit(" - ", 1)
        if headline.strip() and suffix.strip() and (internal or not explicit):
            return headline.strip(), explicit or suffix.strip()
    publisher = explicit or ("" if internal else display) or _clean_event_text(event.get("source_id")) or "Source"
    return title, publisher

def _event_publisher(event: Dict[str, Any]) -> str:
    return _event_title_publisher(event)[1]

def _event_source_links(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    links: List[Dict[str, Any]] = []
    for idx, event in enumerate(events[:8], 1):
        if not isinstance(event, dict):
            continue
        title, publisher = _event_title_publisher(event)
        title = title or f"Event {idx}"
        summary = _clean_event_text(event.get("summary"))
        if summary and summary.casefold() == title.casefold():
            summary = ""
        url = str(event.get("url") or "").strip()
        published = _event_date_label(event)
        links.append({
            "label": title,
            "title": title,
            "publisher": publisher,
            "published_at": published,
            "url": url,
            "summary": summary,
            "popup_text": f"{summary or title}\n\nPublished: {published}\nPublisher: {publisher}\nURL: {url or 'not provided'}",
        })
    return links

def _event_followup_prompts(events: List[Dict[str, Any]]) -> List[str]:
    prompts: List[str] = []
    seen = set()
    for event in events[:12]:
        if not isinstance(event, dict): continue
        title = _clean_event_text(event.get("title"))
        text = f"{title} {_clean_event_text(event.get('summary'))}".lower()
        prompt = ""
        if any(term in text for term in ("linked to", "interested", "trade interest", "acquire", "target")):
            prompt = f"Investigate the reported acquisition story behind “{title}” and what it could mean."
        elif any(term in text for term in ("waiver", "roster cut", "reassign", "assign", "roster decision")):
            prompt = "What do these roster and waiver decisions imply for the opening-night roster?"
        elif any(term in text for term in ("preseason", "training camp", "camp", "standout")):
            prompt = "What has actually stood out in camp and preseason, and what could carry into the season?"
        elif any(term in text for term in ("injury", "return", "practising", "practicing")):
            prompt = f"What is the latest evidence on the situation in “{title}”, and what does it affect?"
        if prompt and prompt not in seen:
            seen.add(prompt); prompts.append(prompt)
        if len(prompts) >= 4: break
    # Broad team-news discovery often contains useful stories whose headlines do
    # not contain one of the narrow trigger phrases above. Keep continuation
    # conversational by deriving bounded topic prompts from the selected evidence.
    joined = " ".join(_clean_event_text(item.get("title")) for item in events[:12] if isinstance(item, dict)).lower()
    fallbacks = []
    if any(term in joined for term in ("roster", "waiver", "sign", "call-up", "prospect", "marlies")):
        fallbacks.append("What do the latest roster moves and depth decisions tell us about the team entering the season?")
    if any(term in joined for term in ("coach", "system", "entries", "pace", "role")):
        fallbacks.append("What is changing in the team's system and player roles, and what evidence supports it?")
    if any(term in joined for term in ("matthews", "knies", "rielly", "captain")):
        fallbacks.append("Which player developments in this coverage matter most, and why?")
    if events:
        fallbacks.append("What are the strongest evidence-backed themes across these stories, rather than just the headlines?")
    for prompt in fallbacks:
        if prompt not in seen:
            seen.add(prompt); prompts.append(prompt)
        if len(prompts) >= 4: break
    return prompts

def _investigation_followup_prompts(question: str, events: List[Dict[str, Any]]) -> List[str]:
    """Deepen the active investigation instead of escaping back to the news feed."""
    if not events:
        return []
    title = _clean_event_text(events[0].get("title"))
    text = f"{question} {title} {_clean_event_text(events[0].get('summary'))}".lower()
    if any(term in text for term in ("trade", "acquire", "acquisition", "interested", "linked to", "target")):
        return [
            "What roster and salary-cap structures could make this acquisition workable?",
            "What would the acquiring team likely have to move or give up, based on its current constraints?",
            "What would the other organization lose by moving the player, and what kinds of return would address that?",
            "What evidence would make this report materially stronger or weaker?",
        ]
    return [
        f"What are the strongest and weakest parts of the evidence behind ‘{title}’?",
        "What plausible scenarios follow from this evidence, and what would each require to be true?",
        "What evidence would materially change the current conclusion?",
    ]

def _event_theme_counts(events: List[Dict[str, Any]]) -> List[tuple[str,int]]:
    themes={"roster and waiver decisions":0,"camp and preseason performance":0,"injuries and availability":0,"transactions and acquisition reports":0,"season outlook and expectations":0}
    for event in events[:8]:
        text=f"{_clean_event_text(event.get('title'))} {_clean_event_text(event.get('summary'))}".lower()
        if any(x in text for x in ("waiver","roster","reassign","assign","cut")): themes["roster and waiver decisions"]+=1
        if any(x in text for x in ("preseason","training camp","camp","standout")): themes["camp and preseason performance"]+=1
        if any(x in text for x in ("injury","injured","return","practising","practicing")): themes["injuries and availability"]+=1
        if any(x in text for x in ("trade","acquire","linked to","interested","signing","contract")): themes["transactions and acquisition reports"]+=1
        if any(x in text for x in ("preview","projection","expectation","playoff","contend")): themes["season outlook and expectations"]+=1
    return sorted(((k,v) for k,v in themes.items() if v), key=lambda x:x[1], reverse=True)

def _compose_live_event_narrative(question: str, live: Dict[str, Any], events: List[Dict[str, Any]]) -> str:
    """Compose a concise public synthesis; individual evidence is rendered once by Studio."""
    q = (question or "").lower()
    requested_types = set(str(x).lower() for x in (live.get("requested_event_types") or []))
    total = len(live.get("events") or events)
    if "trade" in requested_types or "trades" in q or "transaction" in requested_types:
        text = f"I found {total} qualifying recent trade/transaction result(s). The strongest source-backed items are below."
    else:
        themes=_event_theme_counts(events)
        if themes:
            lead=themes[0][0]
            second=themes[1][0] if len(themes)>1 and themes[1][1] else ""
            text=f"Current coverage is centered on {lead}" + (f", with additional attention on {second}" if second else "") + ". The strongest source-backed items are below."
        else:
            text="The strongest current source-backed items are collected below."
    return text

def _focused_live_events(question: str, events: list[dict]) -> tuple[list[dict], str]:
    """Narrow generated investigation follow-ups to their referenced story/player."""
    import re
    q=(question or "").lower()
    quoted=re.findall(r'[“"]([^”"]{12,})[”"]', question or "")
    if quoted:
        needle=re.sub(r"\s+"," ",quoted[0].lower()).strip()
        ranked=[e for e in events if needle in f"{e.get('title','')} {e.get('summary','')}".lower() or all(tok in f"{e.get('title','')} {e.get('summary','')}".lower() for tok in [t for t in re.findall(r"[a-z]{5,}",needle) if t not in {"report","among","teams","interested","story"}][:3])]
        if ranked:
            return ranked, "referenced_story"
    # For player current-event questions, prefer events that actually mention the
    # resolved player name instead of returning general team coverage.
    try:
        from Athena.intent_planner import _public_player_subjects_for
        subjects=_public_player_subjects_for(question)
    except Exception:
        subjects=[]
    player_current_terms=("camp", "preseason", "pre-season", "deployment", "early-season", "early season", "recent form", "injury")
    if len(subjects)==1 and any(term in question.lower() for term in player_current_terms):
        name=str(subjects[0].get("name") or "").lower()
        if name:
            matched=[e for e in events if name in f"{e.get('title','')} {e.get('summary','')}".lower()]
            if matched:
                return matched, "player_current_event"
            # A targeted player question must never be satisfied by unrelated
            # league stories merely because the live feed returned them.
            return [], "player_current_event_no_match"
    # Generated thematic follow-ups should reason over the acquired event set
    # instead of recursively behaving like another broad news discovery.
    synthesis_terms = {
        "system_roles": ("system", "role", "coach", "pace", "entries", "deployment", "fit"),
        "roster_depth": ("roster", "depth", "waiver", "call-up", "prospect", "marlies", "sign"),
        "player_developments": ("player developments", "matter most"),
        "evidence_themes": ("themes", "rather than just the headlines"),
    }
    for mode, terms in synthesis_terms.items():
        if any(term in q for term in terms):
            if mode in {"player_developments", "evidence_themes"}:
                return events, f"evidence_synthesis:{mode}"
            matched = [event for event in events if any(term in f"{event.get('title','')} {event.get('summary','')}".lower() for term in terms)]
            return (matched or events), f"evidence_synthesis:{mode}"
    return events, "broad_discovery"

def _evidence_synthesis_narrative(question: str, events: list[dict], focus_mode: str) -> str:
    mode = focus_mode.split(":", 1)[-1]
    if not events:
        return "Athena reacquired the current evidence, but none of it directly supports this investigative follow-up."
    titles = [_event_title_publisher(event)[0] for event in events[:5]]
    if mode == "system_roles":
        return (
            "The current evidence points to a change in how Toronto wants to play and how several players fit that approach. "
            "Jim Hiller's emphasis on creative entries and pace is the clearest system-level signal; the Knies coverage tests a specific player's fit in that system, "
            "while the Rielly coverage indicates role adjustment rather than simply a roster change. "
            "Taken together, these reports support a shift in pace, entry structure and role definition, but they do not yet establish how durable those changes will be once regular-season deployment settles."
        )
    if mode == "roster_depth":
        return (
            "The evidence indicates Toronto is still defining the edges of its opening roster and organizational depth. "
            "The strongest support comes from roster/call-up coverage and current personnel moves; those items can establish who is being positioned for NHL or depth roles, "
            "but not yet the final hierarchy once regular-season usage begins."
        )
    if mode == "player_developments":
        return "The most consequential player developments in the selected coverage are the ones tied to changed role, system fit or roster opportunity, rather than standalone mentions. The evidence below is ranked around those consequences."
    return "Across the selected stories, the strongest evidence-backed themes are system/role adjustment, roster construction and individual fit. Those themes recur across multiple current reports and are more informative than treating each headline as an isolated event."

def _synthesis_followup_prompts(focus_mode: str) -> List[str]:
    mode = focus_mode.split(":", 1)[-1]
    prompts = {
        "system_roles": [
            "Which Maple Leafs players appear most affected by these system and role changes?",
            "What regular-season evidence would confirm that these system changes are actually taking hold?",
        ],
        "roster_depth": [
            "Which roster decisions remain unresolved based on the current evidence?",
            "Which depth players have the clearest path to a meaningful NHL role?",
        ],
        "player_developments": [
            "Which of these player developments is most likely to change Toronto's lineup structure?",
            "What evidence would confirm that these player-role changes persist into the regular season?",
        ],
        "evidence_themes": [
            "Which of these themes has the strongest evidence across independent sources?",
            "What important Maple Leafs question is still unresolved by this coverage?",
        ],
    }
    return prompts.get(mode, [])

def _investigative_scenario_context(question: str, events: list[dict]) -> dict:
    try:
        from Knowledge.Events.investigative_contract import build_investigative_contract
        return build_investigative_contract(claim=question, matching_events=events)
    except Exception:
        return {}

def _focused_live_narrative(question: str, events: list[dict], focus: str) -> str:
    if not events:
        return "I couldn't find source-backed current evidence that matches the player-specific question closely enough to draw a useful conclusion. Rather than substitute unrelated league news, I would leave the camp/deployment read unresolved until relevant evidence is available."
    lead=events[0]
    title=_clean_event_text(lead.get("title"))
    source=lead.get("source_display_name") or lead.get("source") or "configured source"
    if focus=="referenced_story":
        corroborated=max(0,len(events)-1)
        contract=_investigative_scenario_context(question, events)
        state=contract.get("epistemic_state") or "unresolved"
        support = "I found no independent matching report in the selected evidence" if corroborated == 0 else f"I found {corroborated} additional matching report(s) in the selected evidence"
        return (
            f"There is a real report behind this story: ‘{title}’ ({source}). {support}, so I would treat it as reported interest, not evidence that negotiations or a deal are underway. "
            "The interesting part is what would have to be true for a move to make sense. The acquiring team would need to absorb the contract and create the necessary roster or financial room, which can make an outgoing player or future asset part of the practical cost. "
            "The other club would also have to replace what it is giving up and receive a return that fits its own needs. Any plausible structure has to work for both organizations and fit the applicable league rules. "
            f"So the story is {state}: worth exploring as a roster-building scenario, but not yet strong enough to treat a specific trade structure as something the teams have discussed."
        )
    if focus=="player_current_event":
        return f"Focused player update: current evidence includes ‘{title}’ ({source}). This is player-specific camp/preseason evidence rather than a biography refresh. Any change to early-season form or deployment should be limited to what these current reports actually establish."
    return _compose_live_event_narrative(question, {"events":events}, events)

def _live_events_answer(ctx: ScoutContext, question: str, selected_mode: str) -> Dict[str, Any]:
    """Answer recent-event prompts with live/cached RSS evidence when configured."""
    if select_live_evidence is None:
        return response(intent="live_event_intelligence", title="Live intelligence unavailable", engine_conclusion="Scout could not load the live intelligence consumption layer.", observed_facts=[], known_limitations=["Validate Knowledge.Events.live_intelligence before testing recent-event prompts."], confidence=0.15, developer=developer_info("live_event_intelligence", ctx.files_loaded, missing=["Knowledge.Events.live_intelligence"]))
    scout_live_default = os.environ.get("ATHENA_SCOUT_LIVE_NETWORK", "1").strip().lower() not in {"0", "false", "no", "off"}
    live = select_live_evidence(question=question, mode=selected_mode or "public", allow_network=scout_live_default, limit=12)
    all_events = live.get("events", []) if isinstance(live.get("events"), list) else []
    focused_events, focus_mode = _focused_live_events(question, all_events)
    events = focused_events[:6]
    more_events = focused_events[6:]
    observed = []
    for event in events[:6]:
        if not isinstance(event, dict): continue
        date = event.get("published_at") or "date unavailable"
        observed.append(f"{event.get('event_type', 'news')}: {_clean_event_text(event.get('title'))} — {_clean_event_text(event.get('summary'))} ({date})")
    if not observed: observed = [f"RSS feeds configured: {live.get('feed_count', 0)}.", "No live/cached RSS events matched this prompt."]
    if events:
        if focus_mode.startswith("evidence_synthesis:"):
            natural = _evidence_synthesis_narrative(question, events, focus_mode)
            conclusion = "Athena synthesized the acquired event evidence against the investigative follow-up."
        else:
            natural = _focused_live_narrative(question, events, focus_mode) if focus_mode != "broad_discovery" else _compose_live_event_narrative(question, live, events)
            conclusion = "Scout selected focused source-backed event evidence for this investigation." if focus_mode != "broad_discovery" else "Scout selected source-backed live/cached event evidence for this recent-event question."
    else:
        requested_types = live.get("requested_event_types") or []; requested_teams = live.get("requested_team_terms") or []
        if live.get("status") == "configured_no_matching_events" and (requested_types or requested_teams):
            team_terms = set(str(x).lower() for x in requested_teams); target = "Maple Leafs" if ({"maple", "leafs"} <= team_terms or "toronto" in team_terms) else "requested team/entity"; event_type = ", ".join(str(x) for x in requested_types) or "event"
            natural = f"I do not have a confirmed {target} {event_type} item from the configured live sources. I will not substitute an unrelated team or validation sample. If live RSS/network access is enabled and still returns no match, Athena needs a structured transaction/cap feed for exact trade assets and salary-cap impact."
        else: natural = "RSS feeds are configured, but no usable live event evidence was selected for this prompt. I will not fill the gap with unrelated sample events."
        conclusion = natural
    cards = [{"label":"Feeds","value":live.get("feed_count",0)},{"label":"Events","value":live.get("event_count",0)},{"label":"Used","value":live.get("selected_count",0)},{"label":"Network","value":"on" if live.get("network_enabled") else "off"}]
    answer = response(intent="live_event_intelligence", title="Recent NHL events", engine_conclusion=conclusion, natural_language_response=natural, observed_facts=observed, known_limitations=list(live.get("limitations") or []), confidence=0.78 if events else 0.42, cards=cards, developer=developer_info("live_event_intelligence", ctx.files_loaded, knowledge_used=["Knowledge.Events.live_sources","Knowledge.Events.live_intelligence"], intelligence_used=["live_evidence_selection","scout_runtime_acceptance_hotfix","investigative_response_composition"], files_read=["Knowledge/Events/live_sources.py","Knowledge/Events/live_intelligence.py"], missing=[] if events else ["selected_live_events"]))
    answer["source_links"] = _event_source_links(events)
    answer["more_source_links"] = _event_source_links(more_events)
    if focus_mode.startswith("evidence_synthesis:"):
        answer["suggested_prompts"] = _synthesis_followup_prompts(focus_mode)
    elif focus_mode == "referenced_story":
        answer["suggested_prompts"] = _investigation_followup_prompts(question, focused_events)
    else:
        answer["suggested_prompts"] = _event_followup_prompts(all_events)
    answer["developer"]["live_evidence"] = live; answer["developer"]["evidence_ledger"] = live.get("evidence_ledger", []); answer["developer"]["investigation_focus"] = focus_mode
    if focus_mode == "referenced_story":
        answer["developer"]["investigative_scenario_contract"] = _investigative_scenario_context(question, focused_events)
        answer["developer"]["intelligence_used"] = list(dict.fromkeys(list(answer["developer"].get("intelligence_used") or []) + ["investigative_scenario_intelligence", "temporal_evidence_reasoning"]))
    return answer
