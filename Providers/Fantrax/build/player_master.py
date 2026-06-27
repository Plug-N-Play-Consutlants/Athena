"""
Fantrax Player Master Builder

Layer: Providers/Fantrax/build

Responsibility:
    Produce Output/player_master.* from the current canonical Fantrax player
    pool build output.

Current source of truth:
    Raw/fantrax_player_pool.json -> player_pool_master.py

This module preserves Output/player_master.json as a compatibility output for
existing Knowledge and Intelligence modules while removing dependency on retired
legacy raw files:

- Raw/player_ids.json
- Raw/team_rosters.json
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from Core.json_utils import read_optional_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR, ensure_project_dirs
from Providers.Fantrax.build.player_pool_master import build_player_pool_master


PLAYER_POOL_MASTER_JSON = OUTPUT_DIR / "player_pool_master.json"
PLAYER_MASTER_CSV = OUTPUT_DIR / "player_master.csv"
PLAYER_MASTER_JSON = OUTPUT_DIR / "player_master.json"


CSV_FIELDS = [
    "player_id",
    "player_name",
    "nhl_team",
    "position",
    "owner_team",
    "team_id",
    "contract_year",
    "contract_id",
    "roster_status",
    "availability_status",
    "contract_years_remaining",
    "contract_band",
    "source_type",
    "source_live",
]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _load_player_pool_master() -> dict[str, Any]:
    payload = read_optional_json(PLAYER_POOL_MASTER_JSON)
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload
    return build_player_pool_master()


def _rows_from_player_pool(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("records") or []
    rows: list[dict[str, Any]] = []

    for record in records:
        if not isinstance(record, dict):
            continue

        rows.append(
            {
                "player_id": _safe_str(record.get("fantrax_player_id")),
                "player_name": _safe_str(record.get("player_name")),
                "nhl_team": _safe_str(record.get("nhl_team") or record.get("teamShortName") or record.get("team_short_name")),
                "position": _safe_str(record.get("position")),
                "owner_team": _safe_str(record.get("fantasy_team")),
                "team_id": _safe_str(record.get("fantasy_team_id") or record.get("team_id")),
                "contract_year": _safe_str(record.get("contract_expiry_year")),
                "contract_id": _safe_str(record.get("contract_runway_indicator")),
                "roster_status": _safe_str(record.get("roster_slot") or record.get("source_status")),
                "availability_status": _safe_str(record.get("availability_status")),
                "contract_years_remaining": record.get("contract_years_remaining"),
                "contract_band": _safe_str(record.get("contract_band")),
                "source_type": _safe_str(record.get("source_type")),
                "source_live": bool(record.get("source_live")),
            }
        )

    return rows


def write_outputs(rows: list[dict[str, Any]]) -> None:
    ensure_project_dirs()
    with PLAYER_MASTER_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})
    write_json(PLAYER_MASTER_JSON, rows)


def build_player_master() -> list[dict[str, Any]]:
    payload = _load_player_pool_master()
    rows = _rows_from_player_pool(payload)
    write_outputs(rows)
    return rows


def main() -> None:
    rows = build_player_master()

    log_header("PLAYER MASTER COMPLETE", 80)
    log(f"Rows: {len(rows)}")
    log(f"CSV: {PLAYER_MASTER_CSV}")
    log(f"JSON: {PLAYER_MASTER_JSON}")

    log_section("Roster Status Counts", 80)
    for status, count in sorted(Counter(row.get("roster_status") for row in rows).items()):
        log(f"  {status}: {count}")

    missing_names = sum(1 for row in rows if not row.get("player_name"))
    log("")
    log(f"Missing player names: {missing_names}")


if __name__ == "__main__":
    main()
