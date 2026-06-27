"""Validate drop4e38 public reasoning reintegration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION
from Scout.conversation.router import route_question


def check(cond: bool, label: str, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}" + (f": {detail}" if detail else ""))
    return cond


def main() -> int:
    print("Reasoning Reintegration Validation")
    print("=" * 60)
    failures = 0

    if not check(ATHENA_VERSION in {"0.5.0-drop4e38", "0.5.0-drop4e39", "0.5.0-drop4e40", "0.5.0-drop4e41", "0.5.0-drop4e42", "0.5.0-drop4e42"}, "version", ATHENA_VERSION):
        failures += 1

    matthews = route_question("Auston Matthews", mode="public")
    dev = matthews.get("developer") or {}
    intel = dev.get("intelligence_used") or []
    natural = matthews.get("natural_language_response") or ""
    if not check("reasoning_engine" in intel and "executive_brief_composer" in intel, "public player uses reasoning stack", str(intel)):
        failures += 1
    if not check("Executive Summary" in natural and "Career Identity" in natural, "public player renders executive brief", natural[:120]):
        failures += 1

    aho = route_question("Sebastian Aho", mode="public")
    cards = aho.get("cards") or []
    prompts = [card.get("prompt") for card in cards]
    if not check(len(cards) >= 2 and all(prompts), "disambiguation cards include prompts", str(prompts)):
        failures += 1

    fin = route_question(prompts[0], mode="public") if prompts else {}
    if not check(fin.get("intent") == "public_player_profile", "clickable Aho prompt resolves to profile", fin.get("title", "")):
        failures += 1

    swe = route_question(prompts[1], mode="public") if len(prompts) > 1 else {}
    swe_dev = swe.get("developer") or {}
    if not check(swe.get("intent") == "public_player_profile" and "seed_profile_fallback" in (swe_dev.get("intelligence_used") or []), "Swedish Aho does not merge into Carolina reasoning", str(swe_dev.get("intelligence_used"))):
        failures += 1

    comp = route_question("Compare Auston Matthews and Connor McDavid", mode="public")
    comp_text = comp.get("natural_language_response") or ""
    if not check("What separates" in comp_text and "Provider-specific league context is excluded" in comp_text, "comparison narrative is structured/public-first", comp_text[:180]):
        failures += 1

    print()
    if failures:
        print(f"Overall status: FAIL | failures={failures}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
