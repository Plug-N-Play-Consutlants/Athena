"""Doctor for Athena 0.5.1.1.x Event Registry & Source Intelligence."""
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
    print("Event Registry & Source Intelligence Doctor")
    print("=" * 64)
    checks: list[tuple[str, bool, str]] = []

    version_file = PROJECT_ROOT / "Core" / "version.py"
    version_text = version_file.read_text(encoding="utf-8") if version_file.exists() else ""
    checks.append(check("version is Epic 5 event release", ('ATHENA_VERSION = "0.5.1.' in version_text or 'ATHENA_VERSION = "0.5.2.' in version_text), str(version_file)))
    checks.append(check("release metadata preserves Event Registry patch lineage", 'RELEASE_EPIC = "5"' in version_text and 'RELEASE_SPRINT = "1"' in version_text, "release metadata"))
    checks.append(check("repository standard remains AthenaEngine", 'REPOSITORY_NAME = "AthenaEngine"' in version_text and 'PYTHON_PACKAGE_NAME = "Athena"' in version_text, "root renamed; package preserved"))

    required = [
        "Knowledge/Events/__init__.py",
        "Knowledge/Events/models.py",
        "Knowledge/Events/registry.py",
        "Knowledge/Events/source_intelligence.py",
        "Knowledge/Events/normalizer.py",
        "Knowledge/Events/event_graph.py",
        "Tests/validate_event_registry_source_intelligence.py",
        "Tools/doctor_event_registry_source_intelligence.py",
    ]
    for rel in required:
        checks.append(check(f"required file present: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    try:
        events = importlib.import_module("Knowledge.Events")
        source_registry = events.seed_source_registry()
        checks.append(check("source registry imports and seeds", len(source_registry.sources) >= 7, f"sources={len(source_registry.sources)}"))
        checks.append(check("primary fact sources available", len(source_registry.primary_fact_sources()) >= 5, f"primary={len(source_registry.primary_fact_sources())}"))
        checks.append(check("opinion sources deprioritized", all(src.opinion_weight <= 0.25 for src in source_registry.primary_fact_sources()), "primary sources exclude high-opinion sources"))
        checks.append(check("expanded event taxonomy present", {"trade", "injury", "free_agent_signing", "contract_extension", "game_result"}.issubset(set(events.EVENT_TYPES)), ", ".join(events.EVENT_TYPES)))
    except Exception as exc:
        checks.append(check("event/source registry imports", False, str(exc)))

    try:
        from Knowledge.Events import bind_event_to_graph, normalize_event_payload
        record = normalize_event_payload({
            "event_type": "signing",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player signed with Team B.",
            "entities": ["Example Player", "Team B"],
            "source_id": "nhl_api",
            "published_at": "2026-06-23T12:00:00+00:00",
        })
        graph, binding = bind_event_to_graph(record)
        checks.append(check("normalizer canonicalizes event aliases", record.event_type == "free_agent_signing", record.event_type))
        checks.append(check("normalizer applies source confidence", record.confidence >= 0.75, f"confidence={record.confidence:.3f}"))
        checks.append(check("graph binding creates event/source/entity/evidence nodes", len(binding.source_node_ids) >= 1 and len(binding.entity_node_ids) >= 2 and len(binding.evidence_node_ids) >= 1, str(binding.to_dict())))
        checks.append(check("graph binding creates relationships", graph.to_dict()["relationship_count"] >= 4, f"relationships={graph.to_dict()['relationship_count']}"))
        checks.append(check("knowledge boundary preserved", not hasattr(record, "conclusion") and not hasattr(record, "recommendation"), "facts only"))
    except Exception as exc:
        checks.append(check("event normalization and graph binding", False, str(exc)))

    failed = [item for item in checks if not item[1]]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    if failed:
        for name, _, detail in failed:
            print(f"[FAIL] {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
