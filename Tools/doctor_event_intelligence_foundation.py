"""Aggregate Event Intelligence doctor for Athena 0.5.3.1.0."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Tools.doctor_multi_sport_provider_connectors import main as doctor_multi_sport_connectors


if __name__ == "__main__":
    raise SystemExit(doctor_multi_sport_connectors())
