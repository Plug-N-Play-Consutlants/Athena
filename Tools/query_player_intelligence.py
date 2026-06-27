"""Manual query tool for Athena Player Intelligence."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Intelligence.Player.player_intelligence import build_player_evaluation

if __name__ == "__main__":
    query = "Sidney Crosby"
    result = build_player_evaluation(query, mode="fantasy", project_root=PROJECT_ROOT)
    print("Player Intelligence")
    print("===================")
    print(f"Status: {result.get('status')}")
    print(f"Title: {result.get('title')}")
    print(f"Confidence: {result.get('confidence')}")
    print(result.get("evaluation"))
    for fact in result.get("observed_facts", [])[:8]:
        print(f"- {fact}")
    reports = result.get("reports") or {}
    if reports:
        print(f"JSON: {reports.get('json')}")
        print(f"Text: {reports.get('text')}")
    raise SystemExit(0)
