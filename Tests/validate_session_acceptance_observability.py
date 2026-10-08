from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'Scout' / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'Core' / 'version.py').read_text(encoding='utf-8')

assert tuple(map(int, VERSION.split("."))) >= (0, 7, 7, 3, 4)
assert 'presentation_mode' in APP
assert 'USER-VISIBLE RESPONSE:' in APP
assert 'INTERNAL EXECUTION RESULT:' in APP
assert '/api/session/visible' in APP
assert 'user_visible_text' in APP
assert 'developer_mode: isDeveloperModeActive()' in APP
assert "return last ? String(last.innerText || '').trim() : '';" in APP
assert 'session_turn_id' in APP
print('PASS: session acceptance observability separates browser-visible output from internal execution.')
