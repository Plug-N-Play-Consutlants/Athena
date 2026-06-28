"""Doctor for canonical root Core namespace.

Core/ is the only active Core namespace after consensus repository cleanup.
Legacy Intelligence/Core must not be required by doctors, validators, or runtime
paths.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    rows: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        rows.append((name, ok, detail))

    core_dir = ROOT / "Core"
    legacy_dir = ROOT / "Intelligence" / "Core"
    check("root_core_exists", core_dir.exists(), str(core_dir))
    check("legacy_core_removed_or_absent", not legacy_dir.exists(), str(legacy_dir))

    try:
        version = importlib.import_module("Core.version")
        logger = importlib.import_module("Core.logger")
        paths = importlib.import_module("Core.project_paths")
        imported = True
        detail = f"{version.ATHENA_VERSION} from {version.__file__}"
    except Exception as exc:  # pragma: no cover
        imported = False
        detail = repr(exc)
        version = logger = paths = None  # type: ignore[assignment]

    check("core_imports_resolve", imported, detail)
    if imported:
        check("version_advanced", getattr(version, "ATHENA_VERSION", "") >= "0.5.5.5.26", getattr(version, "ATHENA_VERSION", ""))
        check("project_root_is_repo_root", Path(paths.PROJECT_ROOT).resolve() == ROOT.resolve(), str(paths.PROJECT_ROOT))
        check("logger_api_available", all(hasattr(logger, name) for name in ["log", "log_header", "log_section"]), "log/log_header/log_section")

    print("Canonical Core Namespace Doctor")
    print("=" * 60)
    failed = 0
    for name, ok, detail in rows:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            failed += 1
    print()
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
