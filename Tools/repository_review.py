"""Shim and duplicate basename review tooling for AthenaEngine.

This module is intentionally read-only. It inventories root-level compatibility
shims and duplicate Python basenames, classifies them for later cleanup review,
and writes machine-readable JSON plus human-readable Markdown reports.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPOSITORY_REVIEW_VERSION = "0.5.6.2.4"
IGNORED_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", "env", "build", "dist",
}
ARCHIVE_DIRS = {"Archive"}
NORMAL_DUPLICATE_BASENAMES = {"__init__.py", "models.py", "registry.py"}
ROOT_SHIM_RE = re.compile(r"^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+\*\s*$", re.M)


@dataclass(frozen=True)
class ShimReviewItem:
    path: str
    target_module: str
    import_type: str
    last_modified: str
    purpose: str
    referenced_by: list[str]
    classification: str
    rationale: str


@dataclass(frozen=True)
class DuplicateBasenameItem:
    basename: str
    locations: list[str]
    package_owners: list[str]
    likely_purpose: str
    classification: str
    rationale: str


@dataclass(frozen=True)
class RepositoryReviewReport:
    version: str
    generated_at: str
    project_root: str
    status: str
    summary: dict[str, object]
    shims: list[ShimReviewItem] = field(default_factory=list)
    duplicates: list[DuplicateBasenameItem] = field(default_factory=list)
    report_paths: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["shims"] = [asdict(item) for item in self.shims]
        payload["duplicates"] = [asdict(item) for item in self.duplicates]
        return payload


def project_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _iter_python_files(root: Path, include_archive: bool = True) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_parts = current.relative_to(root).parts if current != root else ()
        dirnames[:] = [
            name for name in dirnames
            if name not in IGNORED_DIRS and (include_archive or name not in ARCHIVE_DIRS)
        ]
        if any(part in IGNORED_DIRS for part in rel_parts):
            continue
        if not include_archive and any(part in ARCHIVE_DIRS for part in rel_parts):
            continue
        for filename in filenames:
            if filename.endswith(".py"):
                yield current / filename


def _module_name_for_path(root: Path, path: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def _package_owner(root: Path, path: Path) -> str:
    rel = path.relative_to(root).parts
    if not rel:
        return "root"
    return rel[0]


def _target_from_root_shim(path: Path) -> tuple[str, str]:
    text = _read_text(path)
    match = ROOT_SHIM_RE.search(text)
    if match:
        return match.group(1), "star re-export"
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return "", "unparseable"
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return (targets[0] if targets else ""), "compatibility shim" if "shim" in text.lower() else "unknown"


def _is_root_shim(root: Path, path: Path) -> bool:
    if path.parent != root or path.name.startswith(".") or path.name == "__init__.py":
        return False
    text = _read_text(path)
    if "compatibility shim" in text.lower() or "shim" in text.lower():
        return True
    target, import_type = _target_from_root_shim(path)
    return bool(target and import_type in {"star re-export", "compatibility shim"})


def _files_referencing_module(root: Path, module_name: str, shim_basename: str) -> list[str]:
    references: list[str] = []
    import_patterns = (
        f"import {module_name}",
        f"from {module_name} import",
        f"import {shim_basename}",
        f"from {shim_basename} import",
    )
    for py in _iter_python_files(root, include_archive=False):
        if py.parent == root and py.stem == shim_basename:
            continue
        text = _read_text(py)
        if any(pattern in text for pattern in import_patterns):
            references.append(_rel(root, py))
    return sorted(set(references))


def _classify_shim(path: Path, target_module: str, referenced_by: list[str]) -> tuple[str, str, str]:
    name = path.name
    purpose = "Root-level compatibility import forwarding to canonical package implementation."
    if referenced_by:
        return "keep", purpose, "Still referenced by repository code; keep until callers are migrated."
    if target_module.startswith("Athena."):
        return "archive candidate", purpose, "No active internal references found; preserve for one cleanup cycle before removal."
    if target_module:
        return "archive candidate", purpose, "Target detected but no active internal references found."
    return "remove candidate", "Unclear root-level shim or compatibility artifact.", "No target module or active internal references detected."


def review_shims(root: Path) -> list[ShimReviewItem]:
    items: list[ShimReviewItem] = []
    for path in sorted(root.glob("*.py")):
        if not _is_root_shim(root, path):
            continue
        target_module, import_type = _target_from_root_shim(path)
        referenced_by = _files_referencing_module(root, target_module, path.stem)
        classification, purpose, rationale = _classify_shim(path, target_module, referenced_by)
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        items.append(ShimReviewItem(
            path=_rel(root, path),
            target_module=target_module or "unknown",
            import_type=import_type,
            last_modified=modified,
            purpose=purpose,
            referenced_by=referenced_by,
            classification=classification,
            rationale=rationale,
        ))
    return items


def _likely_duplicate_purpose(basename: str, locations: list[str]) -> str:
    if basename == "__init__.py":
        return "Package marker files."
    if basename in {"models.py", "registry.py"}:
        return "Common domain-local module name used inside multiple bounded packages."
    if basename.startswith("validate_"):
        return "Validator scripts with similar phase or feature naming."
    if basename.startswith("doctor_"):
        return "Doctor scripts with similar phase or feature naming."
    owners = {loc.split("/", 1)[0] for loc in locations}
    if len(owners) == 1:
        return "Duplicate basename contained within one top-level package or tool family."
    return "Same Python basename appears across multiple top-level package owners."


def _classify_duplicate(basename: str, locations: list[str], owners: list[str]) -> tuple[str, str]:
    if basename in NORMAL_DUPLICATE_BASENAMES:
        return "intentional domain-local", "Common Python/package convention; document but do not rename."
    if basename.startswith(("validate_", "doctor_")) and len(set(owners)) == 1:
        return "intentional domain-local", "Phase-specific tool/validator naming within one owner is acceptable."
    if len(set(owners)) == 1 and owners[0] in {"Tests", "Tools"}:
        return "cleanup candidate", "Same script basename repeats inside one operational area; review for stale superseded versions."
    if len(set(owners)) > 1:
        return "ambiguous", "Same basename crosses package boundaries; review import ambiguity before cleanup."
    return "cleanup candidate", "Non-standard duplicate basename should be reviewed for consolidation or rename."


def review_duplicate_basenames(root: Path) -> list[DuplicateBasenameItem]:
    basename_map: dict[str, list[str]] = defaultdict(list)
    for py in _iter_python_files(root, include_archive=True):
        basename_map[py.name].append(_rel(root, py))
    items: list[DuplicateBasenameItem] = []
    for basename, locations in sorted(basename_map.items()):
        if len(locations) <= 1:
            continue
        owners = sorted({_package_owner(root, root / loc) for loc in locations})
        classification, rationale = _classify_duplicate(basename, sorted(locations), owners)
        items.append(DuplicateBasenameItem(
            basename=basename,
            locations=sorted(locations),
            package_owners=owners,
            likely_purpose=_likely_duplicate_purpose(basename, sorted(locations)),
            classification=classification,
            rationale=rationale,
        ))
    return items


def _summary(shims: list[ShimReviewItem], duplicates: list[DuplicateBasenameItem]) -> dict[str, object]:
    shim_counts: dict[str, int] = defaultdict(int)
    duplicate_counts: dict[str, int] = defaultdict(int)
    non_standard = [item for item in duplicates if item.basename not in NORMAL_DUPLICATE_BASENAMES]
    for item in shims:
        shim_counts[item.classification] += 1
    for item in duplicates:
        duplicate_counts[item.classification] += 1
    return {
        "shim_count": len(shims),
        "duplicate_basename_group_count": len(duplicates),
        "non_standard_duplicate_basename_group_count": len(non_standard),
        "shim_classifications": dict(sorted(shim_counts.items())),
        "duplicate_classifications": dict(sorted(duplicate_counts.items())),
    }


def build_repository_review(project_root: Path | str | None = None) -> RepositoryReviewReport:
    root = Path(project_root or project_root_from_here()).resolve()
    shims = review_shims(root)
    duplicates = review_duplicate_basenames(root)
    return RepositoryReviewReport(
        version=REPOSITORY_REVIEW_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_root=str(root),
        status="pass",
        summary=_summary(shims, duplicates),
        shims=shims,
        duplicates=duplicates,
    )


def _markdown_table_row(values: list[object]) -> str:
    escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in values]
    return "| " + " | ".join(escaped) + " |"


def _render_shim_markdown(report: RepositoryReviewReport) -> str:
    lines = [
        "# AthenaEngine Shim Inventory Report",
        "",
        f"Version: {report.version}",
        f"Generated: {report.generated_at}",
        f"Status: {report.status.upper()}",
        "",
        "This report is read-only. It does not remove, rename, or rewrite files.",
        "",
        _markdown_table_row(["Path", "Target", "Import Type", "Classification", "References", "Rationale"]),
        _markdown_table_row(["---", "---", "---", "---", "---", "---"]),
    ]
    for item in report.shims:
        lines.append(_markdown_table_row([
            item.path,
            item.target_module,
            item.import_type,
            item.classification,
            len(item.referenced_by),
            item.rationale,
        ]))
    lines.append("")
    return "\n".join(lines)


def _render_duplicate_markdown(report: RepositoryReviewReport) -> str:
    lines = [
        "# AthenaEngine Duplicate Basename Classification Report",
        "",
        f"Version: {report.version}",
        f"Generated: {report.generated_at}",
        f"Status: {report.status.upper()}",
        "",
        "This report is read-only. It classifies duplicates for later decision locking.",
        "",
        _markdown_table_row(["Basename", "Owners", "Count", "Classification", "Likely Purpose", "Rationale"]),
        _markdown_table_row(["---", "---", "---", "---", "---", "---"]),
    ]
    for item in report.duplicates:
        lines.append(_markdown_table_row([
            item.basename,
            ", ".join(item.package_owners),
            len(item.locations),
            item.classification,
            item.likely_purpose,
            item.rationale,
        ]))
        for location in item.locations:
            lines.append(f"  - `{location}`")
    lines.append("")
    return "\n".join(lines)


def write_repository_review_reports(project_root: Path | str | None = None, reports_dir: Path | str | None = None) -> RepositoryReviewReport:
    root = Path(project_root or project_root_from_here()).resolve()
    report = build_repository_review(root)
    reports = Path(reports_dir or root / "Reports" / "repository_review")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    paths = {
        "combined_json": reports / f"repository_review_{stamp}.json",
        "combined_latest_json": reports / "repository_review_latest.json",
        "shim_json": reports / f"shim_inventory_{stamp}.json",
        "shim_latest_json": reports / "shim_inventory_latest.json",
        "shim_markdown": reports / f"shim_inventory_{stamp}.md",
        "shim_latest_markdown": reports / "shim_inventory_latest.md",
        "duplicate_json": reports / f"duplicate_basename_report_{stamp}.json",
        "duplicate_latest_json": reports / "duplicate_basename_report_latest.json",
        "duplicate_markdown": reports / f"duplicate_basename_report_{stamp}.md",
        "duplicate_latest_markdown": reports / "duplicate_basename_report_latest.md",
    }

    report_paths = {key: str(value) for key, value in paths.items()}
    report = RepositoryReviewReport(
        version=report.version,
        generated_at=report.generated_at,
        project_root=report.project_root,
        status=report.status,
        summary=report.summary,
        shims=report.shims,
        duplicates=report.duplicates,
        report_paths=report_paths,
    )
    combined = json.dumps(report.to_dict(), indent=2, sort_keys=True)
    shim_payload = json.dumps({"version": report.version, "generated_at": report.generated_at, "shims": [asdict(item) for item in report.shims]}, indent=2, sort_keys=True)
    duplicate_payload = json.dumps({"version": report.version, "generated_at": report.generated_at, "duplicates": [asdict(item) for item in report.duplicates]}, indent=2, sort_keys=True)
    for key in ("combined_json", "combined_latest_json"):
        paths[key].write_text(combined, encoding="utf-8")
    for key in ("shim_json", "shim_latest_json"):
        paths[key].write_text(shim_payload, encoding="utf-8")
    for key in ("duplicate_json", "duplicate_latest_json"):
        paths[key].write_text(duplicate_payload, encoding="utf-8")
    shim_md = _render_shim_markdown(report)
    duplicate_md = _render_duplicate_markdown(report)
    for key in ("shim_markdown", "shim_latest_markdown"):
        paths[key].write_text(shim_md, encoding="utf-8")
    for key in ("duplicate_markdown", "duplicate_latest_markdown"):
        paths[key].write_text(duplicate_md, encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AthenaEngine shim and duplicate basename review.")
    parser.add_argument("--root", default=None, help="Project root. Defaults to repository root inferred from this script.")
    args = parser.parse_args()
    report = write_repository_review_reports(Path(args.root).resolve() if args.root else None)
    print("AthenaEngine Shim & Duplicate Review")
    print("=" * 64)
    print(f"Version: {report.version}")
    print(f"Status: {report.status.upper()}")
    print(f"Shim count: {report.summary.get('shim_count')}")
    print(f"Duplicate basename groups: {report.summary.get('duplicate_basename_group_count')} total / {report.summary.get('non_standard_duplicate_basename_group_count')} non-standard")
    print("Shim classifications:", report.summary.get("shim_classifications"))
    print("Duplicate classifications:", report.summary.get("duplicate_classifications"))
    print(f"Report: {report.report_paths.get('combined_json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
