"""Validate Sprint 4A.3 public hockey source registry and shared bridge."""
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Sources.public_hockey_registry import (  # noqa: E402
    build_public_hockey_capability_report,
    default_public_hockey_sources,
    find_public_hockey_topics,
    write_public_hockey_registry_outputs,
)
try:
    from Core.version import ATHENA_VERSION
except Exception:  # pragma: no cover
    ATHENA_VERSION = "unknown"


class ValidationReport:
    def __init__(self) -> None:
        self.passed = []
        self.failed = []
        self.warnings = []

    def pass_(self, name: str, detail: str = "") -> None:
        self.passed.append((name, detail))

    def fail(self, name: str, detail: str = "") -> None:
        self.failed.append((name, detail))

    def warn(self, name: str, detail: str = "") -> None:
        self.warnings.append((name, detail))

    def print(self) -> None:
        print("Public Hockey Knowledge Registry Validation Report")
        print("===================================================")
        status = "PASS" if not self.failed else "FAIL"
        print(f"Overall status: {status}")
        print(f"Passed: {len(self.passed)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Failed: {len(self.failed)}")
        print("")
        for name, detail in self.passed:
            print(f"[PASS] {name}: {detail}")
        for name, detail in self.warnings:
            print(f"[WARN] {name}: {detail}")
        for name, detail in self.failed:
            print(f"[FAIL] {name}: {detail}")


def main() -> int:
    r = ValidationReport()

    sources = default_public_hockey_sources()
    source_ids = {s.source_id for s in sources}
    if {"nhl_official_rules_2025_2026", "nhl_nhlpa_mou_2025_06_27"}.issubset(source_ids):
        r.pass_("required_sources_registered", ", ".join(sorted(source_ids)))
    else:
        r.fail("required_sources_registered", ", ".join(sorted(source_ids)))

    modes_ok = all("public_sports" in s.modes and "fantasy_league" in s.modes for s in sources)
    if modes_ok:
        r.pass_("sources_available_to_public_and_fantasy_modes", "all registered sources expose both modes")
    else:
        r.fail("sources_available_to_public_and_fantasy_modes", "one or more sources missing shared modes")

    report = build_public_hockey_capability_report(ROOT)
    if report["source_count"] == 2 and report["topic_count"] >= 12:
        r.pass_("capability_report_shape", f"sources={report['source_count']}; topics={report['topic_count']}; status={report['status']}")
    else:
        r.fail("capability_report_shape", json.dumps(report, indent=2)[:500])

    cap_topics = find_public_hockey_topics("How does LTIR affect salary cap space?")
    cap_ids = {item["source_id"] for item in cap_topics}
    topic_keys = {item["topic"]["key"] for item in cap_topics}
    if "nhl_nhlpa_mou_2025_06_27" in cap_ids and {"ltir_lti", "salary_cap"}.intersection(topic_keys):
        r.pass_("ltir_salary_cap_routes_to_mou", ", ".join(sorted(topic_keys)))
    else:
        r.fail("ltir_salary_cap_routes_to_mou", json.dumps(cap_topics, indent=2))

    injury_topics = find_public_hockey_topics("What happens when a player is injured during a game?")
    injury_keys = {item["topic"]["key"] for item in injury_topics}
    if "injured_players" in injury_keys:
        r.pass_("injury_game_question_routes_to_rulebook", ", ".join(sorted(injury_keys)))
    else:
        r.fail("injury_game_question_routes_to_rulebook", json.dumps(injury_topics, indent=2))

    contract_topics = find_public_hockey_topics("no trade clause salary retention contract variability")
    contract_keys = {item["topic"]["key"] for item in contract_topics}
    expected = {"no_trade_lists", "salary_retention", "contract_variability"}
    if expected.issubset(contract_keys):
        r.pass_("contract_transaction_topics_registered", ", ".join(sorted(expected)))
    else:
        r.fail("contract_transaction_topics_registered", ", ".join(sorted(contract_keys)))

    paths = write_public_hockey_registry_outputs(ROOT)
    json_path = Path(paths["json"])
    txt_path = Path(paths["text"])
    if json_path.exists() and txt_path.exists():
        r.pass_("registry_outputs_written", f"json={json_path.name}; text={txt_path.name}")
    else:
        r.fail("registry_outputs_written", str(paths))

    if str(ATHENA_VERSION).endswith("drop4a3"):
        r.pass_("version_updated", f"Athena={ATHENA_VERSION}")
    else:
        r.fail("version_updated", f"Athena={ATHENA_VERSION}")

    r.print()
    return 1 if r.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
