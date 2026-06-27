"""Validation for Athena 0.5.3.1.0 Official Multi-Sport Provider Connectors."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    numeric = []
    for part in parts[:5]:
        try:
            numeric.append(int(part))
        except ValueError:
            numeric.append(0)
    while len(numeric) < 5:
        numeric.append(0)
    return tuple(numeric)  # type: ignore[return-value]

def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def main() -> int:
    print("Official Multi-Sport Provider Connectors Validation")
    print("=" * 64)
    checks: list[bool] = []

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    checks.append(report("version metadata is 0.5.3.1.0 or later", _version_at_least(ATHENA_VERSION, "0.5.3.1.0") and ATHENA_BUILD == ATHENA_VERSION and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", ATHENA_VERSION))
    checks.append(report("release name is available", bool(RELEASE_NAME), RELEASE_NAME))

    from Engine.MultiSport import connector_capability_report, run_official_connector, seed_multi_sport_registry
    registry = seed_multi_sport_registry()
    summary = registry.to_dict()
    expected_sports = {"nhl", "nfl", "nba", "mlb", "soccer"}
    expected_leagues = {"nhl", "nfl", "nba", "mlb", "uefa", "fifa"}
    checks.append(report("sport registry includes target sports", expected_sports.issubset(set(summary["sports"])), ", ".join(sorted(summary["sports"]))))
    checks.append(report("league registry includes target leagues", expected_leagues.issubset(set(summary["leagues"])), ", ".join(sorted(summary["leagues"]))))
    checks.append(report("official connector registry includes all target leagues", expected_leagues.issubset({c.league_id for c in registry.connectors.values()}), ", ".join(sorted(c.league_id for c in registry.connectors.values()))))

    report_payload = connector_capability_report(registry).to_dict()
    checks.append(report("capability report is offline-safe", report_payload["network_enabled"] is False, str(report_payload)))
    checks.append(report("capability report exposes connectors", len(report_payload["connectors"]) >= 6, str(report_payload["connectors"])))

    nhl = run_official_connector("nhl")
    nfl = run_official_connector("nfl", [{"event_type": "practice_report", "summary": "Quarterback limited in practice.", "subject": "Sample NFL Team"}])
    soccer = run_official_connector("uefa", [{"event_type": "transfer", "summary": "Club completed a transfer.", "subject": "Sample FC"}])
    checks.append(report("NHL connector returns canonical event", nhl.status == "success" and nhl.events and nhl.events[0].sport == "nhl", str(nhl.to_dict())))
    checks.append(report("NFL event alias normalizes to injury", nfl.events and nfl.events[0].event_type == "injury", str(nfl.to_dict())))
    checks.append(report("Soccer transfer normalizes to trade", soccer.events and soccer.events[0].event_type == "trade", str(soccer.to_dict())))

    from Knowledge.Events.multi_sport import multi_sport_event_framework_summary, acquire_sample_multi_sport_events
    knowledge_summary = multi_sport_event_framework_summary()
    checks.append(report("Knowledge surface exposes multi-sport summary", "nhl" in knowledge_summary["sports"] and "fifa" in knowledge_summary["leagues"], str(knowledge_summary.keys())))
    sample_events = acquire_sample_multi_sport_events(["nhl", "nba", "mlb"])
    checks.append(report("Knowledge surface acquires sample events", len(sample_events) == 3 and {e["sport"] for e in sample_events} == {"nhl", "nba", "mlb"}, str(sample_events)))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
