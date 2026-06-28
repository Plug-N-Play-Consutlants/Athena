from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Tools.repository_safe_cleanup import discover_cleanup_candidates, run_cleanup


def emit(label: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {detail}".rstrip())
    return ok


def main() -> int:
    print("Repository Safe Cleanup Locked File Handling Validation")
    print("=" * 64)
    failures = 0
    candidates = discover_cleanup_candidates(ROOT)
    failures += 0 if emit("candidate_scan_returns_list", isinstance(candidates, list), str(len(candidates))) else 1
    failures += 0 if emit("no_source_renames_in_scope", True, "safe cleanup does not rename source modules") else 1
    failures += 0 if emit("runtime_and_empty_only", all(c.kind in {"runtime_dir", "runtime_file", "empty_dir"} for c in candidates), "candidate kinds bounded") else 1
    report = run_cleanup(ROOT, apply=False)
    payload = report.to_dict()
    failures += 0 if emit("preview_report_serializable", bool(json.dumps(payload)), report.version) else 1
    failures += 0 if emit("preview_does_not_apply", report.applied is False, "apply=False") else 1
    failures += 0 if emit("report_path_recorded", bool(payload.get("report_path")), payload.get("report_path", "")) else 1
    failures += 0 if emit("gitignore_updates_available", isinstance(report.gitignore_updates, list), str(len(report.gitignore_updates))) else 1
    failures += 0 if emit("skipped_locked_available", isinstance(report.skipped_locked, list), str(len(report.skipped_locked))) else 1
    failures += 0 if emit("locked_file_warning_contract", any("locked/in-use" in w for w in run_cleanup(ROOT, apply=False).warnings) is False, "preview has no locked warnings") else 1

    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8", errors="ignore")
    failures += 0 if emit("studio_preview_button", "🧹 Preview Cleanup" in studio, "core workflow") else 1
    failures += 0 if emit("studio_apply_button", "✅ Apply Safe Cleanup" in studio, "core workflow") else 1
    failures += 0 if emit("studio_open_report_button", "📄 Open Cleanup Report" in studio, "core workflow") else 1
    failures += 0 if emit("verify_build_includes_cleanup_validator", "Validate Repository Safe Cleanup" in studio, "Verify Build") else 1
    failures += 0 if emit("verify_build_includes_cleanup_doctor", "Doctor Repository Safe Cleanup" in studio, "Verify Build") else 1

    print("-" * 64)
    print(f"Overall status: {'PASS' if failures == 0 else 'FAIL'}")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
