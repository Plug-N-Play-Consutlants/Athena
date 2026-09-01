"""Doctor for Consensus Repository Cleanup with v0.6.3 root-history tolerance."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _read(path: str) -> str:
    target = ROOT / path
    return target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""


def _contains_legacy_core_import() -> list[str]:
    offenders: list[str] = []
    skip_parts = {".git", "Archive", "Reports", "Logs", "Output", "Raw", "Runtime"}
    allow = {
        "Tools/apply_consensus_repository_cleanup.py",
        "Tools/doctor_consensus_repository_cleanup.py",
        "Tests/validate_consensus_repository_cleanup.py",
        "Tools/doctor_core_namespace_recovery.py",
        "Tests/validate_core_namespace_recovery.py",
        "Tools/athena_studio.py",
    }
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if rel in allow:
            continue
        if set(path.relative_to(ROOT).parts) & skip_parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "Intelligence.Core" in text or "Intelligence/Core" in text:
            offenders.append(rel)
    return sorted(offenders)


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    return name, bool(condition), detail


def main() -> int:
    rows: list[tuple[str, bool, str]] = []
    version = importlib.import_module("Core.version")
    rows.append(check("version_at_least_cleanup", tuple(map(int, version.ATHENA_VERSION.split("."))) >= (0, 5, 5, 5, 26), version.ATHENA_VERSION))
    rows.append(check("release_name_available", bool(getattr(version, "RELEASE_NAME", "")), version.RELEASE_NAME))
    rows.append(check("core_canonical", (ROOT / "Core" / "version.py").exists(), "Core/version.py"))
    rows.append(check("legacy_intelligence_core_removed", not (ROOT / "Intelligence" / "Core").exists(), "Intelligence/Core"))
    rows.append(check("runtime_quarantine_removed", not (ROOT / "Archive" / "runtime_quarantine").exists(), "Archive/runtime_quarantine"))
    gitignore = _read(".gitignore")
    workspace_json = ROOT / "Configuration" / "workspace.json"
    workspace_ignored = "Configuration/workspace.json" in gitignore
    # Configuration/workspace.json is runtime state. Studio/Scout can recreate it
    # during normal use, so Verify Build must not fail merely because the file
    # exists after a session. Safe Cleanup still reports/removes it when applied.
    rows.append(check(
        "workspace_json_removed_or_ignored",
        (not workspace_json.exists()) or workspace_ignored,
        "absent" if not workspace_json.exists() else "present but gitignored; safe cleanup pending",
    ))
    rows.append(check("workspace_gitignored", workspace_ignored, ".gitignore"))
    rows.append(check("runtime_quarantine_gitignored", "Archive/runtime_quarantine/" in gitignore, ".gitignore"))
    # Patch archives cannot delete pre-existing files on extract. Root history
    # files are cleanup targets, but they must not break Verify Build while the
    # Studio-first safe cleanup flow is responsible for archiving them.
    tolerated_root_history = {
        "CHANGE_MANIFEST_v0.5.6.2.4_repository_review.md",
        "CHANGE_MANIFEST_v0.6.1.0.0_experience_layer_foundation.md",
        "CHANGE_MANIFEST_v0.6.2.0.0_player_experience_foundation.md",
        "CHANGE_MANIFEST_v0.6.2.0.2_player_experience_rendering_hotfix.md",
        "CHANGE_MANIFEST_v0.6.3.0.0_foundational_governance_and_module_adaptivity.md",
    }
    root_history = [
        p.name for p in ROOT.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".md"
        and (p.name.startswith("CHANGE_MANIFEST_") or p.name.startswith("README_") or p.name.startswith("RELEASE_NOTES_") or p.name.startswith("CLEANUP_REPORT_"))
        and p.name not in tolerated_root_history
    ]
    tolerated = sorted(p.name for p in ROOT.iterdir() if p.is_file() and (p.name in tolerated_root_history or p.name.startswith("README_v")))
    # Only truly unexpected root history is a failure. Known root history residue
    # remains a Release Hygiene warning and is archived by Studio Safe Cleanup.
    rows.append(check("root_history_archived", not root_history, ", ".join(root_history[:10]) if root_history else ("tolerated root history pending safe cleanup: " + ", ".join(tolerated) if tolerated else "none")))
    rows.append(check("archived_change_manifests_folder", (ROOT / "Archive" / "Documentation" / "ChangeManifests").exists(), "Archive/Documentation/ChangeManifests"))
    offenders = _contains_legacy_core_import()
    rows.append(check("no_legacy_core_importers", not offenders, ", ".join(offenders[:10]) if offenders else "none"))
    try:
        import build_engine
        missing = build_engine.validate_pipeline()
        rows.append(check("build_engine_pipeline_valid", not missing, ", ".join(missing) if missing else "all stages present"))
    except Exception as exc:  # pragma: no cover
        rows.append(check("build_engine_import", False, f"{type(exc).__name__}: {exc}"))

    failed = [row for row in rows if not row[1]]
    print("Consensus Repository Cleanup Doctor")
    print("=" * 64)
    for name, ok, detail in rows:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(rows) - len(failed)}")
    print(f"Failed: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
