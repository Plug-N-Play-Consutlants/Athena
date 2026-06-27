"""Doctor for Athena 0.5.1.5.0 Multi-Source Evidence Fusion."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    if len(parts) != 5 or not all(part.isdigit() for part in parts):
        return (0, 0, 0, 0, 0)
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def _version_literal(text: str, name: str) -> str:
    import re
    match = re.search(rf'{name}\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else ""


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))
    return name, condition, detail


def main() -> int:
    print("Multi-Source Evidence Fusion Doctor")
    print("=" * 64)
    checks: list[tuple[str, bool, str]] = []

    version_file = PROJECT_ROOT / "Core" / "version.py"
    version_text = version_file.read_text(encoding="utf-8") if version_file.exists() else ""
    current_version = _version_literal(version_text, "ATHENA_VERSION")
    checks.append(check("version is 0.5.1.5.0 or later", _version_at_least(current_version, "0.5.1.5.0"), current_version or str(version_file)))

    required = [
        "Knowledge/Events/evidence_fusion.py",
        "Knowledge/Events/__init__.py",
        "Tests/validate_multisource_evidence_fusion.py",
        "Tools/doctor_multisource_evidence_fusion.py",
        "Tools/athena_studio.py",
    ]
    for rel in required:
        checks.append(check(f"required file present: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    try:
        events = importlib.import_module("Knowledge.Events")
        expected = ["EvidenceFusionEngine", "FusedEvidenceRecord", "FusionResult", "SourceConfidenceProfile", "fuse_event_evidence", "event_fusion_key"]
        checks.append(check("Evidence Fusion exports are available", all(hasattr(events, name) for name in expected), ", ".join(expected)))
        registry = events.seed_source_registry()
        engine = events.EvidenceFusionEngine(registry)
        checks.append(check("source confidence profile resolves official source", engine.source_confidence("nhl_api").weight >= 0.9, str(engine.source_confidence("nhl_api").to_dict())))
        sample = events.acquire_nhl_official_sample()
        result = engine.fuse(sample.events)
        checks.append(check("fusion engine accepts official NHL sample", result.fused_count >= 1 and result.fused_records[0].confidence >= 0.8, result.to_dict().__repr__()[:240]))
    except Exception as exc:
        checks.append(check("Evidence Fusion import/smoke test", False, str(exc)))

    studio_text = (PROJECT_ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    checks.append(check("Studio routes latest Event validator", "validate_multisource_evidence_fusion.py" in studio_text, "Validate Event Intelligence uses latest validator"))
    checks.append(check("Studio routes latest Event doctor", "doctor_multisource_evidence_fusion.py" in studio_text, "Doctor Event Intelligence uses latest doctor"))

    failed = [item for item in checks if not item[1]]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    if failed:
        for name, _, detail in failed:
            print(f"[FAIL] {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
