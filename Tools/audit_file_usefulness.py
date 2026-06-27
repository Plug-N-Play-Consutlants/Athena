"""AthenaEngine file usefulness audit.

Classifies repository files by likely role and cleanup risk. This tool is intentionally
conservative: static import absence is not treated as proof of dead code.
"""

from __future__ import annotations

import ast
import csv
import json
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


AUDIT_VERSION = "0.5.5.5.22"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def classify_path(path: str) -> str:
    parts = path.split("/")
    top = parts[0]
    name = parts[-1]

    if top == "Tests":
        return "TEST"
    if top == "Tools":
        if name.startswith("doctor_"):
            return "DOCTOR"
        if name.startswith("validate_"):
            return "VALIDATOR_IN_TOOLS"
        if name.startswith("cleanup_"):
            return "CLEANUP_TOOL"
        if name.startswith("audit_"):
            return "AUDIT_TOOL"
        return "TOOL"
    if top in {"Archive", "Logs", "Reports", "Output", "Raw", "Diagnostics"}:
        return "RUNTIME_OR_ARTIFACT"
    if name.startswith("CHANGE_MANIFEST") or name.startswith("README") or top == "docs" or name.endswith(".md"):
        return "DOC"
    if top == "Scout":
        return "SCOUT"
    if top == "Knowledge":
        return "KNOWLEDGE"
    if top == "Reasoning":
        return "REASONING"
    if top == "Intelligence":
        return "INTELLIGENCE"
    if top == "Engine":
        return "ENGINE"
    if top == "Providers":
        return "PROVIDER"
    if top == "Core":
        return "CORE"
    if top == "Athena":
        return "ATHENA_PACKAGE"
    if top == "Sports":
        return "SPORTS"
    if top == "Configuration":
        return "CONFIG"
    return "ROOT_OR_MISC"


def module_name(root: Path, path: Path) -> str:
    rp = path.relative_to(root)
    parts = list(rp.parts)
    if parts[-1] == "__init__.py":
        return ".".join(parts[:-1])
    return ".".join(parts)[:-3]


def build_import_graph(root: Path, py_files: List[Path]) -> Tuple[Dict[str, set], Dict[str, Path], List[Tuple[str, str]]]:
    file_by_module = {module_name(root, path): path for path in py_files}
    imports: Dict[str, set] = defaultdict(set)
    parse_errors: List[Tuple[str, str]] = []

    for path in py_files:
        module = module_name(root, path)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:
            parse_errors.append((rel(root, path), str(exc)))
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

    internal_refs: Dict[str, set] = defaultdict(set)
    modules = set(file_by_module)
    for source_module, imported_modules in imports.items():
        for imported in imported_modules:
            for target in modules:
                if imported == target or imported.startswith(target + ".") or target.startswith(imported + "."):
                    internal_refs[target].add(source_module)

    return internal_refs, file_by_module, parse_errors


