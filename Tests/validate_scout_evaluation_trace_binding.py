"""
Validate Sprint 3E.4.2 — Scout Evaluation Trace Binding.

This validation focuses on the Scout -> Athena Evaluation Engine handoff. It
intentionally does not require Fantrax transaction authentication because market
and manager activity can be capability-limited while the trace binding still
works.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json  # noqa: E402
from Core.logger import log, log_header  # noqa: E402

REPORT_JSON = PROJECT_ROOT / "Reports" / "scout_evaluation_trace_binding_report.json"
REPORT_TXT = PROJECT_ROOT / "Reports" / "scout_evaluation_trace_binding_report.txt"

QUESTION_SET = [
    ("Analyze my league", "analyze_league"),
    ("Analyze my team", "analyze_team"),
    ("Tell me about Sidney Crosby", "player_profile"),
    ("Who are the most active managers?", "most_active_managers"),
    ("What's the trade market like?", "trade_market"),
]

REQUIRED_DEVELOPER_FIELDS = [
    "question",
    "context",
    "provider",
    "intent",
    "modules_executed",
    "evidence_used",
    "confidence",
    "evaluation",
    "natural_language_response",
]


def _check(name: str, status: str, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"name": name, "status": status, "message": message, "details": details or {}}


def _has_content(answer: Dict[str, Any]) -> bool:
    return bool(answer.get("engine_conclusion") or answer.get("natural_language_response"))


def _developer(answer: Dict[str, Any]) -> Dict[str, Any]:
    developer = answer.get("developer") if isinstance(answer, dict) else None
    return developer if isinstance(developer, dict) else {}


def validate() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    try:
        from Intelligence.evaluation_engine import EvaluationContext, classify_intent, evaluate, plan_evaluation  # noqa: PLC0415

        ctx = EvaluationContext(question="Analyze my league", provider="Fantrax")
        evaluation = evaluate("Analyze my league", ctx)
        checks.append(_check(
            "evaluation_engine_import",
            "pass" if evaluation.get("developer") else "fail",
            "Athena Evaluation Engine imports and returns a developer trace.",
            {"intent": evaluation.get("intent"), "developer_keys": sorted(list(_developer(evaluation).keys()))},
        ))
        checks.append(_check(
            "intent_classifier",
            "pass" if classify_intent("What's the trade market like?").get("intent") == "trade_market" else "fail",
            "Intent classifier recognizes the trade-market question.",
            {"classification": classify_intent("What's the trade market like?")},
        ))
        checks.append(_check(
            "evaluation_planner",
            "pass" if plan_evaluation("analyze_league").get("modules") else "fail",
            "Evaluation planner returns modules for supported intents.",
            {"plan": plan_evaluation("analyze_league")},
        ))
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("evaluation_engine_import", "fail", str(exc)))

    try:
        from Scout.conversation.context import load_context  # noqa: PLC0415
        from Scout.conversation.router import route_question  # noqa: PLC0415

        ctx = load_context()
        for question, expected_intent in QUESTION_SET:
            answer = route_question(question, ctx, mode="fantasy")
            developer = _developer(answer)
            missing = [field for field in REQUIRED_DEVELOPER_FIELDS if field not in developer]
            wrong_intent = answer.get("intent") != expected_intent
            status = "pass"
            problems = []
            if not _has_content(answer):
                status = "fail"
                problems.append("no natural-language/engine response")
            if missing:
                status = "fail"
                problems.append(f"missing developer fields: {missing}")
            if wrong_intent:
                status = "fail"
                problems.append(f"expected intent {expected_intent}, got {answer.get('intent')}")
            if not isinstance(developer.get("modules_executed"), list):
                status = "fail"
                problems.append("modules_executed is not a list")
            if not isinstance(developer.get("evidence_used"), list):
                status = "fail"
                problems.append("evidence_used is not a list")

            checks.append(_check(
                f"scout_trace:{question}",
                status,
                "; ".join(problems) if problems else f"Intent={answer.get('intent')}; full developer trace present.",
                {
                    "question": question,
                    "expected_intent": expected_intent,
                    "actual_intent": answer.get("intent"),
                    "confidence": answer.get("confidence"),
                    "developer_keys": sorted(list(developer.keys())),
                    "modules_executed": developer.get("modules_executed"),
                    "evidence_count": len(developer.get("evidence_used") or []),
                    "title": answer.get("title"),
                    "engine_conclusion": answer.get("engine_conclusion"),
                    "limitations": answer.get("known_limitations"),
                },
            ))

        public_answer = route_question("Analyze the NHL", ctx, mode="public")
        public_developer = _developer(public_answer)
        checks.append(_check(
            "scout_public_mode_trace",
            "pass" if public_answer.get("intent") == "public_sports_overview" and not [f for f in REQUIRED_DEVELOPER_FIELDS if f not in public_developer] else "fail",
            "Public mode returns a bounded public-sports trace without pretending rich NHL rule books exist.",
            {"intent": public_answer.get("intent"), "developer_keys": sorted(list(public_developer.keys()))},
        ))
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("scout_trace_path", "fail", str(exc)))

    passed = sum(1 for item in checks if item["status"] == "pass")
    warned = sum(1 for item in checks if item["status"] == "warn")
    failed = sum(1 for item in checks if item["status"] == "fail")
    report = {
        "report_name": "Scout Evaluation Trace Binding Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "fail" if failed else ("warn" if warned else "pass"),
        "summary": {"pass": passed, "warn": warned, "fail": failed},
        "interpretation": {
            "scope": "Scout -> Athena Evaluation Engine trace binding only",
            "transaction_auth": "not_required_for_this_validation",
        },
        "checks": checks,
        "blockers": [item for item in checks if item["status"] == "fail"],
        "warnings": [item for item in checks if item["status"] == "warn"],
    }
    return report


def write_report(report: Dict[str, Any]) -> None:
    write_json(REPORT_JSON, report)
    lines = [
        "Scout Evaluation Trace Binding Validation Report",
        "=" * 55,
        f"Overall status: {str(report.get('overall_status', 'unknown')).upper()}",
        f"Passed: {report.get('summary', {}).get('pass', 0)}",
        f"Warnings: {report.get('summary', {}).get('warn', 0)}",
        f"Failed: {report.get('summary', {}).get('fail', 0)}",
        "",
    ]
    for item in report.get("checks", []):
        lines.append(f"[{item['status'].upper()}] {item['name']}: {item['message']}")
    if report.get("blockers"):
        lines.extend(["", "Blocking issues:"])
        for item in report["blockers"]:
            lines.append(f"- {item['name']}: {item['message']}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    log_header("SCOUT EVALUATION TRACE BINDING VALIDATION")
    report = validate()
    write_report(report)
    for line in REPORT_TXT.read_text(encoding="utf-8").splitlines():
        log(line)
    log("")
    log(f"JSON report: {REPORT_JSON}")
    log(f"Text report: {REPORT_TXT}")


if __name__ == "__main__":
    main()
