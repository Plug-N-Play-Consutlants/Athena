"""Remove legacy acceptance-pathway residue that can shadow canonical code.

This cleanup is intentionally conservative. It removes:
1. The nested `AthenaEngine/` directory inside the canonical repository, if present.
2. Exact files created by the malformed v0.5.5.5.11 patch when it was extracted
   into F:\Development without the canonical `AthenaEngine/` prefix.

It does not delete unrelated developer folders wholesale. Parent directories are
removed only when they become empty after the exact residue files are deleted.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_ROOT = PROJECT_ROOT.parent
NESTED_ROOT = PROJECT_ROOT / "AthenaEngine"

MALFORMED_PATCH_RESIDUE = [
    "Core/version.py",
    "Scout/app.py",
    "Scout/conversation/router.py",
    "Knowledge/Intelligence/Intent/intent_classifier.py",
    "Knowledge/Intelligence/Entities/entity_registry.py",
    "Knowledge/Intelligence/Public/public_player_profiles.py",
    "Knowledge/Intelligence/Public/public_team_profiles.py",
    "Knowledge/Intelligence/Public/public_answers.py",
    "Tests/validate_public_analyst_composition_v055511.py",
    "CHANGE_MANIFEST_v0.5.5.5.11_public_analyst_composition.md",
]


def _remove_empty_parents(path: Path, stop_at: Path, removed: List[str]) -> None:
    current = path.parent
    stop_at = stop_at.resolve()
    while current.resolve() != stop_at and current.exists():
        try:
            current.rmdir()
        except OSError:
            break
        removed.append(str(current.relative_to(stop_at)))
        current = current.parent


def cleanup() -> Dict[str, object]:
    removed: List[str] = []
    skipped: List[str] = []
    if NESTED_ROOT.exists() and NESTED_ROOT.is_dir():
        shutil.rmtree(NESTED_ROOT)
        removed.append(str(NESTED_ROOT.relative_to(PROJECT_ROOT)))
    else:
        skipped.append(str(NESTED_ROOT.relative_to(PROJECT_ROOT)))
    for rel in MALFORMED_PATCH_RESIDUE:
        candidate = DEVELOPMENT_ROOT / rel
        try:
            candidate.relative_to(PROJECT_ROOT)
            skipped.append(f"canonical-skip:{rel}")
            continue
        except ValueError:
            pass
        if candidate.exists() and candidate.is_file():
            candidate.unlink()
            removed.append(str(candidate.relative_to(DEVELOPMENT_ROOT)))
            _remove_empty_parents(candidate, DEVELOPMENT_ROOT, removed)
        else:
            skipped.append(str(candidate.relative_to(DEVELOPMENT_ROOT)))
    return {"ok": True, "project_root": str(PROJECT_ROOT), "development_root": str(DEVELOPMENT_ROOT), "removed": removed, "skipped": skipped}


def main() -> int:
    result = cleanup()
    print("Acceptance Pathway Residue Cleanup")
    print("==================================")
    print(f"Project root: {result['project_root']}")
    print(f"Development root: {result['development_root']}")
    for item in result["removed"]: print(f"[REMOVED] {item}")  # type: ignore[index]
    for item in result["skipped"]: print(f"[SKIPPED] {item}")  # type: ignore[index]
    print("[PASS] Cleanup completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
