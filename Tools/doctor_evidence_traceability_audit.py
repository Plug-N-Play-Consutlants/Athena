"""Doctor for Evidence Traceability Audit v0.5.5.5.20."""
from __future__ import annotations

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS = []


def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((name, condition, detail))


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    audit_tool = PROJECT_ROOT / "Tools" / "audit_evidence_paths.py"
    cleanup_tool = PROJECT_ROOT / "Tools" / "cleanup_repository_noise.py"
    audit_doc = PROJECT_ROOT / "docs" / "EVIDENCE_TRACEABILITY_AUDIT_v0.5.5.5.20.md"
    structure_doc = PROJECT_ROOT / "docs" / "REPOSITORY_NOISE_AND_CONSOLIDATION_AUDIT_v0.5.5.5.20.md"

    check("audit tool exists", audit_tool.exists(), str(audit_tool))
    check("cleanup planner exists", cleanup_tool.exists(), str(cleanup_tool))
    check("traceability doc exists", audit_doc.exists(), str(audit_doc))
    check("noise/consolidation doc exists", structure_doc.exists(), str(structure_doc))

    if audit_tool.exists():
        module = load_module(audit_tool)
        audit = module.build_audit()
        check("audit has canonical stages", len(audit.get("canonical_stages", [])) >= 8, str(audit.get("canonical_stages")))
        check("audit has prompt trace templates", len(audit.get("prompt_trace_templates", [])) >= 5, str(len(audit.get("prompt_trace_templates", []))))
        check("audit tracks route files", "Scout/conversation/router.py" in audit.get("runtime_route_files", []), str(audit.get("runtime_route_files", [])))
        check("audit inventory counts python files", audit.get("inventory", {}).get("python_files", 0) > 100, str(audit.get("inventory", {}).get("python_files")))

    if audit_doc.exists():
        text = audit_doc.read_text(encoding="utf-8", errors="replace")
        check("audit doc names vertical slice", "What is the Leafs weakness?" in text, "vertical slice")
        check("audit doc includes unused evidence concept", "Evidence Available but Unused" in text, "unused evidence")
        check("audit doc rejects premature reorg", "Do not reorganize yet" in text, "reorg guardrail")

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    failed = len(CHECKS) - passed
    print("Evidence Traceability Audit Doctor")
    print("=" * 52)
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print("-" * 52)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
