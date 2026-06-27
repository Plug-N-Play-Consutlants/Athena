"""Doctor for Athena Cross-Domain Event Impact (0.5.2.2.1+)."""
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
    print("Cross-Domain Event Impact Doctor")
    print("=" * 64)
    checks: list[tuple[str, bool, str]] = []

    required = [
        "Core/version.py",
        "Engine/__init__.py",
        "Engine/Events/event_reasoning.py",
        "Engine/CrossDomain/cross_domain_engine.py",
        "Engine/CrossDomain/impact_models.py",
        "Engine/CrossDomain/impact_rules.py",
        "Engine/CrossDomain/domain_router.py",
        "Engine/CrossDomain/graph_delta_builder.py",
        "Engine/Evidence/__init__.py",
        "Knowledge/Events/feeds.py",
        "Knowledge/Events/acquisition.py",
        "Knowledge/Events/evidence_fusion.py",
        "Tests/validate_cross_domain_event_impact.py",
        "Tools/doctor_cross_domain_event_impact.py",
    ]
    for rel in required:
        checks.append(check(f"required file present: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    version_text = (PROJECT_ROOT / "Core/version.py").read_text(encoding="utf-8")
    current_version = _version_literal(version_text, "ATHENA_VERSION")
    checks.append(check("version metadata is 0.5.2.2.1 or later", _version_at_least(current_version, "0.5.2.2.1"), current_version or "Core/version.py"))

    imports = [
        ("Knowledge.Events", "seed_event_registry"),
        ("Knowledge.Events.feeds", "seed_feed_registry"),
        ("Knowledge.Events.acquisition", "StaticPayloadConnector"),
        ("Knowledge.Events.evidence_fusion", "fuse_events"),
        ("Engine.Events", "EventReasoningEngine"),
        ("Engine.CrossDomain", "CrossDomainImpactEngine"),
    ]
    for module_name, symbol in imports:
        try:
            module = importlib.import_module(module_name)
            checks.append(check(f"import {module_name}.{symbol}", hasattr(module, symbol), module_name))
        except Exception as exc:
            checks.append(check(f"import {module_name}", False, str(exc)))

    try:
        from Knowledge.Events import normalize_event_payload
        from Engine.CrossDomain import CrossDomainImpactEngine
        event = normalize_event_payload({
            "event_type": "trade",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player was traded.",
            "source_id": "nhl_api",
            "source_confidence": 0.95,
        })
        result = CrossDomainImpactEngine().propagate(event)
        checks.append(check("trade event propagates to multiple domains", len(result.impacts) >= 4 and len(result.graph_deltas) == len(result.impacts), f"impacts={len(result.impacts)} deltas={len(result.graph_deltas)}"))
    except Exception as exc:
        checks.append(check("cross-domain smoke test", False, str(exc)))

    print("-" * 64)
    failed = [item for item in checks if not item[1]]
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")
    print("Overall status:", "PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
