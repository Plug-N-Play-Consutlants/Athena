from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.constants import ENGINE_NAME, ENGINE_VERSION
from Core.project_paths import RAW_DIR, OUTPUT_DIR, REPORTS_DIR, LOGS_DIR, ensure_project_dirs
from Core.json_utils import write_json, read_json
from Core.knowledge_builder import build_metadata
from Core.logger import log_header, log


def main():
    log_header("CORE SELF TEST")

    ensure_project_dirs()

    test_file = OUTPUT_DIR / "_core_self_test.json"

    payload = {
        "status": "ok",
        "metadata": build_metadata(
            generator="core_self_test.py",
            generator_version="2.0.0",
            source="manual_test",
        ),
    }

    write_json(test_file, payload)
    loaded = read_json(test_file)

    assert loaded["status"] == "ok"
    assert loaded["metadata"]["engine"] == ENGINE_NAME
    assert loaded["metadata"]["engine_version"] == ENGINE_VERSION

    log(f"RAW_DIR: {RAW_DIR}")
    log(f"OUTPUT_DIR: {OUTPUT_DIR}")
    log(f"REPORTS_DIR: {REPORTS_DIR}")
    log(f"LOGS_DIR: {LOGS_DIR}")
    log("")
    log("Core self-test passed.")


if __name__ == "__main__":
    main()