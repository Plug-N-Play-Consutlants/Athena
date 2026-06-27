"""
Doctor for Epic 4E.2 Player Reasoning.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("Epic 4E.2 Player Reasoning Doctor")
    print("=================================")

    checks = []

    def check(label, condition, detail=""):
        status = "PASS" if condition else "FAIL"
        checks.append(condition)
        print(f"[{status}] {label}" + (f": {detail}" if detail else ""))

    check("Reasoning package", (PROJECT_ROOT / "Reasoning").exists())
    check("Player intelligence output", (PROJECT_ROOT / "Output" / "player_master.json").exists())
    check("Player production output", (PROJECT_ROOT / "Output" / "player_production.json").exists())
    check("Player contract output", (PROJECT_ROOT / "Output" / "player_contracts.json").exists())

    try:
        from Reasoning.reasoning_engine import ReasoningEngine
        assessment = ReasoningEngine().reason_about_player("Analyze Auston Matthews")
        check("ReasoningEngine player assessment", bool(getattr(assessment, "summary", "")), getattr(assessment, "summary", "")[:120])
        check("Assessment confidence", getattr(assessment, "confidence", 0) > 0, str(getattr(assessment, "confidence", None)))
        check("Assessment evidence", bool(getattr(assessment, "evidence_used", [])), ", ".join(getattr(assessment, "evidence_used", [])))
    except Exception as ex:
        check("ReasoningEngine player assessment", False, str(ex))

    try:
        from Scout.conversation.router import route_question
        answer = route_question("Analyze Auston Matthews")
        check("Scout route", bool(answer.get("natural_language_response")), answer.get("intent", "unknown"))
    except Exception as ex:
        check("Scout route", False, str(ex))

    print()
    if all(checks):
        print("STATUS: PASS")
    else:
        print("STATUS: FAIL")
        raise RuntimeError("One or more doctor checks failed.")


if __name__ == "__main__":
    main()
