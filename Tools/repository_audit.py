"""Repository Audit Foundation for AthenaEngine.

This module performs read-only repository hygiene and release-readiness audits.
It deliberately does not mutate files. Cleanup belongs to a later phase after
findings are reviewed.
"""
from __future__ import annotations

import ast
import json
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

AUDIT_VERSION = "0.5.6.2.0"
ROOT_MARKERS = ("Core/version.py", "Scout/app.py", "Tools/athena_studio.py")
IGNORED_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", "env", "build", "dist",
}
ARCHIVE_DIRS = {"Archive"}
RUNTIME_PATTERNS = ("diagnostics_export_", "execution_trace_doctor_tmp", "__pycache__")
TOP_LEVEL_ALLOWED_DUPLICATE_PACKAGES = {"Athena"}
SHIM_IMPORT_RE = re.compile(r"^\s*from\s+Athena\.[\w.]+\s+import\s+\*\s*$", re.M)


@dataclass
class AuditFinding:
    area: str
    severity: str
    title: str
    detail: str
    path: str = ""
    recommendation: str = ""


@dataclass
class RepositoryAuditReport:
    version: str
    created_at: str
    project_root: str
    status: str
    summary: dict[str, int]
    findings: list[AuditFinding] = field(default_factory=list)
    sections: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["findings"] = [asdict(f) for f in self.findings]
        return data


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_files(root: Path, include_archive: bool = True) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_parts = set(current.relative_to(root).parts) if current != root else set()
        dirnames[:] = [
            d for d in dirnames
            if d not in IGNORED_DIRS and (include_archive or d not in ARCHIVE_DIRS)
        ]
        if any(part in IGNORED_DIRS for part in rel_parts):
            continue
        for name in filenames:
            yield current / name


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    nums = []
    for part in value.split(".")[:5]:
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    while len(nums) < 5:
        nums.append(0)
    return tuple(nums)  # type: ignore[return-value]


def _severity_rank(severity: str) -> int:
    return {"fail": 3, "warn": 2, "info": 1, "pass": 0}.get(severity, 1)


def _status_from_findings(findings: list[AuditFinding]) -> str:
    if any(f.severity == "fail" for f in findings):
        return "fail"
    if any(f.severity == "warn" for f in findings):
        return "warn"
    return "pass"


def _count_summary(findings: list[AuditFinding]) -> dict[str, int]:
    summary = {"fail": 0, "warn": 0, "info": 0, "pass": 0, "total": len(findings)}
    for finding in findings:
        summary[finding.severity] = summary.get(finding.severity, 0) + 1
    return summary


def _package_roots(root: Path) -> list[str]:
    roots: list[str] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "__init__.py").exists():
            roots.append(child.name)
    return roots


