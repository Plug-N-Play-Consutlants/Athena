"""Studio entry point for the canonical Athena league synchronization pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Athena.sync import sync, FANTRAX_FANTASY_PIPELINE
from Athena.workspace import get_workspace_value


def main() -> int:
    # The Studio command must not silently select a different workspace or
    # declare success without executing the mandatory canonical stages.
    mode = str(get_workspace_value("mode") or "fantasy_league")
    provider = str(get_workspace_value("provider") or "Fantrax")
    if mode.lower() not in {"fantasy", "fantasy_league"} or provider.lower() != "fantrax":
        print(f"[FAIL] Sync League requires Fantrax fantasy workspace; got mode={mode}, provider={provider}.")
        return 1
    result = sync(mode=mode, provider=provider)
    required = {step["id"] for step in FANTRAX_FANTASY_PIPELINE if step.get("required", True)}
    completed = {step.get("id") for step in result.get("completed_steps", [])
                 if step.get("status") == "completed" and step.get("validation_status") == "pass"}
    missing = required - completed
    if result.get("ok") and (result.get("dry_run") or missing or result.get("mode", "").lower() != mode.lower()
                             or result.get("provider", "").lower() != provider.lower()):
        result = {**result, "ok": False, "error": f"Sync completion contract failed; missing required stages: {sorted(missing)}"}
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    if result.get("ok"):
        print("[PASS] Canonical Fantrax sync completed with all required stages verified.")
    else:
        print(f"[FAIL] Canonical Fantrax sync: {result.get('error') or 'see failed_step'}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
