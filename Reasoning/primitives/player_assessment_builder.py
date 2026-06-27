"""
Build PlayerAssessment from canonical findings.
"""
from __future__ import annotations

from typing import Any, Dict, List

from Reasoning.models.player_assessment import PlayerAssessment
from Reasoning.primitives.player_narrative_builder import PlayerNarrativeBuilder
from Reasoning.primitives.player_context_builder import PlayerContextBuilder


class PlayerAssessmentBuilder:
    def __init__(self):
        self.narrative = PlayerNarrativeBuilder()
        self.context = PlayerContextBuilder()

    def _average_confidence(self, findings: List[Dict[str, Any]]) -> float:
        vals = []
        for f in findings:
            try:
                vals.append(float(f.get("confidence", 0.5)))
            except Exception:
                pass
        if not vals:
            return 0.5
        return round(sum(vals) / len(vals), 3)

    def _role(self, findings: List[Dict[str, Any]], confidence: float) -> str:
        text = " ".join(str(f.get("statement", "")).lower() for f in findings)
        if "franchise" in text or "cornerstone" in text:
            return "Franchise/Core Asset"
        if "rostered by" in text and ("contract" in text or "scarcity" in text):
            return "Core Fantasy Asset"
        if confidence >= 0.82:
            return "Core Asset"
        if confidence >= 0.65:
            return "Useful Asset"
        return "Under Evaluation"

    def build(self, profile: Any, findings: List[Dict[str, Any]]) -> PlayerAssessment:
        pa = PlayerAssessment()
        pa.findings = findings
        pa.confidence = self._average_confidence(findings)
        pa.organizational_role = self._role(findings, pa.confidence)

        contexts = self.context.build(findings)

        production = contexts["production"]
        contract = contexts["contract"]
        fantasy = contexts["fantasy"] + contexts["organizational"]
        trend = contexts["trend"] + contexts["temporal"]
        historical = contexts["historical"]

        pa.historical_value = historical[0] if historical else (
            "Athena has limited career-depth historical evidence in the current local outputs; assessment therefore emphasizes current production, value model, contract, scarcity, and available temporal snapshots."
        )
        pa.trend_value = trend[0] if trend else (production[0] if production else "")
        pa.contract_value = contract[0] if contract else ""
        pa.fantasy_value = fantasy[0] if fantasy else ""

        pa.strengths = []
        for bucket in (production, contract, fantasy, trend):
            for item in bucket:
                if item not in pa.strengths:
                    pa.strengths.append(item)

        pa.risks = list(dict.fromkeys(contexts["risks"] + contexts["limitations"]))
        pa.limitations = list(dict.fromkeys(contexts["limitations"]))

        pa.opportunities = [
            "Add multi-season public production, deployment, injury, line, and power-play evidence to improve player trajectory quality.",
            "Connect deeper rule evidence where contract or CBA claims require explicit source citations.",
        ]

        pa.value_drivers = []
        for label, bucket in [
            ("Production", production),
            ("Contract/control", contract),
            ("Fantasy context", fantasy),
            ("Trend", trend),
        ]:
            if bucket:
                pa.value_drivers.append(f"{label}: {bucket[0]}")

        pa.evidence_used = list(dict.fromkeys([
            str(f.get("type") or f.get("category") or "unknown") for f in findings
        ]))

        pa.cards = []
        for f in findings:
            meta = f.get("metadata") if isinstance(f.get("metadata"), dict) else {}
            if f.get("category") == "current_value" and meta:
                for label, key in [
                    ("Points", "points"),
                    ("Goals", "goals"),
                    ("Assists", "assists"),
                    ("PPG", "points_per_game"),
                    ("Band", "production_band"),
                ]:
                    if meta.get(key) is not None:
                        pa.cards.append({"label": label, "value": meta.get(key)})
            if f.get("category") == "contract_value" and meta:
                if meta.get("years_remaining") is not None:
                    pa.cards.append({"label": "Contract years", "value": meta.get("years_remaining")})
                if meta.get("contract_band"):
                    pa.cards.append({"label": "Contract band", "value": meta.get("contract_band")})

        name = getattr(profile, "name", "Player")
        pa.executive_summary = (
            f"{name} is no longer assessed as a one-season stat line. Athena is combining identity, production, "
            f"contract/control, fantasy roster context, and trajectory evidence into a single asset assessment. "
            f"The current local evidence supports a {pa.organizational_role.lower()} classification, while also noting where "
            f"multi-season and deployment evidence remains incomplete."
        )
        pa.summary = self.narrative.build(profile, pa)
        return pa
