"""
Centralized project paths for the Sports Intelligence Engine.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORE_DIR = PROJECT_ROOT / "Core"
PROVIDERS_DIR = PROJECT_ROOT / "Providers"
KNOWLEDGE_DIR = PROJECT_ROOT / "Knowledge"

CONFIGURATION_DIR = PROJECT_ROOT / "Configuration"

RAW_DIR = PROJECT_ROOT / "Raw"
OUTPUT_DIR = PROJECT_ROOT / "Output"
REPORTS_DIR = PROJECT_ROOT / "Reports"
LOGS_DIR = PROJECT_ROOT / "Logs"
ARCHIVE_DIR = PROJECT_ROOT / "Archive"
DOCS_DIR = PROJECT_ROOT / "docs"


def ensure_project_dirs() -> None:
    """Create the standard project directories if they do not exist."""
    for path in [
        RAW_DIR,
        OUTPUT_DIR,
        REPORTS_DIR,
        LOGS_DIR,
        ARCHIVE_DIR,
        DOCS_DIR,
        CONFIGURATION_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)