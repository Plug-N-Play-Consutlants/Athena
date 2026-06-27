"""Validate Scout public-hockey answer binding.

Sprint 4A.6 connects Scout public-sports questions to Athena's compact public
hockey knowledge retrieval layer. This validation intentionally checks behavior,
not styling.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION  # noqa: E402
from Scout.conversation.context import load_context  # noqa: E402
from Scout.conversation.router import route_question  # noqa: E402


class Report:
    def __init__(self) -> None:
        self.passed = []
        self.failed = []
        self.warnings = []

    def pass_(self, name: str, detail: str = "") -> None:
        self.passed.append((name, detail))

    def fail(self, name: str, detail: str = "") -> None:
        self.failed.append((name, detail))

    def warn(self, name: str, detail: str = "") -> None:
        self.warnings.append((name, detail))

    def emit(self) -> int:
        print("Scout Public Hockey Answer Binding Validation Report")
        print("====================================================")
        status = "PASS" if not self.failed else "FAIL"
        print(f"Overall status: {status}")
        print(f"Passed: {len(self.passed)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Failed: {len(self.failed)}")
        print()
        for name, detail in self.passed:
            print(f"[PASS] {name}: {detail}".rstrip())
        for name, detail in self.warnings:
            print(f"[WARN] {name}: {detail}".rstrip())
        for name, detail in self.failed:
            print(f"[FAIL] {name}: {detail}".rstrip())
        return 1 if self.failed else 0


def _assert(condition: bool, report: Report, name: str, detail: str = "") -> None:
    if condition:
        report.pass_(name, detail)
    else:
        report.fail(name, detail)


def main() -> int:
    report = Report()
    ctx = load_context()

    ltir = route_question("How does LTIR work?", ctx, mode="public")
    _assert(ltir.get("intent") == "public_hockey_knowledge", report, "public_mode_routes_to_knowledge", str(ltir.get("intent")))
    _assert(ltir.get("title") == "Public hockey knowledge", report, "public_answer_title", str(ltir.get("title")))
    _assert(float(ltir.get("confidence") or 0) >= 0.45, report, "public_answer_confidence", str(ltir.get("confidence")))
    _assert(len(ltir.get("observed_facts") or []) >= 1, report, "public_answer_evidence_visible", f"facts={len(ltir.get('observed_facts') or [])}")
    dev = ltir.get("developer") if isinstance(ltir.get("developer"), dict) else {}
    retrieval = dev.get("retrieval") if isinstance(dev.get("retrieval"), dict) else {}
    _assert(retrieval.get("status") == "available", report, "developer_retrieval_trace", str(retrieval.get("status")))
    evidence = dev.get("evidence_used") if isinstance(dev.get("evidence_used"), list) else []
    _assert(any("MOU" in " ".join(item.get("authority_refs", []) or []) or item.get("document_type") == "cba_mou" for item in evidence), report, "cba_mou_evidence_used", f"evidence={len(evidence)}")

    icing = route_question("What is icing?", ctx, mode="public")
    icing_dev = icing.get("developer") if isinstance(icing.get("developer"), dict) else {}
    icing_evidence = icing_dev.get("evidence_used") if isinstance(icing_dev.get("evidence_used"), list) else []
    _assert(any(item.get("document_type") == "official_rulebook" for item in icing_evidence), report, "rulebook_evidence_used", f"evidence={len(icing_evidence)}")

    unsupported = route_question("How does the Hiller hire affect the Leafs?", ctx, mode="public")
    _assert(unsupported.get("intent") in {"public_hockey_knowledge", "clarify_or_help", "event_intelligence_gap", "public_intelligence_gap"}, report, "unsupported_public_question_bounded", str(unsupported.get("title")))
    _assert("invent" in " ".join(unsupported.get("known_limitations") or []) or "invent" in str(unsupported.get("natural_language_response", "")) or "will not answer" in str(unsupported.get("natural_language_response", "")).lower(), report, "unsupported_question_does_not_invent", str(unsupported.get("natural_language_response", ""))[:120])

    overview = route_question("public sports overview", ctx, mode="public")
    _assert(overview.get("title") == "Public sports mode", report, "public_overview_still_available", str(overview.get("title")))
    _assert(ATHENA_VERSION.startswith("0.5.0-") and SCOUT_VERSION.startswith("v0.5.0-"), report, "version_metadata_available", f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
