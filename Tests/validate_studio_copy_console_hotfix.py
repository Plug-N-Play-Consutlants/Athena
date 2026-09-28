"""Validate fresh/native Studio console copy implementation without launching Tk."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
source=(ROOT/'Tools/athena_studio.py').read_text(encoding='utf-8')
checks=[]
def check(name, ok, detail=''):
    checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
print('Studio Copy Console Hotfix Validation'); print('='*60)
check('version_at_least_0_6_4_5_1', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,4,5,1), ATHENA_VERSION)
check('fresh_widget_snapshot', 'self.output.get("1.0", "end-1c")' in source, 'current Text widget buffer')
check('native_windows_clipboard', 'Set-Clipboard -Value $value' in source, 'PowerShell Set-Clipboard')
check('utf8_stdin', 'InputEncoding' in source and 'encoding="utf-8"' in source, 'UTF-8 console transfer')
check('no_cached_console_source', 'history/export/cache state' in source, 'explicit fresh snapshot contract')
check('fallback', 'Tk clipboard fallback' in source, 'Tk fallback retained')
print('-'*60); print('Overall status:', 'PASS' if all(checks) else 'FAIL')
raise SystemExit(0 if all(checks) else 1)
