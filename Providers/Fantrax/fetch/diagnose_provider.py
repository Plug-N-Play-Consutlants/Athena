"""Run Fantrax provider diagnostics and save the report."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Core.logger import log_header, log
from Core.project_paths import LOGS_DIR
from Providers.Fantrax.diagnostics import run_provider_diagnostics


OUTPUT_FILE = LOGS_DIR / "fantrax_provider_diagnostics.json"


def main() -> None:
    log_header("FANTRAX PROVIDER DIAGNOSTICS")
    diagnostics = run_provider_diagnostics()
    write_json(OUTPUT_FILE, diagnostics)
    log(f"Diagnostics saved: {OUTPUT_FILE}")
    log(f"Configuration: {diagnostics.get('configuration_status')}")
    cookie = diagnostics.get("cookie", {})
    log(f"Cookie present: {cookie.get('present')} ({cookie.get('message')})")


if __name__ == "__main__":
    main()
