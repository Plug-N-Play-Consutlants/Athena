"""Release Hygiene Foundation doctor.

Checks packaging, CI, and version metadata consistency without mutating the repository.
This doctor is intentionally Studio-safe and read-only.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_NAME, SCOUT_VERSION, VERSION_SCHEMA  # noqa: E402

REPORT_DIR = PROJECT_ROOT / "Reports" / "release_hygiene"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _version_from_init(path: Path) -> str:
    text = _read(path)
    if "__version__ = ATHENA_VERSION" in text:
        return ATHENA_VERSION
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else ""


def _stub_files(folder: str) -> List[str]:
    base = PROJECT_ROOT / folder
    if not base.exists():
        return []
    stubs: List[str] = []
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = _read(path).strip()
        compact = text.replace('"', "'")
        if len(text) <= 80 and ("Module stub" in compact or "print('PASS')" in compact or 'print("PASS")' in compact):
            stubs.append(path.relative_to(PROJECT_ROOT).as_posix())
    return stubs


def build_report() -> Dict[str, Any]:
    checks: List[Tuple[str, str, str]] = []
    warnings: List[str] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append(("PASS" if ok else "FAIL", name, detail))

    pyproject = PROJECT_ROOT / "pyproject.toml"
    requirements = PROJECT_ROOT / "requirements.txt"
    workflow = PROJECT_ROOT / ".github" / "workflows" / "verify-build.yml"

    pyproject_text = _read(pyproject)
    requirements_text = _read(requirements)
    workflow_text = _read(workflow)

    check("pyproject.toml present", pyproject.exists(), str(pyproject.relative_to(PROJECT_ROOT)) if pyproject.exists() else "missing")
    check("requirements.txt present", requirements.exists(), str(requirements.relative_to(PROJECT_ROOT)) if requirements.exists() else "missing")
    check("GitHub workflow present", workflow.exists(), str(workflow.relative_to(PROJECT_ROOT)) if workflow.exists() else "missing")
    check("requests dependency declared", "requests" in pyproject_text and "requests" in requirements_text, "requests declared in pyproject and requirements")
    check("version schema locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA)
    check("Athena/Scout build aligned", SCOUT_VERSION == f"v{ATHENA_VERSION}" and ATHENA_BUILD == ATHENA_VERSION, f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}; Build={ATHENA_BUILD}")
    check("Athena package version unified", _version_from_init(PROJECT_ROOT / "Athena" / "__init__.py") == ATHENA_VERSION, _version_from_init(PROJECT_ROOT / "Athena" / "__init__.py") or "missing")
    check("root package version unified", _version_from_init(PROJECT_ROOT / "__init__.py") == ATHENA_VERSION, _version_from_init(PROJECT_ROOT / "__init__.py") or "missing")
    check("legacy doctor version imports Core.version", "VERSION = ATHENA_VERSION" in _read(PROJECT_ROOT / "Tools" / "doctor.py"), "Tools/doctor.py")
    check("CI runs release hygiene validator", "Tests/validate_release_hygiene.py" in workflow_text, ".github/workflows/verify-build.yml")
    check("CI runs release hygiene doctor", "Tools/doctor_release_hygiene.py" in workflow_text, ".github/workflows/verify-build.yml")

    test_stubs = _stub_files("Tests")
    tool_stubs = _stub_files("Tools")
    root_readmes = sorted(path.name for path in PROJECT_ROOT.glob("README*.txt") if path.is_file())
    root_change_manifests = sorted(path.name for path in PROJECT_ROOT.glob("CHANGE_MANIFEST_*.md") if path.is_file())
    if root_readmes:
        warnings.append(f"Root README text duplicates remain for later safe archival: {root_readmes}")
    if root_change_manifests:
        warnings.append(f"Root change manifests remain for later safe archival: {root_change_manifests}")
    if test_stubs:
        warnings.append(f"Stub or trivial test files remain for later integrity review: {test_stubs}")
    if tool_stubs:
        warnings.append(f"Stub or trivial tool/doctor files remain for later integrity review: {tool_stubs}")

    failed = [item for item in checks if item[0] == "FAIL"]
    status = "fail" if failed else "warn" if warnings else "pass"
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "version": ATHENA_VERSION,
        "release_name": RELEASE_NAME,
        "checks": [{"status": s, "name": n, "detail": d} for s, n, d in checks],
        "warnings": warnings,
        "summary": {
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "warnings": len(warnings),
            "stub_tests": len(test_stubs),
            "stub_tools": len(tool_stubs),
            "root_readme_duplicates": len(root_readmes),
            "root_change_manifests": len(root_change_manifests),
        },
    }


def write_report() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    path = REPORT_DIR / "release_hygiene_latest.json"
    stamped = REPORT_DIR / f"release_hygiene_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    payload = json.dumps(report, indent=2, sort_keys=True)
    path.write_text(payload + "\n", encoding="utf-8")
    stamped.write_text(payload + "\n", encoding="utf-8")
    return path


def main() -> int:
    report_path = write_report()
    report = build_report()
    print("Release Hygiene Foundation Doctor")
    print("=" * 64)
    for item in report["checks"]:
        print(f"[{item['status']}] {item['name']}: {item['detail']}")
    for warning in report["warnings"]:
        print(f"[WARN] {warning}")
    print(f"Report: {report_path}")
    print(f"Overall status: {report['status'].upper()}")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
