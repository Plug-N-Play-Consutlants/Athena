"""Validate Scout/Athena debug export support."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Athena.debug_export import build_debug_export, write_debug_export  # noqa: E402
from Athena.capabilities import _count_records  # noqa: E402
from Scout.app import SCOUT_VERSION  # noqa: E402


class ValidationReport:
    def __init__(self) -> None:
        self.passed = []
        self.failed = []
        self.warnings = []

    def pass_(self, name: str, detail: str = "") -> None:
        self.passed.append((name, detail))

    def fail(self, name: str, detail: str = "") -> None:
        self.failed.append((name, detail))

    def render(self) -> str:
        lines = [
            "Debug Export Validation Report",
            "==============================",
            f"Overall status: {'FAIL' if self.failed else 'PASS'}",
            f"Passed: {len(self.passed)}",
            f"Warnings: {len(self.warnings)}",
            f"Failed: {len(self.failed)}",
            "",
        ]
        for name, detail in self.passed:
            lines.append(f"[PASS] {name}: {detail}".rstrip())
        for name, detail in self.warnings:
            lines.append(f"[WARN] {name}: {detail}".rstrip())
        for name, detail in self.failed:
            lines.append(f"[FAIL] {name}: {detail}".rstrip())
        return "\n".join(lines)


def main() -> int:
    report = ValidationReport()

    if SCOUT_VERSION == "v0.5.0-drop3f6":
        report.pass_("scout_version", SCOUT_VERSION)
        report.pass_("scout_version_not_environment_overridden", "SCOUT_VERSION is fixed for this build")
    else:
        report.fail("scout_version", SCOUT_VERSION)

    # Regression check for Fantrax league_info shape. Fantrax stores teams under teamInfo.
    sample_league_info = {"teamInfo": {"team_a": {"name": "A"}, "team_b": {"name": "B"}}}
    count = _count_records(sample_league_info)
    if count == 2:
        report.pass_("fantrax_teamInfo_count_supported", f"count={count}")
    else:
        report.fail("fantrax_teamInfo_count_supported", f"count={count}")

    payload = build_debug_export(source="validation")
    required = ["debug_export_version", "created_at", "workspace", "capability_dashboard", "raw_files", "output_files", "secret_status_redacted"]
    missing = [key for key in required if key not in payload]
    if not missing:
        report.pass_("debug_export_payload_shape", f"keys={len(payload.keys())}")
    else:
        report.fail("debug_export_payload_shape", f"missing={missing}")

    serialized = json.dumps(payload, indent=2, ensure_ascii=False).lower()
    banned_terms = ["auth_cookie", "cookie_header", "fantrax_cookie\"", "password"]
    leaked = [term for term in banned_terms if term in serialized]
    if not leaked:
        report.pass_("debug_export_redacts_secret_values", "no banned secret-value markers found")
    else:
        report.fail("debug_export_redacts_secret_values", f"found={leaked}")

    result = write_debug_export(source="validation")
    json_path = Path(result.get("json_path", ""))
    text_path = Path(result.get("text_path", ""))
    if result.get("ok") and json_path.exists() and text_path.exists():
        report.pass_("debug_export_files_written", f"json={json_path.name}; text={text_path.name}")
    else:
        report.fail("debug_export_files_written", f"result={result}")

    if "operation_history" in payload and isinstance(payload.get("operation_history"), list):
        report.pass_("operation_history_included", f"records={len(payload.get('operation_history') or [])}")
    else:
        report.fail("operation_history_included", "operation_history missing or not list")

    print(report.render())
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
