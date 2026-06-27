"""3G Phase 2 repository residue cleanup.

This script removes legacy/root-duplicate material that can confuse runtime
imports and validator state. It is intentionally conservative about live data:
Raw, Output, Reports, Logs, and Configuration/secrets.local.json are not purged.
Use this after applying 3G.2, then run the paired validator.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = PROJECT_ROOT / "Reports"
MANIFEST_DIR.mkdir(exist_ok=True)

PACKAGE_DIR = PROJECT_ROOT / "Athena"
NESTED_ROOT_DIR_NAMES = {
    "Archive",
    "Athena",
    "Configuration",
    "Core",
    "Diagnostics",
    "docs",
    "Intelligence",
    "Knowledge",
    "Logs",
    "Output",
    "Providers",
    "Raw",
    "Reports",
    "Scout",
    "Sports_Intelligence_Engine_2.0",
    "Tests",
}
NESTED_ROOT_FILE_PREFIXES = (
    "CHANGE_MANIFEST_",
    "RELEASE_NOTES_",
    "RELEASE_MANIFEST_",
    "MANIFEST_",
    "Release_Notes_",
)
NESTED_ROOT_FILES = {
    ".gitignore",
    "CHANGELOG.md",
    "README.md",
    "build_engine.py",
}
ROOT_LEGACY_DIRS = {
    "Sports_Intelligence_Engine_2.0",
}
PLACEHOLDER_IDS = {
    "validation_league_id",
    "test_league_id_provider_registry",
    "test_league_id_drop2",
    "test_league_id",
}


def _remove_path(path: Path, removed: List[Dict[str, str]]) -> None:
    if not path.exists():
        return
    kind = "dir" if path.is_dir() else "file"
    removed.append({"path": str(path.relative_to(PROJECT_ROOT)), "kind": kind})
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _remove_pycache(removed: List[Dict[str, str]]) -> None:
    for path in sorted(PROJECT_ROOT.rglob("__pycache__"), key=lambda p: len(str(p)), reverse=True):
        _remove_path(path, removed)
    for path in sorted(PROJECT_ROOT.rglob("*.pyc")):
        _remove_path(path, removed)


def _remove_legacy_roots(removed: List[Dict[str, str]]) -> None:
    # Top-level duplicate root directories copied from the old project.
    for name in ROOT_LEGACY_DIRS:
        _remove_path(PROJECT_ROOT / name, removed)

    # A prior packaging step copied an entire Athena repository inside the
    # Athena Python package. Keep only package modules; remove nested roots,
    # old manifests, generated data, docs, and duplicated package trees.
    if PACKAGE_DIR.exists():
        for child in sorted(PACKAGE_DIR.iterdir()):
            if child.is_dir() and child.name in NESTED_ROOT_DIR_NAMES:
                _remove_path(child, removed)
                continue
            if child.is_file():
                if child.name in NESTED_ROOT_FILES or child.name.startswith(NESTED_ROOT_FILE_PREFIXES):
                    _remove_path(child, removed)


def _sanitize_workspace() -> Dict[str, Any]:
    workspace_path = PROJECT_ROOT / "Configuration" / "workspace.json"
    if not workspace_path.exists():
        return {"workspace_file_exists": False}
    try:
        payload = json.loads(workspace_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - validation catches this
        return {"workspace_file_exists": True, "error": str(exc)}
    workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else payload
    if not isinstance(workspace, dict):
        workspace = {}
    if str(workspace.get("league_id") or "").strip() in PLACEHOLDER_IDS:
        workspace["league_id"] = None
    workspace["engine_version"] = "Athena v0.5.0-drop3g2"
    # Drop validation/test fixture operation records if any survived.
    history = workspace.get("operation_history")
    if isinstance(history, list):
        workspace["operation_history"] = [
            item for item in history
            if "validation_league_id" not in str(item) and "Tests/fixtures/" not in str(item)
        ]
    last_op = workspace.get("last_operation_result")
    if isinstance(last_op, dict) and ("validation_league_id" in str(last_op) or "Tests/fixtures/" in str(last_op)):
        workspace.pop("last_operation_result", None)
    payload = {"workspace": workspace}
    workspace_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "workspace_file_exists": True,
        "league_id": workspace.get("league_id"),
        "engine_version": workspace.get("engine_version"),
        "operation_history_count": len(workspace.get("operation_history") or []),
    }


def _harden_gitignore() -> Dict[str, Any]:
    gitignore = PROJECT_ROOT / ".gitignore"
    required = [
        "# Local secrets",
        "Configuration/secrets.local.json",
        "# Python cache",
        "__pycache__/",
        "*.py[cod]",
        "# Local runtime artifacts",
        "Raw/",
        "Output/",
        "Reports/",
        "Logs/",
        "Runtime/",
    ]
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    lines = existing.splitlines()
    changed = False
    for line in required:
        if line not in lines:
            lines.append(line)
            changed = True
    if changed:
        gitignore.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"exists": gitignore.exists(), "changed": changed}


def main() -> int:
    removed: List[Dict[str, str]] = []
    _remove_legacy_roots(removed)
    _remove_pycache(removed)
    workspace_status = _sanitize_workspace()
    gitignore_status = _harden_gitignore()
    manifest = {
        "cleanup": "3G Phase 2 Repository Residue Cleanup",
        "version": "0.5.0-drop3g2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT_ROOT),
        "removed_count": len(removed),
        "removed": removed,
        "workspace_status": workspace_status,
        "gitignore_status": gitignore_status,
        "notes": [
            "Live Raw/Output/Reports/Logs data was preserved.",
            "Configuration/secrets.local.json was preserved if present.",
            "Nested legacy project roots and Python cache files were removed.",
        ],
    }
    manifest_path = MANIFEST_DIR / "cleanup_3g_phase2_residue_report.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("3G Phase 2 residue cleanup complete")
    print(f"Removed: {len(removed)} paths")
    print(f"Report: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
