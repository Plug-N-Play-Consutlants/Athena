from __future__ import annotations
import subprocess,sys
p=subprocess.run([sys.executable,"-B","Tests/validate_organizational_asset_rights.py"],text=True,capture_output=True)
print("Organizational Asset Rights Doctor\n==================================")
print(p.stdout,end="");print(p.stderr,end="")
print("Overall status:","PASS" if p.returncode==0 else "FAIL")
raise SystemExit(p.returncode)
