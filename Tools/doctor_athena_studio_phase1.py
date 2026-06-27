"""Doctor for Athena Studio Phase 1 command-center build."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"

CHECKS = [
    ("runtime validator", ROOT / "Tests" / "validate_runtime_cleanup.py"),
    ("pif validator", ROOT / "Tests" / "validate_pif1_build001.py"),
    ("studio validator", ROOT / "Tests" / "validate_athena_studio_phase1.py"),
    ("runtime doctor", ROOT / "Tools" / "doctor_runtime_cleanup.py"),
    ("pif doctor", ROOT / "Tools" / "doctor_pif1_build001.py"),
    ("studio doctor", ROOT / "Tools" / "doctor_athena_studio_phase1.py"),
    ("runtime cleanup tool", ROOT / "Tools" / "runtime_cleanup.py"),
]


def main() -> int:
    print("Athena Studio Phase 1 Doctor")
    print("=" * 52)
    failures: list[str] = []

    for label, path in CHECKS:
        if path.exists():
            print(f"[PASS] {label}: {path}")
        else:
            failures.append(f"Missing {label}: {path}")

    spec = importlib.util.spec_from_file_location("athena_studio_probe", STUDIO)
    if spec and spec.loader:
        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"[PASS] studio import: {STUDIO}")
            athena_version = getattr(module, "ATHENA_VERSION", "")
            scout_version = getattr(module, "SCOUT_VERSION", "")
            athena_build = getattr(module, "ATHENA_BUILD", "")
            if (
                isinstance(athena_version, str)
                and athena_version.startswith("0.5.0-drop4e")
                and scout_version == "v" + athena_version
                and isinstance(athena_build, str)
                and athena_build.startswith("drop4e")
            ):
                print(f"[PASS] studio version metadata loaded: {athena_version}")
            else:
                failures.append(
                    "Studio version metadata mismatch: "
                    f"ATHENA_VERSION={athena_version!r}, "
                    f"SCOUT_VERSION={scout_version!r}, "
                    f"ATHENA_BUILD={athena_build!r}"
                )
        except Exception as exc:
            failures.append(f"Studio import failed: {exc}")
    else:
        failures.append("Could not create import spec for Studio")

    text = STUDIO.read_text(encoding="utf-8") if STUDIO.exists() else ""
    if "HISTORY_FILE" in text and "athena_studio_history.jsonl" in text:
        print("[PASS] validation/runtime history support present")
    else:
        failures.append("Studio history support missing")

    if "create_diagnostic_bundle" in text and "zipfile.ZipFile" in text:
        print("[PASS] diagnostic bundle support present")
    else:
        failures.append("Diagnostic bundle support missing")

    if failures:
        print("\nOverall status: FAIL")
        for item in failures:
            print(f"[FAIL] {item}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
