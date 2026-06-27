"""Doctor for Athena v0.5.5.2.0 Cross-Sport Reasoning Engine."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(condition), detail))


def main() -> int:
    print("Cross-Sport Reasoning Engine Doctor")
    print("=" * 64)
    required = [
        "Intelligence/Reasoning/__init__.py",
        "Intelligence/Reasoning/models.py",
        "Intelligence/Reasoning/adapters.py",
        "Intelligence/Reasoning/engine.py",
        "Tests/validate_cross_sport_reasoning_engine.py",
        "Tools/doctor_cross_sport_reasoning_engine.py",
    ]
    for rel in required:
        check(f"required file exists: {rel}", (ROOT / rel).exists(), rel)

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    version_tuple = tuple(map(int, ATHENA_VERSION.split(".")))
    check("version metadata", ATHENA_VERSION == ATHENA_BUILD and version_tuple >= (0, 5, 5, 2, 0) and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", ATHENA_VERSION)
    check("release name", bool(RELEASE_NAME), RELEASE_NAME)

    from Intelligence.Reasoning import (
        CROSS_SPORT_REASONING_VERSION,
        seed_reasoning_adapter_registry,
        adapter_registry_diagnostics,
        reason_cross_sport_query,
        studio_reasoning_diagnostics,
    )
    check("reasoning version", tuple(map(int, CROSS_SPORT_REASONING_VERSION.split("."))) >= (0, 5, 5, 2, 0), CROSS_SPORT_REASONING_VERSION)

    registry = seed_reasoning_adapter_registry()
    stats = registry.stats()
    check("adapter registry", stats["adapters"] >= 5 and "hockey" in stats["sports"] and "basketball" in stats["sports"], str(stats))
    check("adapter diagnostics", adapter_registry_diagnostics()["status"] == "pass", str(adapter_registry_diagnostics()["stats"]))

    nhl = reason_cross_sport_query("Compare Auston Matthews vs Connor McDavid in the NHL")
    payload = nhl.to_dict()
    check("reasoning result has route", payload["route"] != "unavailable", payload["route"])
    check("reasoning result has adapter", payload["adapter"] == "Hockey Reasoning", payload["adapter"])
    check("reasoning result fuses evidence", payload["evidence_count"] >= 4, str(payload["evidence_count"]))
    check("reasoning result has steps", len(payload["reasoning_steps"]) >= 6, str(payload["reasoning_steps"]))
    check("comparison framing", payload["comparison"]["enabled"] is True, str(payload["comparison"]))

    event = reason_cross_sport_query("Summarize Blue Jays injuries")
    check("baseball adapter resolves", event.adapter == "Baseball Reasoning" and event.intent == "event_context", str(event.to_dict()))

    diag = studio_reasoning_diagnostics()
    check("Studio reasoning diagnostics", diag["panel"] == "cross_sport_reasoning" and diag["status"] == "pass", str(diag.keys()))

    from Knowledge.Intelligence.Routing.multi_sport_router import studio_route_diagnostics
    route_diag = studio_route_diagnostics()
    check("routing diagnostics include reasoning", route_diag.get("reasoning", {}).get("panel") == "cross_sport_reasoning", str(route_diag.keys()))

    failed = [row for row in CHECKS if not row[1]]
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