def _python_module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def audit_repository(project_root: Path | str | None = None) -> RepositoryAuditReport:
    root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
    findings: list[AuditFinding] = []
    sections: dict[str, object] = {}

    marker_results = {marker: (root / marker).exists() for marker in ROOT_MARKERS}
    sections["root_markers"] = marker_results
    for marker, ok in marker_results.items():
        if not ok:
            findings.append(AuditFinding(
                area="root", severity="fail", title="Canonical root marker missing",
                detail=f"Required canonical file is missing: {marker}", path=marker,
                recommendation="Confirm the audit is running from F:/Development/AthenaEngine and restore the missing canonical file.",
            ))

    # Nested duplicate repository/package detection.
    nested_candidates = []
    for path in root.rglob("AthenaEngine"):
        if path == root:
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        nested_candidates.append(_rel(root, path))
    athena_core_duplicates = []
    for path in root.rglob("Athena"):
        if not path.is_dir() or path == root / "Athena":
            continue
        if (path / "Core").exists() or (path / "Scout").exists() or (path / "Athena").exists():
            athena_core_duplicates.append(_rel(root, path))
    sections["duplicate_repository_structures"] = {
        "nested_athenaengine_dirs": nested_candidates,
        "nested_athena_runtime_duplicates": athena_core_duplicates,
    }
    for item in nested_candidates:
        findings.append(AuditFinding(
            area="duplicates", severity="fail", title="Nested AthenaEngine directory found",
            detail="A nested repository copy can confuse imports, validators, and patch extraction.", path=item,
            recommendation="Move or delete nested repository copies during Phase 4 cleanup.",
        ))
    for item in athena_core_duplicates:
        findings.append(AuditFinding(
            area="duplicates", severity="fail", title="Nested Athena runtime duplicate found",
            detail="Nested Athena/Core, Athena/Scout, or Athena/Athena structures are not allowed.", path=item,
            recommendation="Quarantine or remove nested runtime duplicates during Phase 4 cleanup.",
        ))

    package_roots = _package_roots(root)
    sections["package_roots"] = package_roots

    # Duplicate filename inventory: warn only when outside known normal package pattern.
    module_name_map: dict[str, list[str]] = defaultdict(list)
    py_files = [p for p in _iter_files(root) if p.suffix == ".py"]
    for py in py_files:
        module_name_map[py.name].append(_rel(root, py))
    duplicate_basename = {name: paths for name, paths in module_name_map.items() if len(paths) > 1}
    sections["duplicate_module_basenames"] = duplicate_basename
    high_signal_dupes = {
        name: paths for name, paths in duplicate_basename.items()
        if name not in {"__init__.py", "models.py", "registry.py"}
    }
    if high_signal_dupes:
        findings.append(AuditFinding(
            area="duplicates", severity="warn", title="Duplicate Python basenames require review",
            detail=f"{len(high_signal_dupes)} non-standard duplicate module basename group(s) found.",
            recommendation="Confirm these are intentional domain-local modules or rename ambiguous files in Phase 4.",
        ))

    # Shim modules: top-level files that re-export package implementation.
    shim_files: list[str] = []
    for py in root.glob("*.py"):
        text = _read_text(py)
        if SHIM_IMPORT_RE.search(text) or "Compatibility shim" in text:
            shim_files.append(_rel(root, py))
    sections["shim_modules"] = shim_files
    if shim_files:
        findings.append(AuditFinding(
            area="shims", severity="warn", title="Root-level shim modules present",
            detail=f"{len(shim_files)} root shim module(s) found.",
            recommendation="Keep only documented compatibility shims; archive or remove stale shims in Phase 4.",
        ))

    # Obsolete manifests and root clutter.
    root_docs = [
        _rel(root, p) for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml"}
        and p.name.lower() not in {"readme.md", "pyproject.toml", "requirements.txt", "setup.cfg"}
    ]
    sections["root_document_inventory"] = root_docs
    if len(root_docs) > 12:
        findings.append(AuditFinding(
            area="hygiene", severity="warn", title="Root documentation/config clutter",
            detail=f"{len(root_docs)} root-level documentation/config artifacts found.",
            recommendation="Move historical manifests and notes into Archive/Documentation during Phase 4.",
        ))

    # Runtime/export artifacts in repository tree.
    runtime_artifacts: list[str] = []
    for p in _iter_files(root):
        rel = _rel(root, p)
        if any(pattern in rel for pattern in RUNTIME_PATTERNS) or rel.endswith((".pyc", ".pyo")):
            runtime_artifacts.append(rel)
    sections["runtime_artifacts"] = runtime_artifacts[:200]
    if runtime_artifacts:
        findings.append(AuditFinding(
            area="runtime_state", severity="warn", title="Runtime artifacts present in repository tree",
            detail=f"{len(runtime_artifacts)} runtime artifact(s) detected.",
            recommendation="Remove generated runtime/export artifacts or gitignore them during Phase 4.",
        ))

    # Empty directories excluding git internals.
    empty_dirs: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if any(part in IGNORED_DIRS for part in current.relative_to(root).parts if current != root):
            continue
        visible = [d for d in dirnames if d not in IGNORED_DIRS]
        if not visible and not filenames and current != root:
            empty_dirs.append(_rel(root, current))
    sections["empty_directories"] = empty_dirs[:200]
    if empty_dirs:
        findings.append(AuditFinding(
            area="hygiene", severity="info", title="Empty directories detected",
            detail=f"{len(empty_dirs)} empty directorie(s) found.",
            recommendation="Remove empty non-semantic directories during cleanup if they are not placeholders.",
        ))

    # Import correctness: parse all project Python files and identify syntax/import-shape issues.
    syntax_errors: list[dict[str, str]] = []
    import_edges: dict[str, list[str]] = defaultdict(list)
    for py in py_files:
        rel = _rel(root, py)
        text = _read_text(py)
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            syntax_errors.append({"path": rel, "error": str(exc)})
            continue
        module = _python_module_name(root, py)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    if name in package_roots or name in {"Core", "Knowledge", "Reasoning", "Scout", "Tools", "Tests", "Engine", "Intelligence", "Providers", "Sports"}:
                        import_edges[module].append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                base = node.module.split(".")[0]
                if base in package_roots or base in {"Core", "Knowledge", "Reasoning", "Scout", "Tools", "Tests", "Engine", "Intelligence", "Providers", "Sports"}:
                    import_edges[module].append(node.module)
    sections["syntax_errors"] = syntax_errors
    sections["dependency_graph_summary"] = {
        "python_files": len(py_files),
        "modules_with_internal_imports": len(import_edges),
        "internal_import_edges": sum(len(v) for v in import_edges.values()),
    }
    if syntax_errors:
        findings.append(AuditFinding(
            area="imports", severity="fail", title="Python syntax errors detected",
            detail=f"{len(syntax_errors)} Python file(s) failed AST parsing.",
            recommendation="Fix syntax errors before repository cleanup or release-candidate work.",
        ))

    # Packaging / CI readiness.
    packaging = {
        "pyproject.toml": (root / "pyproject.toml").exists(),
        "requirements.txt": (root / "requirements.txt").exists(),
        "setup.cfg": (root / "setup.cfg").exists(),
        ".github/workflows": (root / ".github" / "workflows").exists(),
        "pytest_config": any((root / name).exists() for name in ("pytest.ini", "pyproject.toml", "setup.cfg")),
    }
    sections["packaging_ci_readiness"] = packaging
    if not packaging["pyproject.toml"] and not packaging["requirements.txt"]:
        findings.append(AuditFinding(
            area="packaging", severity="warn", title="Dependency manifest missing",
            detail="No pyproject.toml or requirements.txt found at repository root.",
            recommendation="Add a minimal dependency manifest before Version 1 release candidate.",
        ))
    if not packaging[".github/workflows"]:
        findings.append(AuditFinding(
            area="ci", severity="warn", title="CI workflow missing",
            detail="No .github/workflows directory found.",
            recommendation="Add CI for doctors/validators before Version 1 release candidate.",
        ))

    # Version metadata sanity.
    version_data: dict[str, str] = {}
    version_file = root / "Core" / "version.py"
    if version_file.exists():
        tree = ast.parse(_read_text(version_file))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {"ATHENA_VERSION", "SCOUT_VERSION", "ATHENA_BUILD", "RELEASE_NAME", "VERSION_SCHEMA"}:
                        if isinstance(node.value, ast.Constant):
                            version_data[target.id] = str(node.value.value)
    sections["version_metadata"] = version_data
    current_version = version_data.get("ATHENA_VERSION", "0.0.0.0.0")
    if _version_tuple(current_version) < _version_tuple("0.5.6.2.0"):
        findings.append(AuditFinding(
            area="version", severity="warn", title="Audit build version not yet advanced",
            detail=f"Current ATHENA_VERSION is {current_version}; Phase 3 audit target is {AUDIT_VERSION}.",
            recommendation="Apply the Phase 3 audit patch version bump before locking this build.",
        ))

    # Release readiness derived summary.
    release_blockers = [f for f in findings if f.severity == "fail"]
    release_warnings = [f for f in findings if f.severity == "warn"]
    sections["version_1_release_readiness"] = {
        "ready_for_release_candidate": not release_blockers and len(release_warnings) == 0,
        "blocker_count": len(release_blockers),
        "warning_count": len(release_warnings),
        "next_phase": "Phase 4 Repository Cleanup" if findings else "Phase 5 Release Candidate Prep",
    }

    findings.sort(key=lambda f: (_severity_rank(f.severity), f.area, f.title), reverse=True)
    status = _status_from_findings(findings)
    return RepositoryAuditReport(
        version=AUDIT_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(),
        project_root=str(root),
        status=status,
        summary=_count_summary(findings),
        findings=findings,
        sections=sections,
    )


def write_repository_audit_report(project_root: Path | str | None = None, reports_dir: Path | str | None = None) -> Path:
    root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
    report = audit_repository(root)
    reports = Path(reports_dir or root / "Reports" / "repository_audit")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = reports / f"repository_audit_{stamp}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    latest = reports / "repository_audit_latest.json"
    latest.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report_path = write_repository_audit_report(root)
    report = audit_repository(root)
    print("AthenaEngine Repository Audit")
    print("=" * 64)
    print(f"Version: {report.version}")
    print(f"Status: {report.status.upper()}")
    print(f"Report: {report_path}")
    print(f"Findings: total={report.summary['total']} fail={report.summary['fail']} warn={report.summary['warn']} info={report.summary['info']}")
    for finding in report.findings[:20]:
        print(f"[{finding.severity.upper()}] {finding.area}: {finding.title}" + (f" — {finding.detail}" if finding.detail else ""))
        if finding.path:
            print(f"       path: {finding.path}")
        if finding.recommendation:
            print(f"       next: {finding.recommendation}")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
