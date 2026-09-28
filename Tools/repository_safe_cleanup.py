from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SAFE_RUNTIME_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

SAFE_RUNTIME_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
}

LOCKED_FILE_WARNING_PREFIX = "Skipped locked/in-use file"

SAFE_RUNTIME_PREFIXES = (
    "diagnostics_export_",
    "execution_trace_doctor_tmp",
)

SEMANTIC_EMPTY_DIR_ALLOWLIST = {
    "Archive",
    "Configuration",
    "Core",
    "Engine",
    "Intelligence",
    "Knowledge",
    "Providers",
    "Reasoning",
    "Reports",
    "Scout",
    "Sports",
    "Studio",
    "Tests",
    "Tools",
    "docs",
}

GITIGNORE_LINES = [
    "",
    "# Athena runtime artifacts",
    "Reports/diagnostics_export_*/",
    "Reports/execution_trace_doctor_tmp/",
    "Reports/**/execution_trace_doctor_tmp/",
    "*.pyc",
    "*.pyo",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "*.log",
]

@dataclass(frozen=True)
class CleanupCandidate:
    path: str
    kind: str
    reason: str
    classification: str = "safe"

@dataclass(frozen=True)
class CleanupReport:
    version: str
    generated_at: str
    project_root: str
    applied: bool
    candidates: list[CleanupCandidate]
    removed: list[str]
    gitignore_updates: list[str]
    warnings: list[str]
    skipped_locked: list[str]
    report_path: str = ""

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["candidates"] = [asdict(c) for c in self.candidates]
        return payload


def project_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_runtime_dir(path: Path) -> bool:
    name = path.name
    if name in SAFE_RUNTIME_DIR_NAMES:
        return True
    return any(name.startswith(prefix) for prefix in SAFE_RUNTIME_PREFIXES)


def _is_runtime_file(path: Path) -> bool:
    if path.suffix.lower() in SAFE_RUNTIME_SUFFIXES:
        return True
    return False


def discover_cleanup_candidates(root: Path) -> list[CleanupCandidate]:
    candidates: list[CleanupCandidate] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if ".git/" in rel or rel == ".git" or rel.startswith(("AthenaEngine/", "Intelligence/" + "Core/", "Archive/runtime_quarantine/")) or path.is_symlink():
            continue
        if any(_is_runtime_dir(parent) for parent in path.parents if parent != root and root in parent.parents):
            continue
        if path.is_dir() and _is_runtime_dir(path):
            candidates.append(CleanupCandidate(rel, "runtime_dir", "Generated runtime/cache directory."))
            continue
        if path.is_file() and _is_runtime_file(path):
            candidates.append(CleanupCandidate(rel, "runtime_file", "Generated runtime/log/cache file."))
            continue
        if path.is_file() and path.parent == root and (path.name.endswith(".patch") or path.name.startswith(("APPLY_", "APPLY_NOTES_"))):
            candidates.append(CleanupCandidate(rel, "legacy_patch", "Old patch/apply artifact; review before removal.", "review"))
            continue
        if path.is_dir() and path.parent == root and path.name == "AthenaEngine":
            candidates.append(CleanupCandidate(rel, "nested_overlay", "Nested overlay may contain an older build; review before removal.", "review"))
            continue
        if path.is_dir():
            try:
                if not any(path.iterdir()) and path.name not in SEMANTIC_EMPTY_DIR_ALLOWLIST:
                    candidates.append(CleanupCandidate(rel, "empty_dir", "Empty non-semantic directory."))
            except OSError:
                pass
    # Preserve evidence and source: consensus actions remain visible as review items.
    for rel, kind in (("Intelligence/" + "Core", "legacy_core"), ("Archive/runtime_quarantine", "runtime_quarantine"), ("Configuration/workspace.json", "workspace_state")):
        if (root / rel).exists():
            candidates.append(CleanupCandidate(rel, kind, "Legacy consensus action; requires separate ownership review.", "review"))
    for path in root.iterdir():
        if path.is_file() and path.name.startswith("README_") and "apply_notes" in path.name.lower() and path.suffix.lower() == ".txt":
            candidates.append(CleanupCandidate(path.name, "legacy_apply_notes", "Old installation notes; review before archival or removal.", "review"))
        if path.is_file() and path.suffix.lower() == ".md" and path.name.startswith("CHANGE_MANIFEST_"):
            candidates.append(CleanupCandidate(path.name, "root_change_manifest", "Historical change manifest; archive to canonical change-manifest history."))
        elif path.is_file() and path.suffix.lower() == ".md" and path.name.startswith(("RELEASE_NOTES_", "CLEANUP_REPORT_", "README_")):
            candidates.append(CleanupCandidate(path.name, "root_history", "Historical documentation; review archival.", "review"))
    return sorted(set(candidates), key=lambda c: c.path)


