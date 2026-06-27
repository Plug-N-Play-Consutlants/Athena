"""AthenaEngine repository governance audit and cleanup planner.

Studio-facing authority for noisy repository cleanup. This module classifies the
repository surface, identifies duplicate/consolidation candidates, detects stale
version drift, and produces cleanup recommendations without deleting source.
Apply mode is intentionally limited to reproducible cache/bytecode artifacts.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import shutil
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

GOVERNANCE_VERSION = "0.5.3.1.8-cleanup-approval-architecture-queue"
ACTIVE_ROOTS = {
    "Athena",
    "Configuration",
    "Core",
    "Diagnostics",
    "Engine",
    "Intelligence",
    "Knowledge",
    "Providers",
    "Reasoning",
    "Scout",
    "Sports",
    "Tests",
    "Tools",
}
GENERATED_ROOTS = {"Logs", "Output", "Raw"}
REPORT_ROOTS = {"Reports"}
IGNORED_ROOTS = {".git", ".hg", ".svn", ".idea", ".vscode"}
ARCHIVE_ROOTS = {"Archive"}
SAFE_DELETE_NAMES = {".pytest_cache", ".mypy_cache", ".ruff_cache"}
ENTRYPOINT_NAMES = {
    "launch.py",
    "build_engine.py",
    "Athena Studio.bat",
    "Athena Studio.ps1",
    "Scout.bat",
    "Clean Athena Runtime.bat",
    "Clean Acceptance Pathway Residue.bat",
}
VERSION_PATTERN = re.compile(r"v?(?<!\d)(\d+\.\d+\.\d+(?:\.\d+){0,2}(?:[-_][A-Za-z0-9_.-]+)?)(?!\d)")

RELEASE_VERSION_NAMES = {"ATHENA_VERSION", "ATHENA_BUILD", "SCOUT_VERSION", "VERSION"}
COMPONENT_VERSION_SUFFIXES = ("_VERSION", "_BUILD")
SCHEMA_VERSION_NAMES = {"SCHEMA_VERSION"}
GENERATOR_VERSION_NAMES = {"GENERATOR_VERSION"}
INTERNAL_VERSION_NAMES = {"ENGINE_VERSION"}
FUNCTION_BODY_MIN_NODES = 4
FUNCTION_BODY_MIN_SOURCE_CHARS = 80
ARCHITECTURE_DOMAINS = {
    "Athena": "runtime_api",
    "Configuration": "configuration",
    "Core": "core",
    "Diagnostics": "diagnostics",
    "Engine": "engine",
    "Intelligence": "intelligence",
    "Knowledge": "knowledge",
    "Providers": "providers",
    "Reasoning": "reasoning",
    "Scout": "scout_ui",
    "Sports": "sports_registry",
    "Tests": "tests",
    "Tools": "tools",
    "Archive": "archive",
}


@dataclass(frozen=True)
class FileDecision:
    path: str
    classification: str
    role: str
    reason: str
    size: int
    extension: str
    module: str = ""
    imported_by: int | str = ""
    sha1: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def module_name(root: Path, path: Path) -> str:
    rp = path.relative_to(root)
    parts = list(rp.parts)
    if parts[-1] == "__init__.py":
        return ".".join(parts[:-1])
    return ".".join(parts)[:-3]


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 128), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_python(path: Path) -> ast.AST | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            return ast.parse(safe_read(path))
    except SyntaxError:
        return None


def build_import_graph(root: Path, py_files: list[Path]) -> tuple[dict[str, set[str]], dict[str, Path], list[dict[str, str]]]:
    file_by_module = {module_name(root, path): path for path in py_files}
    imports: dict[str, set[str]] = defaultdict(set)
    parse_errors: list[dict[str, str]] = []

    for path in py_files:
        module = module_name(root, path)
        tree = parse_python(path)
        if tree is None:
            parse_errors.append({"path": rel(root, path), "error": "SyntaxError or parse failure"})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[module].add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.level == 0:
                    imports[module].add(node.module)
                else:
                    base = module.split(".")[:-node.level]
                    imports[module].add(".".join(base + [node.module]))

    internal_refs: dict[str, set[str]] = defaultdict(set)
    modules = set(file_by_module)
    for source_module, imported_modules in imports.items():
        for imported in imported_modules:
            for target in modules:
                if imported == target or imported.startswith(target + ".") or target.startswith(imported + "."):
                    if target != source_module:
                        internal_refs[target].add(source_module)
    return internal_refs, file_by_module, parse_errors


def role_for(path_text: str, path: Path) -> str:
    top = path_text.split("/", 1)[0]
    name = path.name
    if top == "Tools":
        if name.startswith("doctor_"):
            return "DOCTOR"
        if name.startswith("validate_"):
            return "VALIDATOR_TOOL"
        if name.startswith("audit_") or name == "repository_governance.py":
            return "GOVERNANCE_TOOL"
        if name.startswith("cleanup_"):
            return "CLEANUP_TOOL"
        return "TOOL"
    if top == "Tests":
        return "TEST"
    if top in GENERATED_ROOTS:
        return "GENERATED_RUNTIME_DATA"
    if top in REPORT_ROOTS:
        return "GENERATED_REPORT"
    if top in ARCHIVE_ROOTS:
        return "ARCHIVED_HISTORY"
    if name.startswith("CHANGE_MANIFEST_") or name.startswith("RELEASE_NOTES_") or name.startswith("RELEASE_MANIFEST_"):
        return "VERSION_HISTORY"
    if name.lower().endswith((".md", ".txt")):
        return "DOCUMENTATION"
    if top in ACTIVE_ROOTS:
        return top.upper()
    if path.suffix.lower() in {".bat", ".ps1"}:
        return "ENTRYPOINT"
    return "ROOT_OR_MISC"


def classify_file(root: Path, path: Path, internal_refs: dict[str, set[str]]) -> FileDecision:
    path_text = rel(root, path)
    parts = path_text.split("/")
    top = parts[0]
    ext = path.suffix.lower() or "[none]"
    module = module_name(root, path) if ext == ".py" else ""
    imported_by: int | str = len(internal_refs.get(module, set())) if module else ""
    role = role_for(path_text, path)

    classification = "MANUAL_REVIEW_REQUIRED"
    reason = "No automated cleanup decision; review manually."

    if "__pycache__" in parts or ext == ".pyc" or any(part in SAFE_DELETE_NAMES for part in parts):
        classification = "DELETE_SAFE"
        reason = "Reproducible Python/cache artifact."
    elif top in ARCHIVE_ROOTS:
        classification = "KEEP_ARCHIVED"
        reason = "Already out of the active engineering surface."
    elif top in GENERATED_ROOTS:
        classification = "RUNTIME_DATA_REVIEW"
        reason = "Generated logs/output/raw data; preserve useful diagnostics, archive older noise."
    elif top in REPORT_ROOTS:
        classification = "GENERATED_REPORT_REVIEW"
        reason = "Generated report output; excluded from normal governance totals unless report inventory is requested."
    elif path.name in ENTRYPOINT_NAMES:
        classification = "KEEP_ENTRYPOINT"
        reason = "User-facing launcher or workflow entrypoint."
    elif top in {"Core", "Knowledge", "Engine", "Intelligence", "Reasoning", "Providers", "Scout", "Sports", "Athena", "Configuration", "Diagnostics"}:
        if ext == ".py" and imported_by == 0 and path.name != "__init__.py":
            classification = "DYNAMIC_IMPORT_REVIEW"
            reason = "Active-source area but not statically imported; may be dynamic, entrypoint, or obsolete."
        else:
            classification = "KEEP_ACTIVE"
            reason = "Active subsystem source/configuration."
    elif top == "Tests":
        classification = "KEEP_TEST"
        reason = "Regression, acceptance, or smoke validation."
    elif top == "Tools":
        if path.name == "repository_governance.py" or path.name == "audit_file_usefulness.py":
            classification = "KEEP_ACTIVE"
            reason = "Repository governance/audit utility currently surfaced in Studio."
        elif path.name.startswith(("doctor_", "validate_")):
            classification = "LEGACY_TOOL_REVIEW"
            reason = "Doctor/validator script; preserve behavior but route through common Studio workflows where possible."
        elif path.name.startswith(("cleanup_", "patch_")):
            classification = "LEGACY_TOOL_REVIEW"
            reason = "Historical cleanup/patch tool; confirm current use before archive or consolidation."
        elif path.name.startswith("audit_"):
            classification = "CONSOLIDATE_CANDIDATE"
            reason = "Audit utility; consider consolidating under repository governance/reporting."
        elif ext == ".py" and imported_by == 0:
            classification = "UNREFERENCED_SOURCE_REVIEW"
            reason = "Tooling script not statically imported; verify whether Studio, docs, or manual workflow still calls it."
        else:
            classification = "CONSOLIDATE_CANDIDATE"
            reason = "Tooling script; consider common routing through Studio."
    elif path.name.startswith("CHANGE_MANIFEST_"):
        classification = "ROOT_DOC_REVIEW"
        reason = "Root-level historical manifest; archive after confirming release history is preserved."
    elif path.name.startswith("README_") or path.name.startswith("RELEASE_"):
        classification = "ROOT_DOC_REVIEW"
        reason = "Root-level historical/version documentation; archive after confirming current docs remain visible."
    elif ext in {".md", ".txt"}:
        classification = "ROOT_DOC_REVIEW"
        reason = "Documentation; determine whether current, historical, or redundant."
    elif ext == ".py" and imported_by == 0:
        classification = "UNREFERENCED_SOURCE_REVIEW"
        reason = "Python source not statically imported by active repository modules."

    digest = ""
    if path.stat().st_size <= 2_000_000:
        try:
            digest = sha1_file(path)
        except Exception:
            digest = ""
    return FileDecision(path_text, classification, role, reason, path.stat().st_size, ext, module, imported_by, digest)


def detect_duplicate_content(rows: list[FileDecision]) -> dict[str, list[str]]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.sha1:
            by_hash[row.sha1].append(row.path)
    return {digest: paths for digest, paths in by_hash.items() if len(paths) > 1}


NOISE_FUNCTION_NAMES = {
    "__init__", "__post_init__", "main", "to_dict", "from_dict", "as_dict",
    "check", "validate", "report", "result", "ok", "fail", "warn", "emit",
    "print", "print_summary", "read_text", "write_csv", "write_outputs",
    "_safe_str", "safe_str", "_safe_int", "safe_int", "_safe_float",
    "_version_tuple", "_version_at_least", "_version_value", "_utc_now",
    "utc_now_iso", "_read_json", "_write_csv", "_assert", "_check",
}


def _function_body_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    clone = ast.FunctionDef(
        name="<fn>",
        args=node.args,
        body=node.body,
        decorator_list=[],
        returns=node.returns,
        type_comment=getattr(node, "type_comment", None),
    )
    return hashlib.sha1(ast.dump(clone, include_attributes=False).encode("utf-8")).hexdigest()


def _function_source_size(path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    try:
        lines = safe_read(path).splitlines()
        end = getattr(node, "end_lineno", node.lineno)
        return len("\n".join(lines[node.lineno - 1:end]))
    except Exception:
        return 0


def _node_count(node: ast.AST) -> int:
    return sum(1 for _ in ast.walk(node))


def detect_duplicate_function_names(root: Path, py_files: Iterable[Path]) -> dict[str, list[str]]:
    """Return probable duplicate implementations, not ordinary shared API names.

    Earlier governance versions reported duplicate identifiers. That created noise
    because methods such as build(), connect(), fetch(), get(), or __init__() are
    valid common protocol names across Athena subsystems. This pass only reports
    duplicate function *bodies* and preserves the legacy key for compatibility.
    """
    by_body: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in py_files:
        if "Archive" in path.parts:
            continue
        tree = parse_python(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name in NOISE_FUNCTION_NAMES:
                continue
            source_size = _function_source_size(path, node)
            if source_size < FUNCTION_BODY_MIN_SOURCE_CHARS or _node_count(node) < FUNCTION_BODY_MIN_NODES:
                continue
            signature = _function_body_signature(node)
            by_body[signature].append({
                "name": node.name,
                "location": f"{rel(root, path)}:{node.lineno}",
                "file": rel(root, path),
                "source_chars": source_size,
            })

    result: dict[str, list[str]] = {}
    for signature, entries in by_body.items():
        files = {str(entry["file"]) for entry in entries}
        names = {str(entry["name"]) for entry in entries}
        if len(files) <= 1:
            continue
        key_name = sorted(names)[0] if len(names) == 1 else "multiple_names"
        key = f"{key_name}::{signature[:12]}"
        result[key] = [str(entry["location"]) for entry in entries[:50]]
    return dict(sorted(result.items(), key=lambda item: (-len(item[1]), item[0]))[:100])


def detect_duplicate_function_bodies(root: Path, py_files: Iterable[Path]) -> list[dict[str, object]]:
    groups = detect_duplicate_function_names(root, py_files)
    body_groups = []
    for key, locations in groups.items():
        files = sorted({loc.split(":", 1)[0] for loc in locations})
        names = sorted({key.split("::", 1)[0]})
        body_groups.append({"signature": key.split("::", 1)[-1], "function_names": names, "count": len(locations), "file_count": len(files), "files": files, "locations": locations})
    return body_groups


def detect_studio_tool_families(root: Path) -> dict[str, list[str]]:
    tools = root / "Tools"
    tests = root / "Tests"
    families: dict[str, list[str]] = defaultdict(list)
    patterns = [
        (tools, re.compile(r"^(doctor_athena_studio|doctor_studio).+\.py$"), "studio_doctors"),
        (tests, re.compile(r"^(validate_athena_studio|validate_studio).+\.py$"), "studio_validators"),
        (tools, re.compile(r"^doctor_.+\.py$"), "doctor_scripts"),
        (tests, re.compile(r"^validate_.+\.py$"), "validator_scripts"),
        (tools, re.compile(r"^(cleanup_|patch_).+\.py$"), "cleanup_patch_scripts"),
        (tools, re.compile(r"^audit_.+\.py$"), "audit_scripts"),
    ]
    for folder, regex, family in patterns:
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.py")):
            if regex.match(path.name):
                families[family].append(rel(root, path))
    return dict(families)


def build_cleanup_plan(rows: list[FileDecision]) -> dict[str, list[str]]:
    plan: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        plan[row.classification].append(row.path)
    return {key: sorted(value) for key, value in sorted(plan.items())}


def cleanup_action_category(action: str) -> str:
    if action.startswith("delete_dir:") or action.startswith("delete_file:"):
        return "delete_safe"
    if "->Archive/Documentation/ChangeManifests/" in action:
        return "archive_change_manifests"
    if "->Archive/Documentation/ReleaseNotes/" in action:
        return "archive_release_notes"
    if "->Archive/Documentation/LegacyReadme/" in action:
        return "archive_legacy_readmes"
    if "->Archive/Documentation/RootHistory/" in action:
        return "archive_root_history_other"
    if action.startswith("move:"):
        return "move_other"
    return "other"


def cleanup_action_summary(actions: list[str]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for action in actions:
        counts[cleanup_action_category(action)] += 1
    return dict(sorted(counts.items()))


def classify_review_queue_item(row: dict[str, object]) -> str:
    path = str(row.get("path", ""))
    name = path.rsplit("/", 1)[-1]
    classification = str(row.get("classification", ""))
    imported_by = row.get("imported_by", "")
    size = int(row.get("size", 0) or 0)
    if name == "__init__.py":
        return "PACKAGE_MARKER"
    if classification == "ROOT_DOC_REVIEW":
        if name.startswith("CHANGE_MANIFEST_"):
            return "ROOT_HISTORY_CHANGE_MANIFEST"
        if name.startswith("RELEASE_") or name.startswith("RELEASE_NOTES_"):
            return "ROOT_HISTORY_RELEASE_NOTE"
        if name.startswith("README_"):
            return "ROOT_HISTORY_LEGACY_README"
        return "ROOT_DOCUMENT_REVIEW"
    if classification == "DYNAMIC_IMPORT_REVIEW":
        if "/fetch/" in path or "/build/" in path or "/auth/" in path:
            return "KNOWN_DYNAMIC_OR_PROVIDER_ENTRYPOINT"
        if path.startswith("Knowledge/Packs/") or path.startswith("Configuration/"):
            return "DATA_OR_CONFIGURATION_ENTRYPOINT"
        if size <= 100:
            return "STUB_OR_PLACEHOLDER"
        return "DYNAMIC_IMPORT_REVIEW"
    if classification == "LEGACY_TOOL_REVIEW":
        if name.startswith("doctor_"):
            return "LEGACY_DOCTOR_SCRIPT"
        if name.startswith("validate_"):
            return "LEGACY_VALIDATOR_SCRIPT"
        if name.startswith(("cleanup_", "patch_")):
            return "LEGACY_CLEANUP_OR_PATCH_SCRIPT"
        return "LEGACY_TOOL_REVIEW"
    if classification == "UNREFERENCED_SOURCE_REVIEW":
        return "UNREFERENCED_SOURCE_REVIEW"
    if classification == "CONSOLIDATE_CANDIDATE":
        return "CONSOLIDATE_CANDIDATE"
    if classification == "RUNTIME_DATA_REVIEW":
        return "RUNTIME_DATA_REVIEW"
    if imported_by == 0 and str(row.get("extension")) == ".py":
        return "ZERO_STATIC_IMPORT_REVIEW"
    return "GENERAL_REVIEW"


def build_architecture_review_queue(audit: dict[str, object]) -> dict[str, object]:
    rows = audit.get("rows", [])
    queue: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    for row in rows:  # type: ignore[assignment]
        classification = row.get("classification", "")
        if not (str(classification).endswith("REVIEW") or classification in {"CONSOLIDATE_CANDIDATE", "LEGACY_TOOL_REVIEW", "MANUAL_REVIEW_REQUIRED"}):
            continue
        category = classify_review_queue_item(row)
        counts[category] += 1
        queue.append({
            "path": row.get("path"),
            "category": category,
            "classification": classification,
            "role": row.get("role"),
            "reason": row.get("reason"),
            "imported_by": row.get("imported_by"),
            "size": row.get("size"),
        })
    queue.sort(key=lambda item: (str(item["category"]), str(item["path"])))
    return {
        "version": audit["version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": audit["root"],
        "total_review_items": len(queue),
        "category_counts": dict(sorted(counts.items())),
        "items": queue,
        "guardrail": "This queue is diagnostic only. It does not authorize deletion or movement of source files.",
    }


def extract_version_constants(path: Path, root: Path) -> list[dict[str, str]]:
    if path.suffix.lower() != ".py":
        return []
    try:
        tree = parse_python(path)
    except Exception:
        tree = None
    if tree is None:
        return []
    found: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and "VERSION" in target.id.upper():
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str) and VERSION_PATTERN.search(value.value):
                        found.append({"path": rel(root, path), "name": target.id, "value": value.value})
    return found


def normalized_version(value: str) -> str:
    return value[1:] if value.startswith("v") and len(value) > 1 and value[1].isdigit() else value


def version_constant_category(item: dict[str, str]) -> str:
    name = item["name"].upper()
    path = item["path"].replace("\\", "/")
    if name in SCHEMA_VERSION_NAMES:
        return "schema_version"
    if name in GENERATOR_VERSION_NAMES:
        return "generator_version"
    if name in INTERNAL_VERSION_NAMES:
        return "internal_engine_version"
    if name in RELEASE_VERSION_NAMES and path in {"Core/version.py", "Intelligence/Core/version.py"}:
        return "release_version"
    if name in {"SCOUT_VERSION"}:
        return "release_version"
    if name.endswith(COMPONENT_VERSION_SUFFIXES):
        return "component_version"
    return "other_version"


def detect_version_drift(root: Path, py_files: list[Path]) -> dict[str, object]:
    constants: list[dict[str, str]] = []
    for path in py_files:
        if "Archive" in path.parts:
            continue
        for item in extract_version_constants(path, root):
            item = dict(item)
            item["category"] = version_constant_category(item)
            constants.append(item)

    by_value: dict[str, list[str]] = defaultdict(list)
    by_category: dict[str, int] = Counter()
    for item in constants:
        by_value[item["value"]].append(f"{item['path']}::{item['name']}")
        by_category[item["category"]] += 1

    canonical = None
    canonical_source = ""
    preferred = [
        ("Core/version.py", "ATHENA_VERSION"),
        ("Core/version.py", "ATHENA_BUILD"),
        ("Intelligence/Core/version.py", "ATHENA_VERSION"),
        ("Intelligence/Core/version.py", "ATHENA_BUILD"),
        ("Core/version.py", "VERSION"),
        ("Intelligence/Core/version.py", "VERSION"),
    ]
    for preferred_path, preferred_name in preferred:
        for item in constants:
            if item["path"].replace("\\", "/") == preferred_path and item["name"] == preferred_name:
                canonical = normalized_version(item["value"])
                canonical_source = f"{item['path']}::{item['name']}"
                break
        if canonical:
            break

    release_constants = [item for item in constants if item.get("category") == "release_version"]
    release_drift: dict[str, list[str]] = defaultdict(list)
    component_catalog: dict[str, list[str]] = defaultdict(list)
    for item in constants:
        ref = f"{item['path']}::{item['name']}"
        value = item["value"]
        if item.get("category") == "release_version":
            if canonical and normalized_version(value) != canonical:
                release_drift[value].append(ref)
        else:
            component_catalog[item["category"]].append(f"{ref}={value}")

    return {
        "canonical_version": canonical or "UNKNOWN",
        "canonical_source": canonical_source,
        "version_value_count": len(by_value),
        "version_constants": constants,
        "version_category_counts": dict(sorted(by_category.items())),
        "release_drift_values": dict(sorted(release_drift.items())),
        "release_drift_count": sum(len(refs) for refs in release_drift.values()),
        "component_version_catalog": {key: sorted(value) for key, value in sorted(component_catalog.items())},
        # Compatibility fields retained for older Studio/report readers.
        "drift_values": dict(sorted(release_drift.items())),
        "drift_count": sum(len(refs) for refs in release_drift.values()),
    }


def duplicate_group_kind(paths: list[str]) -> str:
    active = [p for p in paths if not p.startswith("Archive/")]
    archived = [p for p in paths if p.startswith("Archive/")]
    if archived and not active:
        return "ARCHIVE_ONLY_DUPLICATE"
    if archived and active:
        return "ACTIVE_WITH_ARCHIVED_COPY"
    if all(p.endswith("/__init__.py") or p.endswith("__init__.py") for p in paths):
        return "EMPTY_INIT_OR_PACKAGE_MARKER"
    return "ACTIVE_DUPLICATE_REVIEW"


def build_duplicate_report(audit: dict[str, object]) -> dict[str, object]:
    rows_by_path = {row["path"]: row for row in audit.get("rows", [])}  # type: ignore[index]
    content_groups = []
    archive_only = 0
    active_with_archive = 0
    active_review = 0
    for digest, paths in (audit.get("duplicate_content") or {}).items():  # type: ignore[union-attr]
        classifications = sorted({rows_by_path.get(path, {}).get("classification", "UNKNOWN") for path in paths})
        kind = duplicate_group_kind(list(paths))
        if kind == "ARCHIVE_ONLY_DUPLICATE":
            archive_only += 1
        elif kind == "ACTIVE_WITH_ARCHIVED_COPY":
            active_with_archive += 1
        elif kind == "ACTIVE_DUPLICATE_REVIEW":
            active_review += 1
        content_groups.append({"sha1": digest, "count": len(paths), "kind": kind, "classifications": classifications, "paths": sorted(paths)})
    function_groups = []
    for name, locations in (audit.get("duplicate_function_names") or {}).items():  # type: ignore[union-attr]
        files = sorted({loc.split(":", 1)[0] for loc in locations})
        function_groups.append({"function": name, "count": len(locations), "file_count": len(files), "files": files[:25], "locations": locations[:50]})
    return {
        "version": audit["version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": audit["root"],
        "duplicate_content_groups": content_groups,
        "duplicate_content_summary": {"archive_only": archive_only, "active_with_archived_copy": active_with_archive, "active_review": active_review},
        "duplicate_function_groups": function_groups,
        "duplicate_function_mode": "probable_duplicate_implementations",
    }


def build_recommendations(audit: dict[str, object]) -> list[dict[str, object]]:
    counts = audit.get("classification_counts") or {}
    version_drift = audit.get("version_drift") or {}
    recs: list[dict[str, object]] = []
    recs.append({
        "priority": 1,
        "action": "Do not delete source yet",
        "rationale": "Only DELETE_SAFE cache/bytecode artifacts are approved for automated cleanup.",
        "affected_count": counts.get("DELETE_SAFE", 0),
    })
    for classification, label in [
        ("LEGACY_TOOL_REVIEW", "Consolidate legacy doctor/validator/patch scripts under common Studio workflows"),
        ("DYNAMIC_IMPORT_REVIEW", "Confirm dynamic entrypoints before classifying active source as obsolete"),
        ("ROOT_DOC_REVIEW", "Archive root-level historical manifests and release notes after approval"),
        ("RUNTIME_DATA_REVIEW", "Archive old generated reports/logs after exporting diagnostic bundles"),
        ("UNREFERENCED_SOURCE_REVIEW", "Review unreferenced Python tools for removal, archival, or Studio routing"),
    ]:
        recs.append({"priority": len(recs) + 1, "action": label, "classification": classification, "affected_count": counts.get(classification, 0)})
    recs.append({
        "priority": len(recs) + 1,
        "action": "Resolve release version drift",
        "rationale": "Only release version constants are treated as release drift; component/schema/generator versions are catalogued separately.",
        "affected_count": version_drift.get("release_drift_count", version_drift.get("drift_count", 0)),
        "canonical_version": version_drift.get("canonical_version", "UNKNOWN"),
    })
    return recs


def should_include_file(root: Path, path: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    if not parts:
        return False
    if parts[0] in IGNORED_ROOTS:
        return False
    if parts[0] in REPORT_ROOTS:
        return False
    return True


def discover_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file() and should_include_file(root, path)]


def build_architecture_governance(audit: dict[str, object]) -> dict[str, object]:
    rows = audit.get("rows", [])
    domain_counts: dict[str, Counter] = defaultdict(Counter)
    source_surface = 0
    generated_surface = 0
    review_surface = 0
    for row in rows:  # type: ignore[assignment]
        path = row["path"]
        top = path.split("/", 1)[0]
        domain = ARCHITECTURE_DOMAINS.get(top, "root_or_misc")
        classification = row["classification"]
        domain_counts[domain][classification] += 1
        if row["extension"] == ".py" and domain not in {"archive", "tests"}:
            source_surface += 1
        if classification in {"RUNTIME_DATA_REVIEW", "GENERATED_REPORT_REVIEW", "ROOT_DOC_REVIEW"}:
            generated_surface += 1
        if classification.endswith("REVIEW") or classification in {"CONSOLIDATE_CANDIDATE", "LEGACY_TOOL_REVIEW", "MANUAL_REVIEW_REQUIRED"}:
            review_surface += 1

    duplicate_report = build_duplicate_report(audit)
    version_drift = audit.get("version_drift") or {}
    recommendations = [
        {
            "priority": 1,
            "area": "release_versioning",
            "action": "Treat only release version constants as release drift; catalog component/schema/generator versions separately.",
            "affected_count": version_drift.get("release_drift_count", 0),
        },
        {
            "priority": 2,
            "area": "repository_surface",
            "action": "Archive root-level historical manifests into structured archive folders after approval.",
            "affected_count": (audit.get("classification_counts") or {}).get("ROOT_DOC_REVIEW", 0),
        },
        {
            "priority": 3,
            "area": "tooling",
            "action": "Route legacy doctors, validators, cleanup scripts, and audits through fewer durable Studio workflows.",
            "affected_count": (audit.get("classification_counts") or {}).get("LEGACY_TOOL_REVIEW", 0),
        },
        {
            "priority": 4,
            "area": "duplicates",
            "action": "Treat archive-only and active-with-archive duplicates as history; only active duplicate review groups require engineering attention.",
            "affected_count": duplicate_report.get("duplicate_content_summary", {}).get("active_review", 0),
        },
        {
            "priority": 5,
            "area": "dynamic_imports",
            "action": "Confirm dynamic entrypoints before demoting unreferenced active-source files.",
            "affected_count": (audit.get("classification_counts") or {}).get("DYNAMIC_IMPORT_REVIEW", 0),
        },
    ]
    return {
        "version": audit["version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": audit["root"],
        "canonical_version": version_drift.get("canonical_version", "UNKNOWN"),
        "domains": {domain: dict(counter) for domain, counter in sorted(domain_counts.items())},
        "source_surface_python_files": source_surface,
        "generated_or_documentation_surface": generated_surface,
        "review_surface_files": review_surface,
        "duplicate_content_summary": duplicate_report.get("duplicate_content_summary", {}),
        "probable_duplicate_implementation_groups": len(duplicate_report.get("duplicate_function_groups", [])),
        "version_category_counts": version_drift.get("version_category_counts", {}),
        "release_drift_count": version_drift.get("release_drift_count", 0),
        "recommendations": recommendations,
    }


def write_architecture_report(report: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"repository_architecture_governance_{stamp}.json"
    md_path = output_dir / f"repository_architecture_governance_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# AthenaEngine Architecture Governance Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Root: `{report['root']}`",
        f"Canonical version: `{report.get('canonical_version', 'UNKNOWN')}`",
        "",
        "## Surface Summary",
        "",
        f"Active Python source surface: **{report.get('source_surface_python_files', 0)}**",
        f"Generated/documentation surface: **{report.get('generated_or_documentation_surface', 0)}**",
        f"Review surface: **{report.get('review_surface_files', 0)}**",
        f"Release drift references: **{report.get('release_drift_count', 0)}**",
        f"Probable duplicate implementation groups: **{report.get('probable_duplicate_implementation_groups', 0)}**",
        "",
        "## Domain Classification Counts",
        "",
    ]
    for domain, counts in (report.get("domains") or {}).items():
        lines.append(f"### {domain}")
        for classification, count in sorted(counts.items()):
            lines.append(f"- {classification}: {count}")
        lines.append("")
    lines.extend(["## Architecture Recommendations", ""])
    for rec in report.get("recommendations", []):
        lines.append(f"- P{rec.get('priority')} `{rec.get('area')}`: {rec.get('action')} ({rec.get('affected_count', 0)})")
    lines.extend(["", "## Guardrail", "", "This report is advisory. It does not authorize source deletion, source consolidation, or release locking by itself.", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "summary": str(md_path)}


def run_governance_audit(root: Path | None = None) -> dict[str, object]:
    root = root or repo_root()
    files = discover_files(root)
    py_files = [path for path in files if path.suffix.lower() == ".py"]
    internal_refs, _modules, parse_errors = build_import_graph(root, py_files)
    rows = [classify_file(root, path, internal_refs) for path in files]
    classifications = Counter(row.classification for row in rows)
    roles = Counter(row.role for row in rows)
    duplicate_content = detect_duplicate_content(rows)
    duplicate_functions = detect_duplicate_function_names(root, py_files)
    tool_families = detect_studio_tool_families(root)
    cleanup_plan = build_cleanup_plan(rows)
    version_drift = detect_version_drift(root, py_files)

    audit: dict[str, object] = {
        "version": GOVERNANCE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "file_count": len(files),
        "python_file_count": len(py_files),
        "classification_counts": dict(sorted(classifications.items())),
        "role_counts": dict(sorted(roles.items())),
        "parse_error_count": len(parse_errors),
        "parse_errors": parse_errors[:100],
        "excluded_roots": sorted(IGNORED_ROOTS | REPORT_ROOTS),
        "duplicate_content_count": len(duplicate_content),
        "duplicate_content": duplicate_content,
        "duplicate_function_name_count": len(duplicate_functions),
        "duplicate_function_names": duplicate_functions,
        "studio_tool_families": tool_families,
        "cleanup_plan": cleanup_plan,
        "version_drift": version_drift,
        "rows": [asdict(row) for row in sorted(rows, key=lambda row: (row.classification, row.path))],
    }
    audit["architecture_governance"] = build_architecture_governance(audit)
    audit["recommendations"] = build_recommendations(audit)
    return audit


def write_outputs(audit: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"repository_governance_{stamp}.json"
    csv_path = output_dir / f"repository_governance_inventory_{stamp}.csv"
    md_path = output_dir / f"repository_governance_summary_{stamp}.md"

    json_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    rows = audit.get("rows", [])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "classification", "role", "reason", "size", "extension", "module", "imported_by", "sha1"])
        writer.writeheader()
        writer.writerows(rows)  # type: ignore[arg-type]

    lines = [
        "# AthenaEngine Repository Governance Summary",
        "",
        f"Version: `{audit['version']}`",
        f"Root: `{audit['root']}`",
        f"Generated: `{audit['generated_at']}`",
        "",
        "## Counts",
        "",
        f"Files: **{audit['file_count']}**",
        f"Python files: **{audit['python_file_count']}**",
        f"Parse errors: **{audit['parse_error_count']}**",
        f"Duplicate content groups: **{audit['duplicate_content_count']}**",
        f"Duplicate function-name groups: **{audit['duplicate_function_name_count']}**",
        "",
        "## Classification Counts",
        "",
    ]
    for name, count in audit["classification_counts"].items():  # type: ignore[union-attr]
        lines.append(f"- {name}: {count}")
    version_drift = audit.get("version_drift") or {}
    lines.extend(["", "## Version Governance", "", f"Canonical version: `{version_drift.get('canonical_version', 'UNKNOWN')}`", f"Release drift references: **{version_drift.get('release_drift_count', version_drift.get('drift_count', 0))}**", f"Version categories: `{version_drift.get('version_category_counts', {})}`"])
    lines.extend(["", "## Recommendations", ""])
    for rec in audit.get("recommendations", []):  # type: ignore[union-attr]
        lines.append(f"- P{rec.get('priority')}: {rec.get('action')} ({rec.get('affected_count', 0)})")
    lines.extend(["", "## Cleanup Rule", "", "Only `DELETE_SAFE` entries are safe for automated deletion. Everything else requires preview and explicit approval.", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "csv": str(csv_path), "summary": str(md_path)}


def write_architecture_review_queue_report(report: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"repository_architecture_review_queue_{stamp}.json"
    md_path = output_dir / f"repository_architecture_review_queue_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# AthenaEngine Architecture Review Queue",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Root: `{report['root']}`",
        "",
        f"Total review items: **{report['total_review_items']}**",
        "",
        "## Category Counts",
        "",
    ]
    for category, count in report.get("category_counts", {}).items():
        lines.append(f"- `{category}`: **{count}**")
    lines.extend(["", "## Review Items", ""])
    for item in report.get("items", [])[:250]:
        lines.append(f"- `{item.get('path')}`")
        lines.append(f"  - category: `{item.get('category')}`")
        lines.append(f"  - classification: `{item.get('classification')}` | role: `{item.get('role')}` | imported_by: `{item.get('imported_by')}`")
        if item.get("reason"):
            lines.append(f"  - reason: {item.get('reason')}")
    lines.extend(["", "## Guardrail", "", str(report.get("guardrail", "Diagnostic only.")), ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "summary": str(md_path)}


def write_duplicate_report(report: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"repository_duplicate_audit_{stamp}.json"
    md_path = output_dir / f"repository_duplicate_audit_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# AthenaEngine Repository Duplicate Audit", "", f"Generated: `{report['generated_at']}`", ""]
    lines.append(f"Duplicate content groups: **{len(report['duplicate_content_groups'])}**")
    summary = report.get("duplicate_content_summary", {})
    lines.append(f"Archive-only groups: **{summary.get('archive_only', 0)}**")
    lines.append(f"Active with archived copy groups: **{summary.get('active_with_archived_copy', 0)}**")
    lines.append(f"Active duplicate review groups: **{summary.get('active_review', 0)}**")
    lines.append(f"Probable duplicate implementation groups: **{len(report['duplicate_function_groups'])}**")
    lines.extend(["", "## Duplicate Content Groups", ""])
    for group in report["duplicate_content_groups"][:50]:  # type: ignore[index]
        lines.append(f"- {group['count']} files, kind={group.get('kind', 'UNKNOWN')}, classifications={', '.join(group['classifications'])}")
        for path in group["paths"][:10]:
            lines.append(f"  - `{path}`")
    lines.extend(["", "## Probable Duplicate Implementations", ""])
    for group in report["duplicate_function_groups"][:50]:  # type: ignore[index]
        lines.append(f"- `{group['function']}`: {group['count']} definitions across {group['file_count']} files")
        for path in group["files"][:10]:
            lines.append(f"  - `{path}`")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "summary": str(md_path)}


def write_recommendation_report(audit: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"repository_cleanup_recommendations_{stamp}.json"
    md_path = output_dir / f"repository_cleanup_recommendations_{stamp}.md"
    payload = {"version": audit["version"], "generated_at": datetime.now(timezone.utc).isoformat(), "root": audit["root"], "classification_counts": audit["classification_counts"], "version_drift": audit["version_drift"], "recommendations": audit["recommendations"]}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# AthenaEngine Cleanup Recommendation Report", "", f"Root: `{audit['root']}`", "", "## Recommendations", ""]
    for rec in audit.get("recommendations", []):  # type: ignore[union-attr]
        lines.append(f"### P{rec.get('priority')} — {rec.get('action')}")
        if rec.get("classification"):
            lines.append(f"Classification: `{rec.get('classification')}`")
        lines.append(f"Affected count: **{rec.get('affected_count', 0)}**")
        if rec.get("rationale"):
            lines.append(str(rec["rationale"]))
        lines.append("")
    lines.extend(["## Guardrail", "", "Do not delete, move, or consolidate anything outside `DELETE_SAFE` until the recommendation report has been reviewed and approved.", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "summary": str(md_path)}


def safe_cleanup(root: Path, apply: bool) -> list[str]:
    actions: list[str] = []
    for cache_dir in sorted(root.rglob("__pycache__")):
        actions.append(f"delete_dir:{rel(root, cache_dir)}")
        if apply:
            shutil.rmtree(cache_dir, ignore_errors=True)
    for cache_name in sorted(SAFE_DELETE_NAMES):
        for cache_dir in sorted(root.rglob(cache_name)):
            if cache_dir.is_dir():
                actions.append(f"delete_dir:{rel(root, cache_dir)}")
                if apply:
                    shutil.rmtree(cache_dir, ignore_errors=True)
    for pyc in sorted(root.rglob("*.pyc")):
        actions.append(f"delete_file:{rel(root, pyc)}")
        if apply:
            try:
                pyc.unlink()
            except FileNotFoundError:
                pass
    return actions


def archive_root_history(root: Path, apply: bool) -> list[str]:
    actions: list[str] = []
    candidates = sorted(list(root.glob("CHANGE_MANIFEST_*.md")) + list(root.glob("RELEASE_*.md")) + [p for p in root.glob("README_*") if p.is_file()])
    for source in candidates:
        if source.name.startswith("CHANGE_MANIFEST_"):
            destination = root / "Archive" / "Documentation" / "ChangeManifests"
        elif source.name.startswith("RELEASE_"):
            destination = root / "Archive" / "Documentation" / "ReleaseNotes"
        elif source.name.startswith("README_"):
            destination = root / "Archive" / "Documentation" / "LegacyReadme"
        else:
            destination = root / "Archive" / "Documentation" / "RootHistory"
        if apply:
            destination.mkdir(parents=True, exist_ok=True)
        target = destination / source.name
        actions.append(f"move:{rel(root, source)}->{rel(root, target)}")
        if apply:
            if target.exists():
                target = destination / f"{source.stem}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{source.suffix}"
            source.replace(target)
    return actions


def write_cleanup_report(root: Path, actions: list[str], apply: bool) -> Path:
    report_dir = root / "Reports" / "repository_governance"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"repository_cleanup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    summary = cleanup_action_summary(actions)
    lines = [
        "AthenaEngine Repository Governance Cleanup",
        "=" * 60,
        f"Applied: {apply}",
        f"Action count: {len(actions)}",
        "",
        "Grouped action summary:",
    ]
    for category, count in summary.items():
        lines.append(f"  {category}: {count}")
    lines.extend(["", "Actions:"])
    lines.extend(actions)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def print_summary(audit: dict[str, object], outputs: dict[str, str] | None = None) -> None:
    print("AthenaEngine Repository Governance")
    print("=" * 60)
    print(f"Version: {audit['version']}")
    print(f"Root: {audit['root']}")
    print(f"Files: {audit['file_count']}")
    print(f"Python files: {audit['python_file_count']}")
    print(f"Duplicate content groups: {audit['duplicate_content_count']}")
    print(f"Duplicate function-name groups: {audit['duplicate_function_name_count']}")
    version_drift = audit.get("version_drift") or {}
    print(f"Canonical version: {version_drift.get('canonical_version', 'UNKNOWN')}")
    print(f"Release drift references: {version_drift.get('release_drift_count', version_drift.get('drift_count', 0))}")
    print("Classification counts:")
    for name, count in audit["classification_counts"].items():  # type: ignore[union-attr]
        print(f"  {name}: {count}")
    if outputs:
        print("Outputs:")
        for label, path in outputs.items():
            print(f"  {label}: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AthenaEngine repository governance audit and cleanup planner.")
    parser.add_argument("--audit", action="store_true", help="Run governance audit and write reports. Default when no action is supplied.")
    parser.add_argument("--duplicates", action="store_true", help="Write a focused duplicate-content and duplicate-function report.")
    parser.add_argument("--recommendations", action="store_true", help="Write a cleanup recommendation report without changing files.")
    parser.add_argument("--architecture", action="store_true", help="Write an architecture governance report that summarizes domains, version categories, duplicate signal, and cleanup queue.")
    parser.add_argument("--review-queue", action="store_true", help="Write an architecture review queue report with category counts and review-safe itemization.")
    parser.add_argument("--preview-cleanup", action="store_true", help="Preview safe cleanup actions without modifying files.")
    parser.add_argument("--apply-delete-safe", action="store_true", help="Apply only reproducible cache/bytecode cleanup actions.")
    parser.add_argument("--apply-safe-cleanup", action="store_true", help="Compatibility alias for --apply-delete-safe.")
    parser.add_argument("--archive-root-history", action="store_true", help="With cleanup preview/apply mode, include root history archival actions in structured Archive/Documentation folders.")
    parser.add_argument("--apply-archive-root-history", action="store_true", help="Apply root historical manifest/readme/release-note archival. Must be paired with --archive-root-history.")
    args = parser.parse_args(argv)

    root = repo_root()
    needs_audit = args.audit or args.duplicates or args.recommendations or args.architecture or args.review_queue or not (args.preview_cleanup or args.apply_safe_cleanup or args.apply_delete_safe)
    audit: dict[str, object] | None = None

    if needs_audit:
        audit = run_governance_audit(root)

    if args.audit or (needs_audit and not (args.duplicates or args.recommendations or args.architecture or args.review_queue)):
        outputs = write_outputs(audit or run_governance_audit(root), root / "Reports" / "repository_governance")
        print_summary(audit or run_governance_audit(root), outputs)

    if args.duplicates:
        report = build_duplicate_report(audit or run_governance_audit(root))
        outputs = write_duplicate_report(report, root / "Reports" / "repository_governance")
        print("Repository Duplicate Audit")
        print("=" * 60)
        print(f"Duplicate content groups: {len(report['duplicate_content_groups'])}")
        summary = report.get("duplicate_content_summary", {})
        print(f"Archive-only duplicate groups: {summary.get('archive_only', 0)}")
        print(f"Active-with-archive duplicate groups: {summary.get('active_with_archived_copy', 0)}")
        print(f"Active duplicate review groups: {summary.get('active_review', 0)}")
        print(f"Probable duplicate implementation groups: {len(report['duplicate_function_groups'])}")
        print("Outputs:")
        for label, path in outputs.items():
            print(f"  {label}: {path}")


    if args.architecture:
        report = build_architecture_governance(audit or run_governance_audit(root))
        outputs = write_architecture_report(report, root / "Reports" / "repository_governance")
        print("Repository Architecture Governance")
        print("=" * 60)
        print(f"Canonical version: {report.get('canonical_version', 'UNKNOWN')}")
        print(f"Review surface files: {report.get('review_surface_files', 0)}")
        print(f"Release drift references: {report.get('release_drift_count', 0)}")
        print(f"Probable duplicate implementation groups: {report.get('probable_duplicate_implementation_groups', 0)}")
        print("Outputs:")
        for label, path in outputs.items():
            print(f"  {label}: {path}")

    if args.review_queue:
        report = build_architecture_review_queue(audit or run_governance_audit(root))
        outputs = write_architecture_review_queue_report(report, root / "Reports" / "repository_governance")
        print("Repository Architecture Review Queue")
        print("=" * 60)
        print(f"Review items: {report.get('total_review_items', 0)}")
        print("Category counts:")
        for category, count in report.get("category_counts", {}).items():
            print(f"  {category}: {count}")
        print("Outputs:")
        for label, path in outputs.items():
            print(f"  {label}: {path}")

    if args.recommendations:
        outputs = write_recommendation_report(audit or run_governance_audit(root), root / "Reports" / "repository_governance")
        print("Repository Cleanup Recommendations")
        print("=" * 60)
        for label, path in outputs.items():
            print(f"  {label}: {path}")

    if args.apply_archive_root_history and not args.archive_root_history:
        print("ERROR: --apply-archive-root-history requires --archive-root-history.")
        return 2

    if args.preview_cleanup or args.apply_safe_cleanup or args.apply_delete_safe or args.apply_archive_root_history:
        apply_delete_safe = bool(args.apply_safe_cleanup or args.apply_delete_safe)
        apply_archive = bool(args.apply_archive_root_history)
        actions = safe_cleanup(root, apply=apply_delete_safe)
        if args.archive_root_history:
            actions.extend(archive_root_history(root, apply=apply_archive))
        report = write_cleanup_report(root, actions, apply=bool(apply_delete_safe or apply_archive))
        summary = cleanup_action_summary(actions)
        print("Repository Governance Cleanup")
        print("=" * 60)
        print(f"Applied delete-safe: {apply_delete_safe}")
        print(f"Applied archive-root-history: {apply_archive}")
        print(f"Actions: {len(actions)}")
        print("Action summary:")
        for category, count in summary.items():
            print(f"  {category}: {count}")
        print(f"Report: {report}")
        if not (apply_delete_safe or apply_archive):
            print("No files changed. Use --apply-delete-safe and/or --archive-root-history --apply-archive-root-history for category-approved cleanup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
