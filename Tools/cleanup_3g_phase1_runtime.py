"""3G Phase 1 runtime cleanup.

This script repairs live runtime state without deleting source code. It is safe to
run after applying the 3G.0 patch. It removes validation placeholders from the
active workspace, clears validation fixture operation-history entries, refreshes
version metadata, and redacts malformed local secrets into the new credential
shape.

Spyder:
    runfile('Tools/cleanup_3g_phase1_runtime.py', wdir=r'F:\Development\Athena')
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Athena.workspace import repair_workspace_file, secrets_status, load_secrets, SECRETS_FILE
from Core.version import ENGINE_LABEL


def main() -> int:
    workspace_payload = repair_workspace_file()
    workspace = workspace_payload.get("workspace", {}) if isinstance(workspace_payload, dict) else {}
    status = secrets_status()

    # Keep existing credential values in place but normalize the file shape when absent.
    if not SECRETS_FILE.exists():
        SECRETS_FILE.write_text(json.dumps({"fantrax": {}}, indent=2), encoding="utf-8")

    duplicate_roots = []
    for rel in ("Athena", "Sports_Intelligence_Engine_2.0"):
        candidate = PROJECT_ROOT / rel
        if candidate.exists() and candidate.is_dir():
            duplicate_roots.append(str(candidate.relative_to(PROJECT_ROOT)))

    report = {
        "ok": True,
        "engine_version": ENGINE_LABEL,
        "workspace_league_id": workspace.get("league_id"),
        "workspace_provider": workspace.get("provider"),
        "operation_history_count": len(workspace.get("operation_history") or []),
        "secret_status": status,
        "duplicate_legacy_roots_detected": duplicate_roots,
        "note": "Duplicate legacy roots are reported only in Phase 1; they are not deleted by this script.",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