def update_gitignore(root: Path, apply: bool = False) -> list[str]:
    gitignore = root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    missing = [line for line in GITIGNORE_LINES if line and line not in existing]
    if apply and missing:
        with gitignore.open("a", encoding="utf-8", newline="\n") as handle:
            for line in GITIGNORE_LINES:
                if line == "":
                    handle.write("\n")
                elif line not in existing:
                    handle.write(line + "\n")
    return missing


def apply_candidates(root: Path, candidates: Iterable[CleanupCandidate]) -> tuple[list[str], list[str]]:
    removed: list[str] = []
    skipped_locked: list[str] = []
    for candidate in candidates:
        path = root / candidate.path
        if candidate.classification != "safe" or not path.exists() or path.is_symlink():
            continue
        try:
            if candidate.kind == "runtime_dir":
                shutil.rmtree(path)
                removed.append(candidate.path)
            elif candidate.kind == "runtime_file":
                path.unlink(missing_ok=True)
                removed.append(candidate.path)
            elif candidate.kind == "empty_dir":
                path.rmdir()
                removed.append(candidate.path)
            elif candidate.kind == "root_change_manifest":
                destination_dir = root / "Archive" / "Documentation" / "ChangeManifests"
                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = destination_dir / path.name
                if destination.exists():
                    if destination.read_bytes() != path.read_bytes():
                        skipped_locked.append(candidate.path)
                        continue
                    path.unlink()
                else:
                    shutil.move(str(path), str(destination))
                removed.append(candidate.path)
        except PermissionError:
            skipped_locked.append(candidate.path)
        except OSError as exc:
            # Windows raises WinError 32 as OSError/PermissionError depending on call site.
            if getattr(exc, "winerror", None) == 32:
                skipped_locked.append(candidate.path)
            elif candidate.kind == "empty_dir":
                # Non-empty-by-the-time-we-delete empty dirs are harmless.
                continue
            else:
                skipped_locked.append(candidate.path)
    return removed, skipped_locked


def _current_version() -> str:
    import sys
    root = str(project_root_from_here())
    if root not in sys.path:
        sys.path.insert(0, root)
    from Core.version import ATHENA_VERSION
    return ATHENA_VERSION


def run_cleanup(root: Path | None = None, apply: bool = False) -> CleanupReport:
    project_root = (root or project_root_from_here()).resolve()
    candidates = discover_cleanup_candidates(project_root)
    gitignore_updates = update_gitignore(project_root, apply=apply)
    removed: list[str] = []
    skipped_locked: list[str] = []
    if apply:
        removed, skipped_locked = apply_candidates(project_root, candidates)
    warnings: list[str] = []
    if any(c.classification == "review" for c in candidates):
        warnings.append("Review candidates are reported only and never deleted by Apply Safe Cleanup.")
    if not apply:
        warnings.append("Preview mode only. Use Apply Safe Cleanup in Studio to remove safe runtime artifacts.")
    if skipped_locked:
        warnings.append(f"{len(skipped_locked)} locked/in-use file(s) were skipped. Relaunch Studio and rerun cleanup if they still need removal.")
    reports = project_root / "Reports" / "repository_cleanup"
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / f"repository_safe_cleanup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    report = CleanupReport(
        version=_current_version(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_root=str(project_root),
        applied=apply,
        candidates=candidates,
        removed=removed,
        gitignore_updates=gitignore_updates,
        warnings=warnings,
        skipped_locked=skipped_locked,
        report_path=str(out),
    )
    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="AthenaEngine repository safe cleanup.")
    parser.add_argument("--apply", action="store_true", help="Apply safe cleanup actions.")
    args = parser.parse_args()
    report = run_cleanup(apply=args.apply)
    print("Repository Safe Cleanup")
    print("=" * 64)
    print(f"Version: {report.version}")
    print(f"Applied: {report.applied}")
    print(f"Candidates: {len(report.candidates)}")
    print(f"Removed: {len(report.removed)}")
    print(f"Review only: {sum(c.classification == 'review' for c in report.candidates)}")
    print(f"Gitignore updates: {len(report.gitignore_updates)}")
    print(f"Skipped locked: {len(report.skipped_locked)}")
    if report.skipped_locked:
        for item in report.skipped_locked[:10]:
            print(f"[WARN] skipped locked: {item}")
    print("Overall status: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
