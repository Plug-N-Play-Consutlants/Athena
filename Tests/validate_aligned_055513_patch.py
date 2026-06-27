"""Validate v0.5.5.5.14 aligned .11/.12 cleanup patch."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def read(rel): return (ROOT / rel).read_text(encoding="utf-8")
def main():
    failures=[]
    if 'ATHENA_VERSION = "0.5.5.5.14"' not in read("Core/version.py"): failures.append("version")
    block=read("Scout/app.py")
    block=block[block.find("function renderAnswer"):block.find("function setConnectionStatus")]
    if block.count("const rawPayload") != 1: failures.append("rawPayload_count")
    if "let rawPayload" in block: failures.append("legacy_rawPayload")
    public_answers=read("Knowledge/Intelligence/Public/public_answers.py")
    if "def _set_public_surface" not in public_answers: failures.append("set_public_surface")
    if "_production_sentence" not in public_answers: failures.append("player_eval_sentence")
    if "evaluation: Optional[Dict[str, Any]]" not in public_answers: failures.append("player_eval_param")
    if "core_players" not in read("Knowledge/Intelligence/Public/public_team_profiles.py"): failures.append("team_fields")
    router=read("Scout/conversation/router.py")
    if "stars" not in router or "dallas" not in router: failures.append("dallas_route")
    if "how good (?:is|are)" not in router: failures.append("analytical_pattern")
    if "MALFORMED_PATCH_RESIDUE" not in read("Tools/cleanup_acceptance_pathway_residue.py"): failures.append("malformed_cleanup")
    if failures:
        print("v0.5.5.5.14 aligned cleanup validation: FAIL")
        for f in failures: print("[FAIL]", f)
        return 1
    print("v0.5.5.5.14 aligned cleanup validation: PASS")
    return 0
if __name__=="__main__": raise SystemExit(main())
