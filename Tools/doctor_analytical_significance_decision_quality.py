from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
scripts=['Tests/validate_analytical_significance_decision_quality.py','Tests/validate_player_intelligence_analytical_evidence.py']
failed=0
for script in scripts:
    p=subprocess.run([sys.executable,'-B',script],cwd=ROOT,text=True,capture_output=True)
    print(p.stdout,end='');print(p.stderr,end='')
    if p.returncode: failed=p.returncode
raise SystemExit(failed)
