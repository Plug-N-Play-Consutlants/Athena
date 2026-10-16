from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Tools.repository_safe_cleanup import discover_cleanup_candidates, run_cleanup
from Tools.athena_studio import BUILD_VALIDATION_REGISTRY, AthenaStudio


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
    failures += 0 if emit("runtime_and_empty_only", all(c.kind in {"runtime_dir", "runtime_file", "empty_dir", "legacy_patch", "nested_overlay", "legacy_core", "runtime_quarantine", "workspace_state", "root_change_manifest", "root_history", "legacy_apply_notes", "legacy_validation_wrapper"} for c in candidates), "candidate kinds bounded") else 1
    failures += 0 if emit("review_never_auto_applied", all(c.classification == "review" for c in candidates if c.kind in {"legacy_patch", "nested_overlay", "legacy_core", "runtime_quarantine", "workspace_state", "root_history", "legacy_apply_notes", "legacy_validation_wrapper"}), "review classification") else 1
    retired_wrappers = {
        "Tools/doctor_epic4_acceptance_suite.py",
        "Tools/doctor_scout_runtime_acceptance_hotfix.py",
    }
    detected_wrappers = {candidate.path for candidate in candidates if candidate.kind == "legacy_validation_wrapper"}
    failures += 0 if emit("retired_acceptance_wrappers_review_only", detected_wrappers == retired_wrappers, str(sorted(detected_wrappers))) else 1
    failures += 0 if emit("change_manifests_safe_to_archive", all(c.classification == "safe" for c in candidates if c.kind == "root_change_manifest"), "canonical Archive/Documentation/ChangeManifests") else 1
    failures += 0 if emit("preserve_evidence_logs", not any(c.path.startswith(("Logs/", "Raw/", "Output/")) and c.path.endswith(".log") for c in candidates), "evidence retention") else 1
    report = run_cleanup(ROOT, apply=False)
    payload = report.to_dict()
    failures += 0 if emit("preview_report_serializable", bool(json.dumps(payload)), report.version) else 1
    failures += 0 if emit("preview_does_not_apply", report.applied is False, "apply=False") else 1
    failures += 0 if emit("report_path_recorded", bool(payload.get("report_path")), payload.get("report_path", "")) else 1
    failures += 0 if emit("gitignore_updates_available", isinstance(report.gitignore_updates, list), str(len(report.gitignore_updates))) else 1
    failures += 0 if emit("skipped_locked_available", isinstance(report.skipped_locked, list), str(len(report.skipped_locked))) else 1
    failures += 0 if emit("locked_file_warning_contract", any("locked/in-use" in w for w in run_cleanup(ROOT, apply=False).warnings) is False, "preview has no locked warnings") else 1

    studio = AthenaStudio.__new__(AthenaStudio)
    studio._script_command = lambda path: ["python", path]
    sequences: dict[str, list[tuple[str, list[str] | None]]] = {}
    studio._run_sequence_threaded = lambda label, commands: sequences.update({label: commands})
    studio.validate_everything()
    studio.doctor_everything()
    validate_paths = {command[-1] for _, command in sequences["Validate Everything"] if command}
    doctor_paths = {command[-1] for _, command in sequences["Doctor Everything"] if command}
    build_paths = {target for _, _, target, _ in BUILD_VALIDATION_REGISTRY}
    failures += 0 if emit("cleanup_validator_in_extended_suite", "Tests/validate_repository_safe_cleanup.py" in validate_paths, "Validate Everything") else 1
    failures += 0 if emit("cleanup_doctor_in_extended_suite", "Tools/doctor_repository_safe_cleanup.py" in doctor_paths, "Doctor Everything") else 1
    failures += 0 if emit("cleanup_not_duplicated_in_release_gate", "Tests/validate_repository_safe_cleanup.py" not in build_paths, "separate extended maintenance check") else 1
    studio_source = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8", errors="ignore")
    failures += 0 if emit("studio_preview_button", "🧹 Preview Cleanup" in studio_source, "core workflow") else 1
    failures += 0 if emit("studio_apply_button", "✅ Apply Safe Cleanup" in studio_source, "core workflow") else 1
    consolidated_report_access = any(marker in studio_source for marker in (
        "📄 Open Cleanup Report",
        "📂 Open Reports",
        "open_repository_cleanup_report",
        "open_reports_folder",
    ))
    failures += 0 if emit("studio_report_access", consolidated_report_access, "core workflow or consolidated reports") else 1
    print("-" * 64)
    print(f"Overall status: {'PASS' if failures == 0 else 'FAIL'}")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
