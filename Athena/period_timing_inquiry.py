"""Question-first JHLPAA period/lock inquiry. No archived recap substitution."""
from __future__ import annotations
from typing import Any
from Scout.conversation.responses import response, developer_info


def execute_period_timing(ctx: Any, question: str) -> dict:
    # Do not infer schedule from a Week 2 archive, wall clock, or an IR/roster
    # snapshot. Fantrax schedule/rule evidence is needed for actual timestamps.
    facts = ["An archived weekly standings snapshot does not establish the current scoring period or its lineup lock."]
    natural = (
        "I cannot yet verify the JHLPAA's current scoring-period boundaries, "
        "lineup-lock timestamp or next period's start from authenticated period schedule and league settings. "
        "The archived Week 2 recap is not an answer to this timing question. "
        "A Wednesday trade's recorded time must be compared with the verified lock and the league's transaction-effective rules. "
        "If JHLPAA's deferred-after-lock policy is confirmed for this season, a trade recorded after the current lock "
        "does not retroactively transfer this week's points: the original team retains this period's scoring "
        "and the acquiring team can use the player starting with the next eligible period. "
        "Before lock, or under different effective-date settings, the outcome may differ. "
        "The weekly report should distinguish the trade announcement from the period in which its competitive impact begins, "
        "and should not credit the acquiring club with points earned for the prior club."
    )
    limitations = [
        "Current and next period's verified Fantrax schedule, eligible game times and configured lock offset not acquired.",
        "Current-season league trade-effective rules and exact transaction timestamp not independently verified.",
    ]
    result = response(intent="league_period_timing", title="JHLPAA: scoring period and transaction timing",
        engine_conclusion=natural, natural_language_response=natural,
        observed_facts=facts, known_limitations=limitations, confidence=.45,
        developer=developer_info("league_period_timing", getattr(ctx, "files_loaded", []),
            intelligence_used=["period_timeline_contract", "question_first_temporal_routing"], missing=limitations))
    result.setdefault("developer", {})["period_timing"] = {
        "schedule_verified": False, "rules_verified": False,
        "current_period": None, "current_lock": None, "next_period_start": None,
        "no_archive_substitution": True,
    }
    return result
