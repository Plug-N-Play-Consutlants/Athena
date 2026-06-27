"""Validate Epic 5A response-composition visibility contract.

Acceptance issue: Scout was rendering Athena diagnostics as the public answer.
This validator proves that public prose and diagnostic evidence are separated,
and that the browser renderer only emits diagnostics when Developer Mode is on.
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ATHENA_BUILD  # noqa: E402
from Scout.conversation.composition import compose_answer_payload, public_debug_summary  # noqa: E402
from Scout.conversation.responses import response  # noqa: E402
from Tests.version_compat import is_recognized_athena_version, is_recognized_build, is_recognized_scout_version  # noqa: E402


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []

    def check(self, condition: bool, name: str, detail: str = "") -> None:
        if condition:
            self.passed += 1
            self.lines.append(f"[PASS] {name}: {detail}".rstrip())
        else:
            self.failed += 1
            self.lines.append(f"[FAIL] {name}: {detail}".rstrip())

    def emit(self) -> int:
        print("Response Composition Visibility Validation Report")
        print("=================================================")
        print(f"Overall status: {'PASS' if self.failed == 0 else 'FAIL'}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print()
        for line in self.lines:
            print(line)
        return 0 if self.failed == 0 else 1


def main() -> int:
    report = Report()

    report.check(is_recognized_athena_version(ATHENA_VERSION), "athena_version", ATHENA_VERSION)
    report.check(is_recognized_scout_version(SCOUT_VERSION, ATHENA_VERSION), "scout_version", SCOUT_VERSION)
    report.check(is_recognized_build(ATHENA_BUILD, ATHENA_VERSION), "athena_build", ATHENA_BUILD)

    answer = response(
        intent="acceptance_probe",
        title="Alex Ovechkin — L / WSH",
        engine_conclusion="Athena internal reasoning conclusion that should not be the default public body.",
        observed_facts=["Identity evidence available: 1.", "Production evidence available: 1."],
        known_limitations=["Player Intelligence limitation should be diagnostic."],
        developer={"modules_executed": ["Player Intelligence"]},
        confidence=0.89,
    )
    answer["natural_language_response"] = "Alex Ovechkin's legacy is defined by unprecedented goal scoring, durability, and a generation-long identity as Washington's franchise player."
    composed = compose_answer_payload(answer)

    report.check("Alex Ovechkin" in composed.get("public_comment", "") and "internal reasoning" not in composed.get("public_comment", ""), "public_comment_uses_public_text", str(composed.get("public_comment"))[:120])
    diagnostics = composed.get("diagnostics") if isinstance(composed.get("diagnostics"), dict) else {}
    report.check("internal reasoning" in str(diagnostics.get("engine_conclusion", "")), "engine_conclusion_preserved_as_diagnostic")
    report.check(len(diagnostics.get("observed_facts") or []) == 2, "observed_facts_preserved_as_diagnostic")
    report.check("Player Intelligence" in str(diagnostics.get("known_limitations", [])), "limitations_preserved_as_diagnostic")

    summary = public_debug_summary(composed)
    report.check("Public response" not in summary.get("public_comment", ""), "summary_public_comment_clean")
    report.check("engine_conclusion" in (summary.get("diagnostics") or {}), "summary_keeps_diagnostics_nested")

    app_text = (PROJECT_ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    report.check("developerActive" in app_text and "if (developerActive)" in app_text, "renderer_has_developer_visibility_gate")
    report.check("const publicText = String(answer.public_comment || '').trim();" in app_text, "renderer_public_comment_first")
    report.check("let diagnosticBlock = ''" in app_text and "Observed Facts" in app_text, "renderer_hides_facts_without_developer_mode")
    report.check("if (developerActive)" in app_text and "Engine Conclusion" in app_text, "renderer_hides_engine_conclusion_without_developer_mode")
    report.check("if (developerActive)" in app_text and "rawPayload" in app_text, "renderer_hides_raw_reasoning_without_developer_mode")

    debug_text = (PROJECT_ROOT / "Athena" / "debug_export.py").read_text(encoding="utf-8")
    report.check("Public response:" in debug_text and "Diagnostics:" in debug_text, "debug_export_separates_public_and_diagnostics")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
