"""Validate Studio aggregate validation reporting for 0.5.1.x compatibility."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"


def check(condition: bool, message: str, passed: list[str], failed: list[str]) -> None:
    if condition:
        passed.append(message)
        print(f"[PASS] {message}")
    else:
        failed.append(message)
        print(f"[FAIL] {message}")


def main() -> int:
    print("Validation Aggregator Hotfix Validation")
    print("=" * 64)
    passed: list[str] = []
    failed: list[str] = []

    text = STUDIO.read_text(encoding="utf-8")
    version = VERSION.read_text(encoding="utf-8")

    check(('ATHENA_VERSION = "0.5.1.' in version or 'ATHENA_VERSION = "0.5.2.' in version), "version is Epic 5 numeric release", passed, failed)
    check('VERSION_SCHEMA = "major.epic.sprint.patch.hotfix"' in version, "release uses locked version schema", passed, failed)
    check('RELEASE_HOTFIX = "' in version, "hotfix component present", passed, failed)
    check('results: list[tuple[str, str, int | None]]' in text, "sequence runner stores per-child results", passed, failed)
    check('failed_names = [name for name, status, _ in results if status == "FAIL"]' in text, "sequence runner reports failed child names", passed, failed)
    check('passed={passed}; skipped={skipped}; failures={failures}; failed=' in text, "history details include aggregate breakdown", passed, failed)
    check('=== {label} Summary ===' in text, "aggregate summary section is rendered", passed, failed)
    check('Validate Aggregator' in text, "Validate Everything includes aggregator validator", passed, failed)
    check('Doctor Aggregator' in text, "Doctor Everything includes aggregator doctor", passed, failed)

    print("\nSummary")
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("\nOverall status: FAIL")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
