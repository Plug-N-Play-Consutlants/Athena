"""
Build structured player assessment sections from findings.
"""
from __future__ import annotations

from typing import Dict, List, Any


class PlayerContextBuilder:
    def build(self, findings: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        ctx = {
            "identity": [],
            "production": [],
            "historical": [],
            "temporal": [],
            "trend": [],
            "contract": [],
            "fantasy": [],
            "organizational": [],
            "rules": [],
            "risks": [],
            "limitations": [],
            "explainability": [],
        }
        for f in findings:
            t = (f.get("type") or "").lower()
            c = (f.get("category") or "").lower()
            statement = str(f.get("statement") or "").strip()
            if not statement:
                continue

            if "limitation" in t or "limitation" in c:
                ctx["limitations"].append(statement)
            elif "identity" in t or "identity" in c:
                ctx["identity"].append(statement)
            elif "production" in t or "current" in c or "production" in c:
                ctx["production"].append(statement)
            elif "histor" in t or "histor" in c:
                ctx["historical"].append(statement)
            elif "tempor" in t or "tempor" in c:
                ctx["temporal"].append(statement)
            elif "trajectory" in t or "trend" in c:
                ctx["trend"].append(statement)
            elif "contract" in t or "contract" in c:
                ctx["contract"].append(statement)
            elif "fantasy" in t or "fantasy" in c:
                ctx["fantasy"].append(statement)
            elif "organiz" in c:
                ctx["organizational"].append(statement)
            elif "rule" in t or "rule" in c:
                ctx["rules"].append(statement)
            elif "risk" in c:
                ctx["risks"].append(statement)
            else:
                ctx["explainability"].append(statement)
        return ctx
