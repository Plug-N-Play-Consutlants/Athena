"""Shared evidence-coverage and editorial significance contract.

A dossier describes what was observed and what remains unverified; it does
not invent missing evidence or turn a candidate relationship into a fact.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable


def build_dossier(*, subject: str, requirements: Iterable[str], evidence: Dict[str, Any],
                  findings: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
    requirements = list(dict.fromkeys(str(x) for x in requirements if str(x).strip()))
    coverage = {name: ("available" if evidence.get(name) not in (None, [], {}) else "missing")
                for name in requirements}
    selected = []
    for finding in findings:
        if not isinstance(finding, dict) or not finding.get("summary"):
            continue
        selected.append({"summary": str(finding["summary"]),
                         "evidence": list(finding.get("evidence") or []),
                         "significance": finding.get("significance", "unassessed"),
                         "uncertainty": list(finding.get("uncertainty") or []),
                         "source_id": finding.get("source_id")})
    return {"subject": subject, "coverage": coverage, "findings": selected,
            "missing": [k for k, v in coverage.items() if v == "missing"],
            "complete": all(v == "available" for v in coverage.values()),
            "contract_version": 1}
