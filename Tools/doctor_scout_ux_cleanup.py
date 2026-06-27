"""Doctor for Scout UX cleanup drop4e26."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Scout" / "app.py"
VERSION = ROOT / "Core" / "version.py"

print("Scout UX Cleanup Doctor")
print("=" * 52)
issues: list[str] = []

def report(ok: bool, label: str) -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        issues.append(label)

text = APP.read_text(encoding="utf-8") if APP.exists() else ""
version_text = VERSION.read_text(encoding="utf-8") if VERSION.exists() else ""
report(APP.exists(), f"Scout app path: {APP}")
report("0.5.0-drop4e26" in version_text, "Core version is drop4e26")
report("/api/connect/fantrax" in text, "Fantrax test endpoint still wired")
report("/api/fantrax/connect-and-sync" in text, "Fantrax sync endpoint still wired")
report("fantraxCredentialForm.addEventListener('submit'" in text, "Fantrax test button cannot submit/reload page")
report("if (mode) mode.value = 'fantasy';" in text, "Fantrax actions preserve fantasy provider selection")
report("raw-reasoning" in text, "raw reasoning output has collapsed container")
report("Developer Mode" in text, "developer JSON output remains available")
report("localStorage.setItem('athena.fantrax.personal_profile_secret'" in text, "secret local persistence exists")
report("autocomplete=\"section-fantrax current-password\"" in text, "secret field supports password managers")
print()
if issues:
    print(f"Overall status: FAIL | failures={len(issues)}")
    for issue in issues:
        print(f" - {issue}")
    sys.exit(1)
print("Overall status: PASS")
