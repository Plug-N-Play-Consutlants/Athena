"""
Player evidence interpreter.

Converts heterogeneous evidence objects/dicts into canonical finding dicts.
"""
from __future__ import annotations

from typing import Any, Dict, List


class PlayerEvidenceInterpreter:
    def interpret(self, evidence: Any) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for item in evidence or []:
            if isinstance(item, dict):
                source_type = item.get("source_type") or item.get("type") or item.get("source") or "general"
                statement = item.get("summary") or item.get("statement") or item.get("label") or str(item)
                confidence = item.get("confidence", 0.5)
                category = item.get("category") or source_type
                metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            else:
                source_type = getattr(item, "source_type", getattr(item, "type", "general"))
                statement = getattr(item, "summary", getattr(item, "statement", str(item)))
                confidence = getattr(item, "confidence", 0.5)
                category = getattr(item, "category", source_type)
                metadata = getattr(item, "metadata", {}) or {}

            try:
                confidence = float(confidence)
            except Exception:
                confidence = 0.5

            findings.append({
                "type": str(source_type),
                "category": str(category),
                "statement": str(statement),
                "confidence": max(0.0, min(confidence, 1.0)),
                "metadata": metadata,
            })
        return findings
