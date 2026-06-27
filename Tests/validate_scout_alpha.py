"""Validate Scout Alpha deterministic router without requiring Streamlit."""

from pathlib import Path
import sys
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Core.logger import log_header, log
from Core.project_paths import REPORTS_DIR
from Scout.conversation.context import load_context
from Scout.conversation.router import route_question, analyze_league

REPORT_JSON = REPORTS_DIR / "scout_alpha_validation_report.json"
REPORT_TXT = REPORTS_DIR / "scout_alpha_validation_report.txt"


def check(name, ok, message, details=None):
    return {"name": name, "status": "pass" if ok else "fail", "message": message, "details": details or {}}


def main():
    log_header("SCOUT ALPHA VALIDATION")
    ctx = load_context()
    checks = []

    checks.append(check("context_load", bool(ctx.files_loaded), "Scout context loaded.", {"files_loaded": ctx.files_loaded}))

    questions = [
        "Who are the most active managers?",
        "Show the league market.",
        "Show expiring contracts.",
        "Compare Alien Agenda to league average.",
        "What are the known limitations?",
        "Analyze my league.",
    ]

    for question in questions:
        answer = route_question(question, ctx)
        ok = bool(answer.get("engine_conclusion")) and bool(answer.get("intent"))
        checks.append(check(f"question:{question}", ok, answer.get("title", "No title"), {"intent": answer.get("intent")}))

    analyze = analyze_league(ctx)
    checks.append(check("analyze_league", bool(analyze.get("observed_facts")), "Analyze League response generated.", {"cards": analyze.get("cards", [])}))

    passed = sum(1 for item in checks if item["status"] == "pass")
    failed = sum(1 for item in checks if item["status"] == "fail")
    report = {
        "report_name": "Scout Alpha Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }
    write_json(REPORT_JSON, report)

    lines = [
        "Scout Alpha Validation Report",
        "=" * 40,
        f"Overall status: {report['overall_status'].upper()}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        "",
    ]
    for item in checks:
        lines.append(f"[{item['status'].upper()}] {item['name']}: {item['message']}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")
    for line in lines:
        log(line)
    log("")
    log(f"JSON report: {REPORT_JSON}")
    log(f"Text report: {REPORT_TXT}")


if __name__ == "__main__":
    main()
