"""
Deterministic player narrative builder.

This is intentionally not an LLM. It turns structured assessment fields into a
stable Scout briefing.
"""
from __future__ import annotations


class PlayerNarrativeBuilder:
    def build(self, profile, assessment) -> str:
        name = getattr(profile, "name", "This player")
        position = getattr(profile, "position", None)
        team = getattr(profile, "team", None)

        identity = name
        if position or team:
            identity += " (" + ", ".join([part for part in [position, team] if part]) + ")"

        lines = [
            f"{identity} is assessed as {assessment.organizational_role or 'an asset under evaluation'} based on Athena's current evidence graph and player intelligence outputs."
        ]

        if assessment.executive_summary:
            lines.append(assessment.executive_summary)

        if assessment.historical_value:
            lines.append("Historical/context signal: " + assessment.historical_value)

        if assessment.trend_value:
            lines.append("Current trend signal: " + assessment.trend_value)

        if assessment.contract_value:
            lines.append("Contract/control signal: " + assessment.contract_value)

        if assessment.fantasy_value:
            lines.append("Fantasy/organizational signal: " + assessment.fantasy_value)

        if assessment.value_drivers:
            lines.append("Primary value drivers: " + "; ".join(assessment.value_drivers[:4]) + ".")

        if assessment.risks:
            lines.append("Main risks or caveats: " + "; ".join(assessment.risks[:3]) + ".")

        lines.append(f"Assessment confidence: {assessment.confidence:.2f}.")
        return " ".join(line for line in lines if line)
