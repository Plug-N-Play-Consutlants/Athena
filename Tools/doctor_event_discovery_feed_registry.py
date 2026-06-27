"""Doctor for Athena 0.5.1.2.0 Event Discovery & Feed Registry."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))
    return name, condition, detail


def main() -> int:
    print("Event Discovery & Feed Registry Doctor")
    print("=" * 64)
    checks: list[tuple[str, bool, str]] = []

    version_file = PROJECT_ROOT / "Core" / "version.py"
    version_text = version_file.read_text(encoding="utf-8") if version_file.exists() else ""
    checks.append(check("version is 0.5.1.2.0 or later", 'VERSION_SCHEMA = "major.epic.sprint.patch.hotfix"' in version_text and ('ATHENA_VERSION = "0.5.1.2.0"' in version_text or 'ATHENA_VERSION = "0.5.1.3.' in version_text or 'ATHENA_VERSION = "0.5.1.4.' in version_text or 'ATHENA_VERSION = "0.5.1.5.' in version_text or 'ATHENA_VERSION = "0.5.2.' in version_text), str(version_file)))
    checks.append(check("repository standard remains AthenaEngine", 'REPOSITORY_NAME = "AthenaEngine"' in version_text and 'PYTHON_PACKAGE_NAME = "Athena"' in version_text, "root renamed; package preserved"))

    required = [
        "Knowledge/Events/feeds.py",
        "Knowledge/Events/__init__.py",
        "Tests/validate_event_discovery_feed_registry.py",
        "Tools/doctor_event_discovery_feed_registry.py",
        "Tests/validate_event_registry_source_intelligence.py",
        "Tools/doctor_event_registry_source_intelligence.py",
    ]
    for rel in required:
        checks.append(check(f"required file present: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    try:
        events = importlib.import_module("Knowledge.Events")
        registry = events.seed_feed_registry()
        checks.append(check("feed registry imports and seeds", len(registry.feeds) >= 7, f"feeds={len(registry.feeds)}"))
        checks.append(check("feed health map is complete", len(registry.health) == len(registry.feeds), f"health={len(registry.health)}"))
        checks.append(check("official NHL feed is available", registry.get("nhl_official_transactions") is not None and registry.get("nhl_official_transactions").source_id == "nhl_api", "nhl_official_transactions"))
        checks.append(check("opinion monitor is disabled", registry.get("opinion_article_monitor") is not None and not registry.get("opinion_article_monitor").enabled, "opinion_article_monitor"))
        result = events.discover_feeds(sport="nhl", league="nhl", event_type="trade", registry=registry)
        checks.append(check("discovery returns compatible feeds", result.to_dict()["feed_count"] >= 3, str([feed.feed_id for feed in result.feeds])))
        checks.append(check("discovery prefers official source", result.best_feed() is not None and result.best_feed().feed_id == "nhl_official_transactions", result.best_feed().feed_id if result.best_feed() else "none"))
        plan = events.build_ingestion_plan(result.best_feed(), event_type_hint="trade")
        checks.append(check("ingestion plan has canonical stages", plan.stages == ["feed", "fetch", "normalize", "canonical_event", "evidence", "knowledge"], str(plan.to_dict())))
        record = events.ingest_static_event_payload({"event_type": "trade", "summary": "Example trade", "subject": "Example Player"}, feed=result.best_feed())
        checks.append(check("static ingestion normalizes event", record.event_type == "trade" and record.source_ids == ["nhl_api"], str(record.to_dict())))
        summary = events.feed_registry_summary(registry)
        checks.append(check("feed registry summary exposes type and health counts", summary["feed_count"] >= 7 and summary["healthy_feed_count"] >= 4 and "official_api" in summary["feed_types"], str(summary)))
    except Exception as exc:
        checks.append(check("feed registry imports and contracts", False, str(exc)))

    failed = [item for item in checks if not item[1]]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    if failed:
        for name, _, detail in failed:
            print(f"[FAIL] {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
