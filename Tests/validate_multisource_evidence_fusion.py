"""Validation for Athena 0.5.1.5.0 Multi-Source Evidence Fusion."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_EPIC, RELEASE_HOTFIX, RELEASE_NAME, RELEASE_PATCH, RELEASE_SPRINT, VERSION_SCHEMA
from Knowledge.Events import (
    EventEvidence,
    EventRecord,
    EvidenceFusionEngine,
    FusionResult,
    FusedEvidenceRecord,
    SourceConfidenceProfile,
    acquire_nhl_official_sample,
    event_fusion_key,
    fuse_event_evidence,
    seed_source_registry,
)


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    if len(parts) != 5 or not all(part.isdigit() for part in parts):
        return (0, 0, 0, 0, 0)
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def _event(event_id: str, source_id: str, summary: str = "Toronto acquired Player A", event_type: str = "trade") -> EventRecord:
    return EventRecord(
        event_id=event_id,
        event_type=event_type,
        sport="nhl",
        subject="Toronto Maple Leafs",
        summary=summary,
        occurred_at="2026-06-23T12:00:00+00:00",
        entities=["toronto-maple-leafs", "player-a"],
        evidence=[EventEvidence(source_id=source_id, title=summary, observed_at="2026-06-23T12:01:00+00:00", confidence=0.92, authority="official")],
        confidence=0.9,
        source_ids=[source_id],
    )


def main() -> int:
    print("Multi-Source Evidence Fusion Validation")
    print("=" * 64)
    checks: list[bool] = []

    checks.append(report("version is 0.5.1.5.0 or later", _version_at_least(ATHENA_VERSION, "0.5.1.5.0") and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("version uses locked schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix" and bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", ATHENA_VERSION)), VERSION_SCHEMA))
    checks.append(report("release metadata remains Epic 5", RELEASE_EPIC == "5" and RELEASE_SPRINT.isdigit() and RELEASE_PATCH.isdigit() and RELEASE_HOTFIX.isdigit(), RELEASE_NAME))

    registry = seed_source_registry()
    engine = EvidenceFusionEngine(registry)
    profile = engine.source_confidence("nhl_api")
    checks.append(report("source confidence profile is canonical", isinstance(profile, SourceConfidenceProfile) and profile.weight >= 0.9 and profile.authority == "official", str(profile.to_dict())))

    event_a = _event("evt-official", "nhl_api")
    event_b = _event("evt-newswire", "trusted_newswire")
    checks.append(report("duplicate event keys match across sources", event_fusion_key(event_a) == event_fusion_key(event_b), event_fusion_key(event_a)))

    result = fuse_event_evidence([event_a, event_b], registry)
    checks.append(report("fusion returns FusionResult", isinstance(result, FusionResult), type(result).__name__))
    checks.append(report("duplicate observations fuse into one record", result.fused_count == 1, result.to_dict().__repr__()[:240]))
    fused = result.fused_records[0]
    checks.append(report("fused record is canonical", isinstance(fused, FusedEvidenceRecord), type(fused).__name__))
    checks.append(report("supporting evidence preserves both sources", set(fused.source_ids) == {"nhl_api", "trusted_newswire"} and len(fused.supporting_evidence) == 2, str(fused.source_ids)))
    checks.append(report("corroborated evidence receives high confidence", fused.corroborated and fused.confidence >= 0.85, str(fused.to_dict())))
    checks.append(report("provenance keeps source ids and event ids", set(fused.event_ids) == {"evt-official", "evt-newswire"}, str(fused.event_ids)))

    single = fuse_event_evidence([event_a], registry).fused_records[0]
    checks.append(report("single-source event remains single_source", single.resolution_state == "single_source" and not single.corroborated, single.to_dict().__repr__()[:240]))

    conflict = engine.detect_conflicts([event_a, _event("evt-conflict", "trusted_newswire", "Toronto did not acquire Player A", event_type="injury")])
    checks.append(report("conflicting classifications are preserved", len(conflict) == 1 and conflict[0].resolution_state == "conflicted" and conflict[0].conflicting_evidence, conflict[0].to_dict().__repr__()[:240] if conflict else "none"))

    official_sample = acquire_nhl_official_sample()
    official_fusion = engine.fuse(official_sample.events)
    checks.append(report("official NHL sample fuses without network access", official_sample.status == "success" and official_fusion.fused_count >= 1, official_fusion.to_dict().__repr__()[:240]))
    checks.append(report("fusion remains Knowledge-layer only", not any(hasattr(record, "recommendation") or hasattr(record, "conclusion") for record in official_fusion.fused_records), "Reasoning owns conclusions"))

    failed = [ok for ok in checks if not ok]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
