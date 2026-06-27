"""
Shared utilities for deterministic knowledge builders.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from Core.constants import ENGINE_NAME, ENGINE_VERSION
from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import ensure_project_dirs


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_metadata(
    generator: str,
    generator_version: str,
    source: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    metadata = {
        "engine": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "generated": utc_now_iso(),
        "generator": generator,
        "generator_version": generator_version,
        "source": source,
    }

    if extra:
        metadata.update(extra)

    return metadata


def load_required_json(path: Path) -> Any:
    return read_json(path)


def write_knowledge_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_project_dirs()
    write_json(path, payload)


def start_builder(name: str) -> None:
    log_header(name)


def finish_builder(name: str, outputs: Dict[str, Path] | None = None) -> None:
    log("")
    log_header(f"{name} COMPLETE")

    if outputs:
        log_section("Output Files")
        for label, path in outputs.items():
            log(f"{label}: {path}")