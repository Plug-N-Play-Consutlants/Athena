"""Validate Scout UX cleanup for drop4e26."""
from __future__ import annotations

from pathlib import Path
import py_compile
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Scout" / "app.py"
VERSION = ROOT / "Core" / "version.py"

checks: list[tuple[bool, str]] = []

def check(condition: bool, label: str) -> None:
    checks.append((condition, label))
    print(f"[{'PASS' if condition else 'FAIL'}] {label}")

print("Scout UX Cleanup Validation")
print("=" * 52)
check(APP.exists(), f"Scout app exists: {APP}")
try:
    py_compile.compile(str(APP), doraise=True)
    check(True, "Scout app py_compile")
except Exception as exc:  # pragma: no cover
    check(False, f"Scout app py_compile: {exc}")

text = APP.read_text(encoding="utf-8")
version_text = VERSION.read_text(encoding="utf-8") if VERSION.exists() else ""
check("0.5.0-drop4e" in version_text, "version metadata available")
check("fantraxCredentialForm.addEventListener('submit'" in text, "Fantrax form submit is intercepted")
check("e.preventDefault()" in text, "Fantrax submit prevents page reload/provider bounce")
check("persistFantraxFieldsLocally" in text, "local Fantrax field persistence helper exists")
check("restoreFantraxFieldsLocally" in text, "local Fantrax field restore helper exists")
check("athena.fantrax.personal_profile_secret" in text, "Personal/Profile Secret ID local restore key exists")
check("Developer / Raw Reasoning Output" in text, "raw reasoning output is collapsed")
check("naturalIsLong" in text, "long natural language output is detected")
check("name=\"fantrax_personal_profile_secret\"" in text, "secret field has stable password-manager name")
check("data-lpignore=\"false\"" in text, "password-manager ignore flags are disabled")

failed = [label for ok, label in checks if not ok]
print()
if failed:
    print(f"Overall status: FAIL | failures={len(failed)}")
    sys.exit(1)
print("Overall status: PASS")