def classify_file(root: Path, path: Path, internal_refs: Dict[str, set], file_by_module: Dict[str, Path]) -> Dict[str, object]:
    path_text = rel(root, path)
    parts = path_text.split("/")
    ext = path.suffix.lower() or "[none]"
    role = classify_path(path_text)
    module = module_name(root, path) if ext == ".py" else ""
    imported_by = len(internal_refs.get(module, set())) if module else ""

    action = "KEEP_REVIEW"
    reason = "Not yet classified."

    if ext == ".pyc" or "__pycache__" in parts:
        action = "DELETE_SAFE"
        reason = "Python bytecode/cache artifact; reproducible and not source."
    elif parts[0] == "Archive":
        action = "ARCHIVE_ALREADY"
        reason = "Already under Archive; exclude from active engineering surface."
    elif parts[0] in {"Logs", "Reports", "Output", "Raw", "Diagnostics"}:
        action = "RUNTIME_DATA_REVIEW"
        reason = "Runtime/generated data or diagnostic output; useful for runs but not active source."
    elif path.name.startswith("CHANGE_MANIFEST_"):
        action = "ARCHIVE_CANDIDATE"
        reason = "Historical change manifest at repository root; useful history but noisy active surface."
    elif path.name.startswith("README") and path.parent == root and path.name != "README.md":
        action = "ARCHIVE_CANDIDATE"
        reason = "Legacy/top-level README variant; useful history but noisy active surface."
    elif path.name in {
        "build_engine.py",
        "capabilities.py",
        "connect.py",
        "debug_export.py",
        "doctor.py",
        "exceptions.py",
        "launch.py",
        "operation_result.py",
        "orchestrator.py",
        "status.py",
        "sync.py",
        "workspace.py",
    }:
        action = "LEGACY_SHIM_REVIEW"
        reason = "Root or package-level Python shim/alias; confirm entrypoint usage before deletion."
    elif parts[0] == "Tools" and path.name.startswith(("doctor_", "validate_")):
        action = "KEEP_VALIDATION_OR_DOCTOR"
        reason = "Operational validation/doctor tooling."
    elif parts[0] == "Tests":
        action = "KEEP_TEST"
        reason = "Regression/acceptance test."
    elif parts[0] == "docs":
        action = "KEEP_DOC"
        reason = "Project documentation/audit artifact."
    elif ext == ".py" and imported_by == 0 and parts[0] not in {"Tools", "Tests"}:
        action = "ENTRYPOINT_OR_UNUSED_REVIEW"
        reason = "Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused."
    else:
        action = "KEEP_ACTIVE"
        reason = "Active source/config/documentation candidate."

    return {
        "path": path_text,
        "role": role,
        "action": action,
        "reason": reason,
        "size": path.stat().st_size,
        "ext": ext,
        "module": module,
        "imported_by": imported_by,
    }


def run_audit(root: Path | None = None) -> Dict[str, object]:
    root = root or repo_root()
    files = [path for path in root.rglob("*") if path.is_file()]
    py_files = [path for path in files if path.suffix == ".py"]
    internal_refs, file_by_module, parse_errors = build_import_graph(root, py_files)

    rows = [classify_file(root, path, internal_refs, file_by_module) for path in files]
    action_counts = Counter(row["action"] for row in rows)
    role_counts = Counter(row["role"] for row in rows)

    duplicate_names = defaultdict(list)
    for path in files:
        duplicate_names[path.name].append(rel(root, path))
    duplicate_names = {name: paths for name, paths in duplicate_names.items() if len(paths) > 1}

    return {
        "version": AUDIT_VERSION,
        "root": str(root),
        "file_count": len(files),
        "python_file_count": len(py_files),
        "parse_error_count": len(parse_errors),
        "parse_errors": parse_errors,
        "action_counts": dict(sorted(action_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "duplicate_filename_count": len(duplicate_names),
        "duplicate_filenames": dict(sorted(duplicate_names.items(), key=lambda item: (-len(item[1]), item[0]))[:50]),
        "rows": sorted(rows, key=lambda row: (str(row["action"]), str(row["path"]))),
    }


def write_outputs(audit: Dict[str, object], output_dir: Path) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"file_usefulness_audit_{AUDIT_VERSION}.json"
    csv_path = output_dir / f"file_usefulness_inventory_{AUDIT_VERSION}.csv"

    json_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    rows = audit["rows"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "role", "action", "reason", "size", "ext", "module", "imported_by"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return json_path, csv_path


def main() -> int:
    root = repo_root()
    audit = run_audit(root)
    output_dir = root / "Reports" / "file_usefulness"
    json_path, csv_path = write_outputs(audit, output_dir)

    print("AthenaEngine File Usefulness Audit")
    print("=" * 60)
    print(f"Version: {audit['version']}")
    print(f"Root: {audit['root']}")
    print(f"Files: {audit['file_count']}")
    print(f"Python files: {audit['python_file_count']}")
    print(f"Parse errors: {audit['parse_error_count']}")
    print()
    print("Action counts:")
    for action, count in audit["action_counts"].items():
        print(f"  {action}: {count}")
    print()
    print(f"Wrote JSON: {json_path}")
    print(f"Wrote CSV : {csv_path}")
    return 0


if __name__ == "__main__":
    main()
