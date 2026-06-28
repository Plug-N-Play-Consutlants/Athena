"""Validation for canonical root Core namespace."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    version = importlib.import_module("Core.version")
    logger = importlib.import_module("Core.logger")
    paths = importlib.import_module("Core.project_paths")

    require(version.ATHENA_VERSION >= "0.5.5.5.26", "Core version was not advanced.")
    require(version.ATHENA_BUILD == version.ATHENA_VERSION, "Core build/version mismatch.")
    require(not (ROOT / "Intelligence" / "Core").exists(), "Legacy Intelligence/Core should be removed after consensus cleanup.")
    require(Path(paths.PROJECT_ROOT).resolve() == ROOT.resolve(), "Core.project_paths does not resolve repository root.")
    require(callable(logger.log), "Core.logger.log missing.")
    require(callable(logger.log_header), "Core.logger.log_header missing.")
    require(callable(logger.log_section), "Core.logger.log_section missing.")

    print("Canonical Core Namespace Validation")
    print("=" * 60)
    print(f"Version: {version.ATHENA_VERSION}")
    print(f"Project root: {paths.PROJECT_ROOT}")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
