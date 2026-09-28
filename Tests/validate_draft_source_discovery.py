"""Focused validation for v0.6.4.2.0 authenticated draft source discovery."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Providers.Fantrax.endpoints import FantraxEndpoints
from Providers.Fantrax.fantrax_client import FantraxClient

def main():
    studio=(ROOT/"Tools/athena_studio.py").read_text(encoding="utf-8")
    discovery=(ROOT/"Providers/Fantrax/fetch/discover_draft_source.py").read_text(encoding="utf-8")
    checks=[
      (ATHENA_VERSION=="0.6.4.2.0","version",ATHENA_VERSION),
      (RELEASE_NAME=="Authenticated Draft Source Discovery","release_name",RELEASE_NAME),
      (FantraxEndpoints.DRAFT_PICKS=="general/getDraftPicks","draft_endpoint",FantraxEndpoints.DRAFT_PICKS),
      (hasattr(FantraxClient,"get_draft_picks"),"client_method","get_draft_picks"),
      ("Discover Draft Source" in studio and "def discover_draft_source" in studio,"studio_action","present"),
      ("Credential values: REDACTED / NOT EXPORTED" in discovery,"credential_redaction","present"),
      ("draft_picks.json" in discovery,"raw_capture","present"),
    ]
    print("Draft Source Discovery Validation")
    print("="*72)
    failed=0
    for ok,name,detail in checks:
      print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
      failed += 0 if ok else 1
    print(f"\nResult: {len(checks)-failed}/{len(checks)} checks passed")
    raise SystemExit(1 if failed else 0)
if __name__=="__main__": main()
