"""Validation for Athena Engine namespace foundation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def expect(condition: bool, label: str, details: str = "") -> list[str]:
    if condition:
        print(f"[PASS] {label}" + (f": {details}" if details else ""))
        return []
    print(f"[FAIL] {label}" + (f": {details}" if details else ""))
    return [label if not details else f"{label}: {details}"]


def main() -> int:
    print("Athena Engine Namespace Validation")
    print("=" * 56)
    failures: list[str] = []

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, REPOSITORY_NAME, PYTHON_PACKAGE_NAME
    failures += expect((ATHENA_VERSION.startswith("0.5.2.") or ATHENA_VERSION.startswith("0.5.3.")), "version metadata", ATHENA_VERSION)
    failures += expect((ATHENA_BUILD.startswith("0.5.2.") or ATHENA_BUILD.startswith("0.5.3.")), "build metadata", ATHENA_BUILD)
    failures += expect(bool(RELEASE_NAME), "release name available", RELEASE_NAME)
    failures += expect(REPOSITORY_NAME == "AthenaEngine", "repository name", REPOSITORY_NAME)
    failures += expect(PYTHON_PACKAGE_NAME == "Athena", "python package remains Athena", PYTHON_PACKAGE_NAME)

    from Engine import ENGINE_NAMESPACE_VERSION
    from Engine.Events import EventEngineFacade, build_event_engine
    from Engine.Evidence import EVIDENCE_ENGINE_VERSION, fuse_event_evidence

    failures += expect((ENGINE_NAMESPACE_VERSION.startswith("0.5.2.") or ENGINE_NAMESPACE_VERSION.startswith("0.5.3.")), "engine namespace version", ENGINE_NAMESPACE_VERSION)
    failures += expect(EVIDENCE_ENGINE_VERSION == "0.5.2.0.0", "evidence namespace version", EVIDENCE_ENGINE_VERSION)
    failures += expect(callable(fuse_event_evidence), "evidence fusion export callable")

    event_engine = build_event_engine()
    failures += expect(isinstance(event_engine, EventEngineFacade), "event engine facade constructed")
    summary = event_engine.summary()
    failures += expect(summary.get("feed_count", 0) >= 1, "event engine sees feed registry", str(summary.get("feed_count")))
    failures += expect(summary.get("source_count", 0) >= 1, "event engine sees source registry", str(summary.get("source_count")))
    failures += expect("connector_types" in summary and len(summary.get("connector_types") or []) >= 1, "event engine sees connector registry", ", ".join(summary.get("connector_types") or []))

    feeds = event_engine.discover(sport="nhl")
    failures += expect(len(feeds) >= 1, "event engine discovers NHL feeds", str(len(feeds)))
    result = event_engine.acquire(feeds[0].feed_id)
    failures += expect(hasattr(result, "to_dict"), "event engine acquisition returns FeedResult-compatible object")

    # Guardrail: Engine is a facade namespace, not a replacement for Knowledge facts.
    failures += expect((ROOT / "Knowledge" / "Events").exists(), "Knowledge.Events remains factual owner")
    failures += expect((ROOT / "Reasoning").exists(), "Reasoning layer remains present")
    failures += expect((ROOT / "Scout").exists(), "Scout layer remains present")

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
