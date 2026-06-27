"""Doctor for the Athena Engine namespace foundation."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_FILES = [
    "Engine/__init__.py",
    "Engine/README.md",
    "Engine/Events/__init__.py",
    "Engine/Events/facade.py",
    "Engine/Evidence/__init__.py",
]

REQUIRED_IMPORTS = [
    "Engine",
    "Engine.Events",
    "Engine.Events.facade",
    "Engine.Evidence",
]


def main() -> int:
    print("Athena Engine Namespace Doctor")
    print("=" * 56)
    failures: list[str] = []

    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if path.exists():
            print(f"[PASS] file present: {rel}")
        else:
            msg = f"missing file: {rel}"
            print(f"[FAIL] {msg}")
            failures.append(msg)

    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
            print(f"[PASS] import: {module_name}")
        except Exception as exc:
            msg = f"import failed: {module_name}: {exc}"
            print(f"[FAIL] {msg}")
            failures.append(msg)

    try:
        from Engine.Events import build_event_engine
        engine = build_event_engine()
        summary = engine.summary()
        if summary.get("feed_count", 0) >= 1 and summary.get("source_count", 0) >= 1:
            print(f"[PASS] event engine summary: feeds={summary.get('feed_count')}; sources={summary.get('source_count')}")
        else:
            msg = f"event engine summary incomplete: {summary}"
            print(f"[FAIL] {msg}")
            failures.append(msg)
    except Exception as exc:
        msg = f"event engine construction failed: {exc}"
        print(f"[FAIL] {msg}")
        failures.append(msg)

    print()
    if failures:
        print("Overall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
