"""Doctor for Studio aggregate validation reporting."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VALIDATOR = ROOT / "Tests" / "validate_validation_aggregator_hotfix.py"
VERSION = ROOT / "Core" / "version.py"


def emit(status: str, message: str) -> None:
    print(f"[{status}] {message}")


def main() -> int:
    print("Validation Aggregator Doctor")
    print("=" * 64)
    failures = 0

    for path, label in [(STUDIO, "Studio tool"), (VALIDATOR, "aggregator validator"), (VERSION, "version metadata")]:
        if path.exists():
            emit("PASS", f"{label} exists: {path.relative_to(ROOT)}")
        else:
            emit("FAIL", f"{label} missing: {path.relative_to(ROOT)}")
            failures += 1

    if STUDIO.exists():
        text = STUDIO.read_text(encoding="utf-8")
        checks = [
            ('=== {label} Summary ===', "aggregate summary output"),
            ('failed_names = [name for name, status, _ in results if status == "FAIL"]', "failed child-name capture"),
            ('passed={passed}; skipped={skipped}; failures={failures}; failed=', "history detail breakdown"),
            ('Validate Aggregator', "Validate Everything aggregator inclusion"),
            ('Doctor Aggregator', "Doctor Everything aggregator inclusion"),
        ]
        for needle, label in checks:
            if needle in text:
                emit("PASS", label)
            else:
                emit("FAIL", label)
                failures += 1

    if VERSION.exists():
        vtext = VERSION.read_text(encoding="utf-8")
        if 'ATHENA_VERSION = "0.5.1.' in vtext or 'ATHENA_VERSION = "0.5.2.' in vtext:
            emit("PASS", "version is Epic 5 numeric release")
        else:
            emit("FAIL", "version is not an Epic 5 numeric release")
            failures += 1

    print("\nOverall status: " + ("PASS" if failures == 0 else "FAIL"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
