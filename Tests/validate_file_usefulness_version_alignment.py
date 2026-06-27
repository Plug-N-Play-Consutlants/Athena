"""Validation for File Usefulness version alignment."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_audit_module():
    audit_tool = ROOT / "Tools" / "audit_file_usefulness.py"
    spec = importlib.util.spec_from_file_location("audit_file_usefulness", audit_tool)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME

    require(tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 5, 5, 5, 24), "Core ATHENA_VERSION was not advanced.")
    require(tuple(map(int, ATHENA_BUILD.split("."))) >= (0, 5, 5, 5, 24), "Core ATHENA_BUILD was not advanced.")
    require(bool(RELEASE_NAME), "Release name not set.")

    module = load_audit_module()
    require(module.AUDIT_VERSION == ATHENA_VERSION, "Audit version does not match Core.version.")
    require(module.canonical_version() == ATHENA_VERSION, "canonical_version() does not return Core.version.")

    audit = module.run_audit(ROOT)
    require(audit["version"] == ATHENA_VERSION, "run_audit() emitted stale version metadata.")
    require(audit["parse_error_count"] == 0, "File usefulness audit has parse errors.")
    require(audit["python_file_count"] >= 598, "Python file count unexpectedly decreased.")
    require(any(row["path"] == "Core/version.py" and row["action"] == "KEEP_ACTIVE" for row in audit["rows"]), "Core/version.py not retained as active source.")

    print("File Usefulness Version Alignment Validation")
    print("=" * 60)
    print(f"Version: {audit['version']}")
    print(f"Python files: {audit['python_file_count']}")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
