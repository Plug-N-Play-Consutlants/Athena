"""Validation for Evidence Traceability Audit v0.5.5.5.20."""
from __future__ import annotations

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    version_file = PROJECT_ROOT / "Core" / "version.py"
    audit_tool = PROJECT_ROOT / "Tools" / "audit_evidence_paths.py"
    audit_doc = PROJECT_ROOT / "docs" / "EVIDENCE_TRACEABILITY_AUDIT_v0.5.5.5.20.md"
    noise_doc = PROJECT_ROOT / "docs" / "REPOSITORY_NOISE_AND_CONSOLIDATION_AUDIT_v0.5.5.5.20.md"

    version_text = version_file.read_text(encoding="utf-8", errors="replace")
    record("version advanced to 0.5.5.5.20", 'ATHENA_VERSION = "0.5.5.5.20"' in version_text, str(version_file))
    record("release identifies traceability audit", "Evidence Traceability Audit" in version_text, "release name")

    module = load_module(audit_tool)
    audit = module.build_audit()
    md = module.render_markdown(audit)

    record("inventory total files present", audit["inventory"]["total_files"] >= 900, str(audit["inventory"]["total_files"]))
    record("inventory python files present", audit["inventory"]["python_files"] >= 500, str(audit["inventory"]["python_files"]))
    record("route files not missing", not audit.get("missing_route_files"), str(audit.get("missing_route_files")))
    record("prompt traces include Leafs weakness", any(t["example"] == "What is the Leafs weakness?" for t in audit["prompt_trace_templates"]), "targeted team weakness")
    record("prompt traces include live trades", any("trades" in t["example"].lower() for t in audit["prompt_trace_templates"]), "live trade path")
    record("consolidation targets are risk classified", all("risk" in t for t in audit["consolidation_targets"]), str(audit["consolidation_targets"]))
    record("markdown renders trace templates", "## Prompt trace templates" in md, "markdown")
    record("audit doc exists", audit_doc.exists(), str(audit_doc))
    record("noise doc exists", noise_doc.exists(), str(noise_doc))

    if audit_doc.exists():
        text = audit_doc.read_text(encoding="utf-8", errors="replace")
        record("audit doc has actual path focus", "actual path" in text.lower(), "actual path")
        record("audit doc includes evidence contract", "Evidence Requested" in text and "Evidence Discarded" in text, "evidence contract")
    if noise_doc.exists():
        text = noise_doc.read_text(encoding="utf-8", errors="replace")
        record("noise doc calls root manifests cleanup candidate", "Root-level release manifests" in text, "root manifests")
        record("noise doc avoids deleting runtime output blindly", "Do not delete" in text, "runtime guardrail")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    print("Evidence Traceability Audit Validation")
    print("=" * 52)
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print("-" * 52)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
