"""Validate Sprint 4A.5 public hockey knowledge retrieval."""
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Sources.public_hockey_packs import build_public_hockey_knowledge_packs  # noqa: E402
from Knowledge.Sources.public_hockey_retrieval import (  # noqa: E402
    build_public_hockey_scout_answer,
    retrieve_public_hockey_knowledge,
    write_public_hockey_retrieval_report,
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
        print("Public Hockey Knowledge Retrieval Validation Report")
        print("====================================================")
        print(f"Overall status: {'PASS' if not self.failed else 'FAIL'}")
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


def _topic_keys(result):
    return {item.get("topic_key") for item in result.get("evidence", [])}


def main() -> int:
    r = ValidationReport()

    summary = build_public_hockey_knowledge_packs(ROOT)
    if summary.get("packs_present") == 2:
        r.pass_("packs_ready", f"packs={summary.get('packs_present')}; document_backed={summary.get('document_backed_packs')}")
    else:
        r.fail("packs_ready", json.dumps(summary, indent=2)[:1200])

    ltir = retrieve_public_hockey_knowledge("How does LTIR affect the salary cap?", ROOT, mode="public_sports")
    if ltir["status"] == "available" and "ltir_lti" in _topic_keys(ltir):
        r.pass_("ltir_query_matches_cba", f"confidence={ltir['confidence']}; topics={sorted(_topic_keys(ltir))}")
    else:
        r.fail("ltir_query_matches_cba", json.dumps(ltir, indent=2)[:1200])

    waivers = retrieve_public_hockey_knowledge("Does this player need waivers?", ROOT, mode="fantasy_league")
    if waivers["status"] == "available" and "waiver_system_access" in _topic_keys(waivers):
        r.pass_("fantasy_mode_can_use_public_hockey_knowledge", f"topics={sorted(_topic_keys(waivers))}")
    else:
        r.fail("fantasy_mode_can_use_public_hockey_knowledge", json.dumps(waivers, indent=2)[:1200])

    icing = retrieve_public_hockey_knowledge("What is icing?", ROOT, mode="public_sports")
    if icing["status"] == "available" and "game_flow" in _topic_keys(icing):
        refs = [ref for item in icing["evidence"] for ref in item.get("authority_refs", [])]
        r.pass_("icing_query_matches_rulebook", "; ".join(refs[:3]))
    else:
        r.fail("icing_query_matches_rulebook", json.dumps(icing, indent=2)[:1200])

    answer = build_public_hockey_scout_answer("Explain LTIR and playoff cap counting", ROOT, mode="public_sports")
    trace = answer.get("developer_trace", {})
    if answer.get("confidence", 0) > 0 and trace.get("evidence_used"):
        r.pass_("scout_answer_shape", f"title={answer.get('title')}; evidence={len(trace.get('evidence_used', []))}")
    else:
        r.fail("scout_answer_shape", json.dumps(answer, indent=2)[:1200])

    report_paths = write_public_hockey_retrieval_report("LTIR waivers icing", ROOT)
    if Path(report_paths["json"]).exists() and Path(report_paths["text"]).exists():
        r.pass_("retrieval_reports_written", f"json={Path(report_paths['json']).name}; text={Path(report_paths['text']).name}")
    else:
        r.fail("retrieval_reports_written", json.dumps(report_paths))

    no_match = retrieve_public_hockey_knowledge("What did the mascot eat for breakfast?", ROOT)
    if no_match["status"] == "no_match" and no_match["evidence_count"] == 0:
        r.pass_("unsupported_query_bounded", f"status={no_match['status']}; confidence={no_match['confidence']}")
    else:
        r.fail("unsupported_query_bounded", json.dumps(no_match, indent=2)[:1200])

    if ATHENA_VERSION == "0.5.0-drop4a5":
        r.pass_("version_updated", f"Athena={ATHENA_VERSION}")
    else:
        r.fail("version_updated", f"Athena={ATHENA_VERSION}")

    r.print()
    return 1 if r.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
