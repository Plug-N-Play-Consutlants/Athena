from __future__ import annotations
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks={
"investigation state":ROOT/'Athena/Investigation/state.py',
"transaction investigation":ROOT/'Athena/Investigation/nhl_transaction.py',
"NHL provider capabilities":ROOT/'Providers/NHL/capabilities.py',
"NHL roster normalization":ROOT/'Knowledge/Organizations/nhl_roster_evidence.py',
"validator":ROOT/'Tests/validate_whole_picture_investigation.py',
}
missing=[name for name,p in checks.items() if not p.exists()]
if missing:
 print('FAIL: missing '+', '.join(missing));raise SystemExit(1)
r=subprocess.run([sys.executable,str(checks['validator'])],cwd=str(ROOT))
raise SystemExit(r.returncode)
