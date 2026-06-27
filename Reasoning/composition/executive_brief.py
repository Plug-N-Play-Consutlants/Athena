"""Executive intelligence composition for Scout.

This layer does not invent facts. It converts existing Reasoning/Intelligence
outputs into a professional, deterministic briefing structure.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _num(value: Any, digits: int = 2) -> str:
    try:
        f = float(value)
        if f.is_integer():
            return str(int(f))
        return f"{f:.{digits}f}"
    except Exception:
        return _clean(value)


def _percent(value: Any) -> str:
    try:
        f = float(value)
        if f <= 1:
            f *= 100
        return f"{f:.0f}%"
    except Exception:
        return _clean(value)


class ExecutiveBriefComposer:
    """Build Scout-ready briefs from player assessments and evaluations."""

    def build_player_brief(
        self,
        assessment: Any,
        evaluation: Dict[str, Any] | None = None,
        question: str = "",
        mode: str = "fantasy",
    ) -> Dict[str, Any]:
        evaluation = evaluation or {}
        player = evaluation.get("player") if isinstance(evaluation.get("player"), dict) else {}
        profiles = evaluation.get("profiles") if isinstance(evaluation.get("profiles"), dict) else {}
        production = profiles.get("production") if isinstance(profiles.get("production"), dict) else {}
        fantasy = profiles.get("fantasy") if isinstance(profiles.get("fantasy"), dict) else {}
        contract = profiles.get("contract") if isinstance(profiles.get("contract"), dict) else {}
        trajectory = profiles.get("trajectory") if isinstance(profiles.get("trajectory"), dict) else {}

        name = _clean(player.get("name")) or _clean(getattr(assessment, "title", "")) or "Player"
        position = _clean(player.get("position"))
        team = _clean(player.get("nhl_team"))
        title_parts = [name]
        if position or team:
            title_parts.append(" / ".join(p for p in [position, team] if p))
        title = " — ".join(title_parts)

        confidence = float(getattr(assessment, "confidence", None) or evaluation.get("confidence") or 0.0)
        confidence = max(0.0, min(1.0, confidence))

        production_band = _clean(production.get("production_band")).replace("_", " ")
        ppg = production.get("points_per_game")
        points = production.get("points")
        goals = production.get("goals")
        assists = production.get("assists")
        games = production.get("games_played")
        percentile = production.get("production_percentile")
        trajectory_label = _clean(trajectory.get("classification")).replace("_", " ")

        mode_key = (mode or "").strip().lower()
        public_mode = mode_key == "public"

        role = _clean(getattr(assessment, "organizational_role", ""))
        if public_mode:
            role = role.replace("Fantasy", "").replace("  ", " ").strip()
        if not role:
            if production_band in {"elite", "top tier"}:
                role = "Core Asset" if public_mode else "Core Fantasy Asset"
            elif production_band == "above average":
                role = "High-Value Contributor"
            elif production_band:
                role = "Evaluated Player Asset"
            else:
                role = "Under Evaluation"

        production_sentence = ""
        if production.get("available"):
            production_sentence = (
                f"Current production evidence shows {int(points or 0)} points in {int(games or 0)} games"
                + (f" ({_num(ppg, 3)} points/game)" if ppg is not None else "")
                + "."
            )
            if goals is not None or assists is not None:
                production_sentence += f" Goal/assist split: {int(goals or 0)} goals and {int(assists or 0)} assists."
        else:
            production_sentence = "Current production evidence is limited in the available Athena outputs."

        current_value = (
            f"{name} currently profiles as {role.lower()}."
            + (f" Production band: {production_band}." if production_band else "")
            + (" " + production_sentence if production_sentence else "")
        )

        historical_context = _clean(getattr(assessment, "historical_context", "")) or _clean(getattr(assessment, "historical_value", ""))
        if not historical_context:
            if production_band in {"elite", "top tier"}:
                historical_context = (
                    "Available evidence supports an established high-end profile rather than a simple one-season lookup. "
                    "Athena should continue enriching this section with historical-season and comparable-player evidence as those feeds expand."
                )
            else:
                historical_context = (
                    "Historical context is not yet fully populated for this player in the current reasoning bundle."
                )

        trend_analysis = _clean(getattr(assessment, "trend_analysis", "")) or _clean(getattr(assessment, "trend_value", ""))
        if not trend_analysis:
            trend_analysis = (
                f"Trajectory classification: {trajectory_label}."
                if trajectory_label
                else "Trajectory evidence is currently bounded to normalized production and availability signals."
            )

        context_impact = _clean(getattr(assessment, "fantasy_impact", ""))
        if public_mode:
            context_impact = (
                context_impact
                .replace("fantasy roster context", "public context")
                .replace("Fantasy roster context", "Public context")
                .replace("Fantasy profile evidence", "Public profile evidence")
                .replace("fantasy profile evidence", "public profile evidence")
                .replace("Fantasy impact", "Context impact")
                .replace("fantasy impact", "context impact")
                .replace("fantasy", "public-context")
                .replace("Fantasy", "Public-context")
            )
        if not context_impact:
            if fantasy.get("available") and not public_mode:
                pieces = []
                if player.get("fantasy_team"):
                    pieces.append(f"currently associated with {player.get('fantasy_team')}")
                if fantasy.get("keeper_relevance") is not None:
                    pieces.append(f"keeper relevance: {fantasy.get('keeper_relevance')}")
                context_impact = "Fantasy profile evidence is available" + (": " + "; ".join(pieces) if pieces else ".")
            elif public_mode:
                context_impact = "Public context is based on identity, production, role, career, contract/control, and trajectory evidence currently available to Athena."
            else:
                context_impact = "Fantasy impact is limited by missing fantasy profile evidence."

        contract_context = _clean(getattr(assessment, "contract_context", ""))
        if not contract_context:
            if contract.get("available"):
                contract_context = (
                    f"Contract evidence: {contract.get('contract_band') or 'available'}, "
                    f"years remaining {contract.get('years_remaining', 'unknown')}."
                )
            else:
                contract_context = "Contract evidence is unavailable or not normalized for this player."

        organizational_importance = _clean(getattr(assessment, "organizational_importance", ""))
        if not organizational_importance:
            if team and production_band in {"elite", "top tier"}:
                organizational_importance = (
                    f"For {team}, this profile represents a high-leverage roster asset because strong production at {position or 'the player position'} "
                    "is difficult to replace through ordinary market activity."
                )
            elif team:
                organizational_importance = (
                    f"For {team}, the current evidence supports an evaluated roster role, but deeper organizational context is still needed."
                )
            else:
                organizational_importance = "Organizational importance is limited by missing team context."

        risks = list(getattr(assessment, "risks", []) or [])
        limitations = list(getattr(assessment, "limitations", []) or evaluation.get("limitations") or [])
        risk_items = risks + [x for x in limitations if x not in risks]
        risk_assessment = _clean(getattr(assessment, "risk_assessment", ""))
        if not risk_assessment:
            if risk_items:
                risk_assessment = "Primary limitations: " + " ".join(str(x) for x in risk_items[:2])
            else:
                risk_assessment = "No major risk factor is isolated by the current evidence bundle, but the assessment remains bounded to available Athena outputs."

        future_outlook = _clean(getattr(assessment, "future_outlook", ""))
        if not future_outlook:
            if trajectory_label:
                future_outlook = (
                    f"Future outlook is currently anchored to trajectory classification '{trajectory_label}'. "
                    "Dedicated projection curves will improve this section in a later sprint."
                )
            else:
                future_outlook = "Future outlook requires richer projection and age-curve evidence."

        evidence_counts = self._evidence_counts(evaluation, assessment)
        supporting_evidence = list(getattr(assessment, "supporting_evidence", []) or [])
        if not supporting_evidence:
            supporting_evidence = self._supporting_evidence(evaluation, evidence_counts)

        executive_summary = _clean(getattr(assessment, "executive_summary", ""))
        if public_mode:
            executive_summary = (
                executive_summary
                .replace("fantasy roster context", "public context")
                .replace("Fantasy roster context", "Public context")
                .replace("fantasy context", "public context")
                .replace("Fantasy context", "Public context")
                .replace("Core Fantasy Asset", "Core Asset")
                .replace("core fantasy asset", "core asset")
            )
        if not executive_summary:
            strongest_context = "public context" if public_mode else "fantasy context"
            executive_summary = (
                f"{name} is assessed as {role}. "
                f"The strongest current signals are production profile, {strongest_context}, contract status, and trajectory evidence where available. "
                f"Confidence is {_percent(confidence)} because Athena is combining player intelligence outputs rather than relying on a single stat line."
            )

        sections = [
            {"heading": "Executive Summary", "body": executive_summary},
            {"heading": "Current Value", "body": current_value},
            {"heading": "Historical Context", "body": historical_context},
            {"heading": "Trend Analysis", "body": trend_analysis},
            {"heading": "Organizational Importance", "body": organizational_importance},
            {"heading": "Context Impact" if public_mode else "Fantasy Impact", "body": context_impact},
            {"heading": "Contract Context", "body": contract_context},
            {"heading": "Risk Assessment", "body": risk_assessment},
            {"heading": "Future Outlook", "body": future_outlook},
            {"heading": "Supporting Evidence", "body": "; ".join(supporting_evidence[:8]) if supporting_evidence else "No supporting evidence list was provided."},
        ]

        cards = [
            {"label": "Role", "value": role},
            {"label": "Confidence", "value": _percent(confidence)},
        ]
        if production_band:
            cards.append({"label": "Production Band", "value": production_band})
        if ppg is not None:
            cards.append({"label": "PPG", "value": _num(ppg, 3)})
        if contract.get("available"):
            cards.append({"label": "Contract", "value": contract.get("years_remaining", "unknown")})

        if public_mode:
            cards = [
                {**c, "value": str(c.get("value", "")).replace("Core Fantasy Asset", "Core Asset").replace("Fantasy", "").strip()}
                for c in cards
            ]

        natural = self.render_text(title, sections, confidence, cards)

        return {
            "title": title,
            "executive_summary": executive_summary,
            "sections": sections,
            "cards": cards,
            "natural_language_response": natural,
            "confidence": confidence,
            "evidence_counts": evidence_counts,
            "supporting_evidence": supporting_evidence,
            "rule_citations": list(getattr(assessment, "rule_citations", []) or []),
        }

    def render_text(self, title: str, sections: List[Dict[str, Any]], confidence: float, cards: List[Dict[str, Any]]) -> str:
        # Scout already renders the title as the answer heading. The brief body
        # starts with confidence to avoid duplicate title/title-body rendering.
        lines = [f"Confidence: {_percent(confidence)}"]
        if cards:
            card_text = " | ".join(f"{c.get('label')}: {c.get('value')}" for c in cards[:5])
            lines.append(card_text)
        for section in sections:
            body = _clean(section.get("body"))
            if body:
                lines.extend(["", f"{section.get('heading')}", body])
        return "\n".join(lines).strip()

    def _evidence_counts(self, evaluation: Dict[str, Any], assessment: Any) -> Dict[str, int]:
        existing = getattr(assessment, "evidence_counts", None)
        if isinstance(existing, dict) and existing:
            return dict(existing)

        profiles = evaluation.get("profiles") if isinstance(evaluation.get("profiles"), dict) else {}
        counts = {}
        for key, value in profiles.items():
            if isinstance(value, dict) and value.get("available"):
                counts[key] = 1
        if evaluation.get("observed_facts"):
            counts["observed_facts"] = len(evaluation.get("observed_facts") or [])
        if evaluation.get("limitations"):
            counts["limitations"] = len(evaluation.get("limitations") or [])
        return counts

    def _supporting_evidence(self, evaluation: Dict[str, Any], counts: Dict[str, int]) -> List[str]:
        evidence = []
        labels = {
            "identity": "Identity evidence",
            "production": "Production evidence",
            "fantasy": "Context profile evidence",
            "contract": "Contract evidence",
            "availability": "Availability evidence",
            "trajectory": "Trajectory evidence",
            "observed_facts": "Observed fact statements",
            "limitations": "Known limitation statements",
        }
        for key, count in counts.items():
            evidence.append(f"{labels.get(key, key)} ({count})")
        return evidence
