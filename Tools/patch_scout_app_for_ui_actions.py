"""Patch Scout/app.py to load ui_action_repair.js.

Spyder:
    %runfile F:/Development/Athena/Tools/patch_scout_app_for_ui_actions.py --wdir
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP = PROJECT_ROOT / "Scout" / "app.py"

SCRIPT_TAG = '<script src="/static/ui_action_repair.js?v=1"></script>'


def main():
    print("Patch Scout app for UI actions")
    print("==============================")

    text = APP.read_text(encoding="utf-8")
    if SCRIPT_TAG in text or "ui_action_repair.js" in text:
        print("[PASS] Scout/app.py already references ui_action_repair.js")
        return

    # Common pattern: insert before </body> inside HTML template.
    if "</body>" in text:
        text = text.replace("</body>", f"{SCRIPT_TAG}\n</body>", 1)
        APP.write_text(text, encoding="utf-8")
        print("[PASS] Added repair script before </body>")
        return

    # Fallback: append to HTML constant if body close not found. This is less ideal
    # but keeps the patch moving.
    APP.write_text(text + "\n# UI repair script reference expected: " + SCRIPT_TAG + "\n", encoding="utf-8")
    print("[WARN] Could not find </body>; added marker comment only.")
    print("       If buttons still do not work, paste the script tag into the served HTML template.")


if __name__ == "__main__":
    main()
