"""Impact text generation for deterministic live-event reasoning."""
from __future__ import annotations

from Knowledge.Events.models import EventRecord
from Engine.EventReasoning.classifier import affected_domains_for, normalized_type, significance_for
from Engine.EventReasoning.models import EventImpactAssessment


def _subject(event: EventRecord) -> str:
    return event.subject or "the subject"


def build_impact_assessment(event: EventRecord, confidence: float) -> EventImpactAssessment:
    etype = normalized_type(event.event_type)
    subject = _subject(event)
    significance = significance_for(etype, confidence)
    domains = affected_domains_for(etype)

    immediate_templates = {
        "trade": f"{subject} changes roster context immediately and may alter role, usage, and team depth.",
        "injury": f"{subject} introduces immediate availability risk and may force lineup or depth-chart changes.",
        "signing": f"{subject} creates a new contractual/team context that should be reflected in current outlook.",
        "extension": f"{subject} stabilizes longer-term team context and reduces near-term contract uncertainty.",
        "waiver": f"{subject} signals a roster-bubble or asset-management decision with immediate transaction implications.",
        "claim": f"{subject} changes team control and may create a new opportunity or depth role.",
        "recall": f"{subject} signals near-term NHL/team usage opportunity.",
        "assignment": f"{subject} reduces immediate top-level availability or role exposure.",
        "suspension": f"{subject} creates immediate absence and discipline-related availability risk.",
        "schedule_change": f"{subject} changes timing context and may affect rest, travel, or fantasy lineup planning.",
        "game_result": f"{subject} updates the competitive record and short-term team context.",
    }
    short_templates = {
        "trade": "Short term, Athena should reassess line fit, team depth, deployment, and fantasy value.",
        "injury": "Short term, Athena should monitor recovery status, replacements, and return-to-play signals.",
        "signing": "Short term, Athena should reassess depth chart fit and likely role.",
        "extension": "Short term, Athena should treat the asset as more stable within organizational planning.",
        "waiver": "Short term, Athena should watch whether the player clears, is claimed, or is reassigned.",
        "claim": "Short term, Athena should reassess opportunity under the claiming team's context.",
        "recall": "Short term, Athena should reassess availability, role, and lineup probability.",
        "assignment": "Short term, Athena should downgrade immediate availability and track recall triggers.",
        "suspension": "Short term, Athena should account for missed games and replacement usage.",
        "schedule_change": "Short term, Athena should update schedule-aware planning and lineup implications.",
        "game_result": "Short term, Athena should update form, standings, and matchup context.",
    }
    long_templates = {
        "trade": "Long term, the event may alter player trajectory, organizational direction, and future roster construction.",
        "injury": "Long term, repeated or severe injuries should affect durability and projection confidence.",
        "signing": "Long term, the contract or roster fit becomes part of the player's or team's planning horizon.",
        "extension": "Long term, the event reinforces asset retention and organizational identity.",
        "waiver": "Long term, the event may indicate declining organizational fit or asset depreciation.",
        "claim": "Long term, the claiming team may create a new development or usage path.",
        "recall": "Long term, recall outcomes can shift prospect status and organizational depth views.",
        "assignment": "Long term, assignment patterns may affect prospect status or roster security.",
        "suspension": "Long term, recurring discipline concerns should affect risk assessment.",
        "schedule_change": "Long term, schedule changes usually have limited strategic impact unless they cluster with fatigue or travel effects.",
        "game_result": "Long term, single results matter most when part of a broader trend or playoff/standings race.",
    }
    return EventImpactAssessment(
        immediate=immediate_templates.get(etype, f"{subject} creates a new event fact that should be tracked before conclusions are drawn."),
        short_term=short_templates.get(etype, "Short term, Athena should monitor corroborating evidence and related updates."),
        long_term=long_templates.get(etype, "Long term, Athena should retain the event as timeline evidence and reassess if related events appear."),
        affected_domains=domains,
        significance=significance,
    )
