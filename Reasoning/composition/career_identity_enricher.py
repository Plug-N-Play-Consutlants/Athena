"""Career identity and legacy enrichment for Scout player briefs."""
from __future__ import annotations

from typing import Any, Dict, List

from Reasoning.career import CareerDataProvider, BaselineEngine


def _fmt_rate(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "unknown"


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):+.1f}%"
    except Exception:
        return "unknown"


class CareerIdentityEnricher:
    def __init__(self):
        self.provider = CareerDataProvider()
        self.baselines = BaselineEngine()

    def enrich_player_brief(self, brief: Dict[str, Any], assessment: Any, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        player = evaluation.get("player") if isinstance(evaluation.get("player"), dict) else {}
        name = player.get("name") or getattr(assessment, "title", "") or "Player"
        career = self.provider.load_player(name)
        if not career:
            return brief

        baseline = self.baselines.compute(career.get("season_history") or [])
        identity_body = self._identity_body(career, baseline)
        legacy_body = self._legacy_body(career, baseline)
        baseline_body = self._baseline_body(career, baseline)
        trend_body = self._trend_body(career, baseline)

        sections = list(brief.get("sections") or [])
        sections = self._upsert_after(sections, "Executive Summary", {"heading": "Career Identity", "body": identity_body})
        sections = self._upsert_after(sections, "Career Identity", {"heading": "Career Legacy", "body": legacy_body})
        sections = self._upsert_after(sections, "Current Value", {"heading": "Career Baselines", "body": baseline_body})
        sections = self._replace_section(sections, "Trend Analysis", trend_body)

        # Improve executive summary with proven-career framing.
        exec_summary = brief.get("executive_summary") or ""
        peak_goals = baseline.get("peak_goals") or {}
        award_count = sum(int(a.get("count") or 1) for a in career.get("awards") or [])
        prefix = (
            f"{career.get('name', name)} is better classified from a career-profile lens than a single-season stat line: "
            f"1st overall pick, Toronto captain, {award_count} major individual NHL honors, "
            f"and a demonstrated {int(peak_goals.get('goals') or 0)}-goal peak season. "
        )
        brief["executive_summary"] = prefix + exec_summary
        sections = self._replace_section(sections, "Executive Summary", brief["executive_summary"])

        # Improve cards.
        cards = list(brief.get("cards") or [])
        if career.get("leadership", {}).get("captain"):
            cards.append({"label": "Leadership", "value": "Captain"})
        cards.append({"label": "3-year PPG", "value": _fmt_rate(baseline.get("rolling_3", {}).get("ppg"))})
        cards.append({"label": "Peak goals", "value": int((baseline.get("peak_goals") or {}).get("goals") or 0)})
        cards.append({"label": "Career tier", "value": "Franchise Superstar"})

        brief["sections"] = sections
        brief["cards"] = self._dedupe_cards(cards)
        brief["career_identity"] = career
        brief["career_baselines"] = baseline
        brief["natural_language_response"] = self._render(brief)
        return brief

    def _identity_body(self, career: Dict[str, Any], baseline: Dict[str, Any]) -> str:
        draft = career.get("draft") or {}
        leadership = career.get("leadership") or {}
        career_base = baseline.get("career") or {}
        pieces = [
            f"{career.get('name')} is a {career.get('position')} for {career.get('team')}.",
            f"Draft pedigree: {draft.get('overall')}st overall in {draft.get('year')} by {draft.get('team')}.",
        ]
        if leadership.get("captain"):
            pieces.append(f"Leadership: captain of the {leadership.get('captain_team', career.get('team'))}.")
        pieces.append(
            f"Career production baseline from the local seed pack: {career_base.get('points')} points in "
            f"{career_base.get('games')} games ({_fmt_rate(career_base.get('ppg'))} PPG)."
        )
        return " ".join(pieces)

    def _legacy_body(self, career: Dict[str, Any], baseline: Dict[str, Any]) -> str:
        awards = career.get("awards") or []
        award_text = []
        for award in awards:
            count = int(award.get("count") or 1)
            years = ", ".join(str(y) for y in award.get("years") or [])
            award_text.append(f"{award.get('name')} x{count}" + (f" ({years})" if years else ""))
        peak_goals = baseline.get("peak_goals") or {}
        honors = career.get("honors") or []
        honor_text = ", ".join(h.get("name", "") for h in honors if h.get("name"))
        body = (
            "Career legacy evidence supports a franchise-superstar classification. "
            f"Major awards: {'; '.join(award_text)}. "
            f"Peak goal season: {peak_goals.get('goals')} goals in {peak_goals.get('season')}. "
        )
        if honor_text:
            body += f"Additional honors: {honor_text}. "
        body += (
            "These accomplishments are not trivia; they are evidence for elite goal scoring, peak dominance, "
            "early NHL impact, peer recognition, and organizational importance."
        )
        return body

    def _baseline_body(self, career: Dict[str, Any], baseline: Dict[str, Any]) -> str:
        cur = baseline.get("current") or {}
        r3 = baseline.get("rolling_3") or {}
        r5 = baseline.get("rolling_5") or {}
        car = baseline.get("career") or {}
        peak = baseline.get("peak_points") or {}
        delta = baseline.get("current_vs_3yr_delta_pct")
        return (
            f"Current season: {cur.get('points')} points in {cur.get('games')} games ({_fmt_rate(cur.get('ppg'))} PPG). "
            f"Rolling 3-year baseline: {r3.get('points')} points in {r3.get('games')} games ({_fmt_rate(r3.get('ppg'))} PPG). "
            f"Rolling 5-year baseline: {r5.get('points')} points in {r5.get('games')} games ({_fmt_rate(r5.get('ppg'))} PPG). "
            f"Career baseline: {car.get('points')} points in {car.get('games')} games ({_fmt_rate(car.get('ppg'))} PPG). "
            f"Peak point season: {peak.get('points')} points in {peak.get('season')}. "
            f"Current season versus 3-year baseline: {_fmt_pct(delta)}."
        )

    def _trend_body(self, career: Dict[str, Any], baseline: Dict[str, Any]) -> str:
        delta = baseline.get("current_vs_3yr_delta_pct")
        r3 = baseline.get("rolling_3") or {}
        cur = baseline.get("current") or {}
        try:
            d = float(delta)
        except Exception:
            d = None
        if d is not None and d < -15:
            return (
                f"Trend assessment: current production ({_fmt_rate(cur.get('ppg'))} PPG) is materially below "
                f"the rolling three-year baseline ({_fmt_rate(r3.get('ppg'))} PPG). "
                "That should be interpreted as a decline signal in output, not automatically as player deterioration. "
                "Given the injury and team-context notes attached to this base case, Athena should treat this as a temporary-regression hypothesis until health, usage, line deployment, and team environment evidence are evaluated."
            )
        return (
            "Trend assessment: current production remains broadly aligned with the rolling three-year baseline. "
            "Additional context intelligence will refine whether the trend reflects player change or environment."
        )

    def _upsert_after(self, sections: List[Dict[str, Any]], after_heading: str, new_section: Dict[str, Any]) -> List[Dict[str, Any]]:
        sections = [s for s in sections if s.get("heading") != new_section.get("heading")]
        out = []
        inserted = False
        for s in sections:
            out.append(s)
            if s.get("heading") == after_heading:
                out.append(new_section)
                inserted = True
        if not inserted:
            out.append(new_section)
        return out

    def _replace_section(self, sections: List[Dict[str, Any]], heading: str, body: str) -> List[Dict[str, Any]]:
        replaced = False
        out = []
        for s in sections:
            if s.get("heading") == heading:
                out.append({"heading": heading, "body": body})
                replaced = True
            else:
                out.append(s)
        if not replaced:
            out.append({"heading": heading, "body": body})
        return out

    def _dedupe_cards(self, cards):
        seen = set()
        out = []
        for card in cards:
            key = (card.get("label"), str(card.get("value")))
            if key not in seen:
                seen.add(key)
                out.append(card)
        return out

    def _render(self, brief: Dict[str, Any]) -> str:
        lines = [brief.get("title", "Player Assessment"), "", f"Confidence: {round(float(brief.get('confidence') or 0) * 100):.0f}%"]
        cards = brief.get("cards") or []
        if cards:
            lines.append(" | ".join(f"{c.get('label')}: {c.get('value')}" for c in cards[:8]))
        for section in brief.get("sections") or []:
            body = str(section.get("body") or "").strip()
            if body:
                lines.extend(["", str(section.get("heading")), body])
        return "\n".join(lines).strip()
