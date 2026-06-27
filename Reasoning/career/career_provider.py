"""Career profile data provider.

Build 003 starts with a small file-backed provider. Later builds can replace or
augment this with API/provider output without changing the composer.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Any, Dict, Optional


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


class CareerDataProvider:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or self._detect_root()

    def _detect_root(self) -> Path:
        candidates = [Path.cwd()]
        here = Path(__file__).resolve()
        candidates.extend(here.parents)
        for candidate in candidates:
            if (candidate / "Knowledge" / "Packs").exists():
                return candidate
        return Path.cwd()

    def load_player(self, name_or_key: str) -> Optional[Dict[str, Any]]:
        key = _slug(name_or_key)
        aliases = {
            "auston_matthews": "matthews",
            "matthews": "matthews",
            "analyze_auston_matthews": "matthews",
        }
        file_key = aliases.get(key, key)
        path = self.project_root / "Knowledge" / "Packs" / "NHL" / "player_career" / f"{file_key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
