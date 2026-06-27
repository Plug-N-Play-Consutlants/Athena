"""Validate Sprint 4A.4 public hockey compact knowledge packs."""
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Sources.public_hockey_packs import (  # noqa: E402
    build_public_hockey_knowledge_packs,
    load_public_hockey_pack_summary,
    public_hockey_pack_status,
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
        print("Public Hockey Knowledge Pack Validation Report")
        print("==============================================")
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


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    r = ValidationReport()

    summary = build_public_hockey_knowledge_packs(ROOT)
    if summary["pack_count"] == 2 and summary["packs_present"] == 2:
        r.pass_("packs_built", f"packs={summary['pack_count']}; present={summary['packs_present']}")
    else:
        r.fail("packs_built", json.dumps(summary, indent=2)[:1000])

    expected_roots = [
        ROOT / "Knowledge" / "Packs" / "NHL" / "rulebook" / "2025_2026",
        ROOT / "Knowledge" / "Packs" / "NHL" / "cba" / "2025_mou",
    ]
    missing = [str(path) for path in expected_roots if not (path / "manifest.json").exists()]
    if not missing:
        r.pass_("expected_pack_directories", "; ".join(str(p.relative_to(ROOT)) for p in expected_roots))
    else:
        r.fail("expected_pack_directories", "; ".join(missing))

    rule_manifest = _read_json(expected_roots[0] / "manifest.json")
    cba_manifest = _read_json(expected_roots[1] / "manifest.json")
    if rule_manifest["document_type"] == "official_rulebook" and cba_manifest["document_type"] == "cba_mou":
        r.pass_("manifest_document_types", f"{rule_manifest['document_type']}; {cba_manifest['document_type']}")
    else:
        r.fail("manifest_document_types", json.dumps([rule_manifest, cba_manifest], indent=2)[:1000])

    if rule_manifest["source_document"]["present"] and cba_manifest["source_document"]["present"]:
        r.pass_("packs_are_document_backed", f"rulebook={rule_manifest['source_document']['size_bytes']}; mou={cba_manifest['source_document']['size_bytes']}")
    else:
        r.warn("packs_are_document_backed", "PDFs not detected in Knowledge/Sources/Documents; packs remain metadata-backed")

    rule_index = _read_json(expected_roots[0] / "topic_index.json")
    cba_index = _read_json(expected_roots[1] / "topic_index.json")
    if "icing" in rule_index and "ltir" in cba_index and "waivers" in cba_index:
        r.pass_("topic_indexes_searchable", "icing/ltir/waivers indexed")
    else:
        r.fail("topic_indexes_searchable", json.dumps({"rule": rule_index, "cba": cba_index}, indent=2)[:1200])

    rule_body = _read_json(expected_roots[0] / "rules.json")
    cba_body = _read_json(expected_roots[1] / "provisions.json")
    if len(rule_body) >= 5 and len(cba_body) >= 8:
        r.pass_("compact_body_files_written", f"rules={len(rule_body)}; provisions={len(cba_body)}")
    else:
        r.fail("compact_body_files_written", f"rules={len(rule_body)}; provisions={len(cba_body)}")

    loaded = load_public_hockey_pack_summary(ROOT)
    if loaded.get("status") == "available" and loaded.get("pack_count") == 2:
        r.pass_("summary_output_loadable", f"status={loaded.get('status')}; packs={loaded.get('pack_count')}")
    else:
        r.fail("summary_output_loadable", json.dumps(loaded, indent=2)[:1000])

    status = public_hockey_pack_status(ROOT)
    if status["pack_status"] == "available" and status["packs_present"] == 2:
        r.pass_("doctor_ready_pack_status", json.dumps(status, sort_keys=True))
    else:
        r.fail("doctor_ready_pack_status", json.dumps(status, indent=2))

    if str(ATHENA_VERSION).endswith("drop4a4"):
        r.pass_("version_updated", f"Athena={ATHENA_VERSION}")
    else:
        r.fail("version_updated", f"Athena={ATHENA_VERSION}")

    r.print()
    return 1 if r.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
