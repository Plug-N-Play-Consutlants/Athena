"""Validate Scout rule-citation cards and rule drill-down endpoint payloads."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Scout.conversation.context import load_context  # noqa: E402
from Scout.conversation.router import route_question  # noqa: E402
from Knowledge.Sources.rule_citations import lookup_rule_citation  # noqa: E402


class Report:
    def __init__(self) -> None:
        self.passed = []
        self.failed = []

    def pass_(self, name: str, detail: str = "") -> None:
        self.passed.append((name, detail))

    def fail(self, name: str, detail: str = "") -> None:
        self.failed.append((name, detail))

    def emit(self) -> int:
        print("Rule Citation Cards Validation Report")
        print("=====================================")
        print(f"Overall status: {'PASS' if not self.failed else 'FAIL'}")
        print(f"Passed: {len(self.passed)}")
        print(f"Failed: {len(self.failed)}")
        print("")
        for name, detail in self.passed:
            print(f"[PASS] {name}: {detail}".rstrip())
        for name, detail in self.failed:
            print(f"[FAIL] {name}: {detail}".rstrip())
        return 1 if self.failed else 0


def check(condition: bool, report: Report, name: str, detail: str = "") -> None:
    report.pass_(name, detail) if condition else report.fail(name, detail)


def main() -> int:
    report = Report()
    ctx = load_context()

    answer = route_question("How does LTIR work?", ctx, mode="public")
    citations = answer.get("rule_citations") if isinstance(answer.get("rule_citations"), list) else []
    check(len(citations) >= 1, report, "scout_answer_includes_rule_citations", f"citations={len(citations)}")
    first = citations[0] if citations else {}
    check(str(first.get("id", "")).startswith("rule:"), report, "citation_has_stable_id", str(first.get("id")))
    check(bool(first.get("view_url")), report, "citation_has_view_url", str(first.get("view_url")))
    check(bool(first.get("authority_refs")), report, "citation_has_authority_refs", "; ".join(first.get("authority_refs", []) or []))

    if first:
        drill = lookup_rule_citation(first.get("source_id", ""), first.get("topic_key", ""), ROOT)
        check(drill.get("status") == "available", report, "drilldown_lookup_available", str(drill.get("status")))
        check(drill.get("citation", {}).get("id") == first.get("id"), report, "drilldown_matches_card", str(drill.get("citation", {}).get("id")))
        check(bool(drill.get("limitations")), report, "drilldown_is_bounded", str(drill.get("limitations", [])[:1]))

    unsupported = route_question("What did the mascot eat for breakfast?", ctx, mode="public")
    unsupported_citations = unsupported.get("rule_citations") if isinstance(unsupported.get("rule_citations"), list) else []
    check(len(unsupported_citations) == 0, report, "unsupported_question_has_no_false_citations", f"citations={len(unsupported_citations)}")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
