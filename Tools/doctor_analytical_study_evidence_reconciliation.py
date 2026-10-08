from __future__ import annotations
import subprocess,sys
p=subprocess.run([sys.executable,'-B','Tests/validate_analytical_study_evidence_reconciliation.py'],text=True,capture_output=True)
print('Analytical Study & Evidence Reconciliation Doctor\n=================================================')
print(p.stdout,end='');print(p.stderr,end='')
print('Overall status:','PASS' if p.returncode==0 else 'FAIL')
raise SystemExit(p.returncode)
