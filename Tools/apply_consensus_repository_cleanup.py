"""Apply consensus repository cleanup items identified by Studio and external audit.

This tool is intentionally conservative. It removes or relocates only items that
are consensus cleanup targets and likely routing/interference risks:

* Intelligence/Core duplicate package after importers have migrated to Core.
* Archive/runtime_quarantine frozen runtime snapshots.
* Configuration/workspace.json committed mutable workspace state.
* Root release-history markdown files into Archive/Documentation.

Run without --apply for a preview. Use --apply to change files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))
REPORT_DIR = PROJECT_ROOT / "Reports" / "repository_governance"

ROOT_HISTORY_PREFIXES = (
    "CHANGE_MANIFEST_",
    "RELEASE_NOTES_",
    "CLEANUP_REPORT_",
)
ROOT_HISTORY_README_PREFIX = "README_"

ALLOWLIST_INTELLIGENCE_CORE_IMPORTERS = {
    "Tools/apply_consensus_repository_cleanup.py",
    "Tools/doctor_consensus_repository_cleanup.py",
    "Tests/validate_consensus_repository_cleanup.py",
    "Tools/doctor_core_namespace_recovery.py",
    "Tests/validate_core_namespace_recovery.py",
    "Tools/athena_studio.py",
}


@dataclass(frozen=True)
class CleanupAction:
    action: str
    path: str
    destination: str = ""
    status: str = "planned"
    reason: str = ""


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_remove_tree(path: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    root = PROJECT_ROOT.resolve()
    if root not in resolved.parents:
        raise RuntimeError(f"Refusing to remove path outside project root: {path}")
    shutil.rmtree(path)


def _safe_remove_file(path: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    root = PROJECT_ROOT.resolve()
    if root not in resolved.parents:
        raise RuntimeError(f"Refusing to remove path outside project root: {path}")
    path.unlink()


def _move_file(src: Path, dst: Path) -> None:
    resolved = src.resolve()
    root = PROJECT_ROOT.resolve()
    if root not in resolved.parents:
        raise RuntimeError(f"Refusing to move path outside project root: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if _sha256(src) == _sha256(dst):
            src.unlink()
            return
        stem = dst.stem
        suffix = dst.suffix
        i = 2
        while True:
            candidate = dst.with_name(f"{stem}_{i}{suffix}")
            if not candidate.exists():
                dst = candidate
                break
            i += 1
    shutil.move(str(src), str(dst))


def _python_files() -> Iterable[Path]:
    skip = {".git", "Reports", "Logs", "Output", "Raw", "Runtime", "Archive"}
    for path in PROJECT_ROOT.rglob("*.py"):
        parts = set(path.relative_to(PROJECT_ROOT).parts)
        if parts & skip:
            continue
        yield path


def find_legacy_core_importers() -> list[str]:
    offenders: list[str] = []
    tokens = ("Intelligence.Core", "Intelligence/Core")
    for path in _python_files():
        rel = _relative(path)
        if rel in ALLOWLIST_INTELLIGENCE_CORE_IMPORTERS:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(token in text for token in tokens):
            offenders.append(rel)
    return sorted(offenders)


def intelligence_core_is_duplicate() -> bool:
    legacy = PROJECT_ROOT / "Intelligence" / "Core"
    canonical = PROJECT_ROOT / "Core"
    if not legacy.exists():
        return True
    if not canonical.exists():
        return False
    for legacy_file in legacy.rglob("*.py"):
        rel = legacy_file.relative_to(legacy)
        canonical_file = canonical / rel
        if not canonical_file.exists():
            # __init__.py may intentionally differ during migration, but all
            # implementation modules must be represented by canonical Core.
            if legacy_file.name == "__init__.py":
                continue
            return False
        if legacy_file.name not in {"__init__.py", "version.py"} and _sha256(legacy_file) != _sha256(canonical_file):
            return False
    return True


def planned_actions() -> list[CleanupAction]:
    actions: list[CleanupAction] = []

    legacy_core = PROJECT_ROOT / "Intelligence" / "Core"
    if legacy_core.exists():
        actions.append(CleanupAction(
            action="remove_duplicate_package",
            path="Intelligence/Core",
            reason="Core/ is canonical; Intelligence/Core is a duplicate/legacy alias risk.",
        ))

    quarantine = PROJECT_ROOT / "Archive" / "runtime_quarantine"
    if quarantine.exists():
        actions.append(CleanupAction(
            action="remove_runtime_quarantine",
            path="Archive/runtime_quarantine",
            reason="Frozen runtime snapshots are duplicate source trees and can confuse audits/routing.",
        ))

    workspace = PROJECT_ROOT / "Configuration" / "workspace.json"
    if workspace.exists():
        actions.append(CleanupAction(
            action="remove_runtime_state",
            path="Configuration/workspace.json",
            reason="Mutable workspace state should be local/gitignored, not committed source.",
        ))

    docs_root = PROJECT_ROOT / "Archive" / "Documentation"
    for path in sorted(PROJECT_ROOT.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".md":
            continue
        name = path.name
        if name.startswith("CHANGE_MANIFEST_"):
            dst = docs_root / "ChangeManifests" / name
        elif name.startswith("README_"):
            dst = docs_root / "LegacyReadmes" / name
        elif name.startswith("RELEASE_NOTES_"):
            dst = docs_root / "ReleaseNotes" / name
        elif name.startswith("CLEANUP_REPORT_"):
            dst = docs_root / "CleanupReports" / name
        else:
            continue
        actions.append(CleanupAction(
            action="archive_root_history",
            path=name,
            destination=_relative(dst),
            reason="Root history/documentation belongs in Archive/Documentation, not repository root.",
        ))
    return actions


def apply_actions(actions: list[CleanupAction]) -> list[CleanupAction]:
    if (PROJECT_ROOT / "Intelligence" / "Core").exists():
        offenders = find_legacy_core_importers()
        if offenders:
            raise SystemExit("Refusing cleanup: legacy Intelligence.Core importers remain: " + ", ".join(offenders))
        if not intelligence_core_is_duplicate():
            raise SystemExit("Refusing cleanup: Intelligence/Core is not byte-identical to canonical Core implementation modules.")

    completed: list[CleanupAction] = []
    for action in actions:
        path = PROJECT_ROOT / action.path
        if action.action == "remove_duplicate_package":
            _safe_remove_tree(path)
            completed.append(CleanupAction(**{**asdict(action), "status": "applied"}))
        elif action.action == "remove_runtime_quarantine":
            _safe_remove_tree(path)
            completed.append(CleanupAction(**{**asdict(action), "status": "applied"}))
        elif action.action == "remove_runtime_state":
            _safe_remove_file(path)
            completed.append(CleanupAction(**{**asdict(action), "status": "applied"}))
        elif action.action == "archive_root_history":
            _move_file(path, PROJECT_ROOT / action.destination)
            completed.append(CleanupAction(**{**asdict(action), "status": "applied"}))
        else:
            completed.append(CleanupAction(**{**asdict(action), "status": "skipped"}))
    return completed


def write_report(actions: list[CleanupAction], *, applied: bool) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report = REPORT_DIR / f"consensus_repository_cleanup_{stamp}.json"
    payload = {
        "version": _version(),
        "applied": applied,
        "action_count": len(actions),
        "actions": [asdict(action) for action in actions],
    }
    report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    csv_path = report.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["action", "path", "destination", "status", "reason"])
        writer.writeheader()
        for action in actions:
            writer.writerow(asdict(action))
    return report


def _version() -> str:
    try:
        from Core.version import ATHENA_VERSION
        return ATHENA_VERSION
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply cleanup actions. Without this flag, only preview.")
    args = parser.parse_args()

    actions = planned_actions()
    result = apply_actions(actions) if args.apply else actions
    report = write_report(result, applied=args.apply)

    print("Consensus Repository Cleanup")
    print("=" * 64)
    print(f"Version: {_version()}")
    print(f"Applied: {args.apply}")
    print(f"Actions: {len(result)}")
    counts: dict[str, int] = {}
    for action in result:
        counts[action.action] = counts.get(action.action, 0) + 1
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    print(f"Report: {report}")
    if not args.apply:
        print("No files changed. Re-run with --apply to apply consensus cleanup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
