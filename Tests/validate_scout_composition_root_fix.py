"""Validate Scout composition root/public-display contract.

This acceptance validator checks the actual root files, not nested stale patch
payloads, and confirms Scout's normal display contract is public-comment-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Scout.conversation.composition import compose_answer_payload


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return condition


def main() -> int:
    passed = 0
    failed = 0

    sample = {
        "intent": "player_analysis",
        "title": "Alex Ovechkin — L / WSH",
        "natural_language_response": "Executive Summary\nAlex Ovechkin is no longer assessed as a one-season stat line. Athena is combining identity, production, contract/control, public context, and trajectory evidence into a single asset assessment. The current local evidence supports a core asset classification.\n\nCurrent Value\nAlex Ovechkin currently profiles as core asset.",
        "engine_conclusion": "Athena is combining identity, production, contract/control, public context, and trajectory evidence into a single asset assessment.",
        "observed_facts": ["Identity evidence available: 1.", "Career Legacy: one of the NHL's defining goal scorers."],
        "known_limitations": ["PIF Build 004 does not yet run full era-adjusted goal models."],
        "cards": [{"label": "Role", "value": "Core Asset"}, {"label": "PPG", "value": "0.780"}],
        "confidence": 0.89,
        "developer": {"modules_executed": ["Player Intelligence"]},
    }
    composed = compose_answer_payload(sample)
    public = composed.get("public_comment", "")
    tests = [
        ("public_comment exists", bool(public), public[:120]),
        ("public strips Athena combining language", "Athena is combining" not in public, public),
        ("public strips evidence counters", "evidence available" not in public.lower(), public),
        ("diagnostics preserved", composed.get("diagnostics", {}).get("engine_conclusion") == sample["engine_conclusion"], "diagnostic conclusion retained"),
        ("display contract locked", composed.get("display_contract") == "public_comment_only", str(composed.get("display_contract"))),
    ]

    app_text = (ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    tests.extend([
        ("renderer uses public_comment first", "const publicText = String(answer.public_comment || '').trim();" in app_text, "publicText contract present"),
        ("renderer gates confidence to developer", "let diagnosticBlock = ''" in app_text and "if (developerActive)" in app_text and "Confidence:" in app_text, "diagnostics are inside developer block"),
        ("renderer public path filters cards", "rawCards.filter" in app_text and "developerVisible ? rawCards" in app_text, "public mode keeps only action cards"),
    ])

    run_scout = (ROOT / "Scout" / "run_scout.py").read_text(encoding="utf-8")
    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    tests.extend([
        ("managed launcher cannot open browser", 'ATHENA_STUDIO_MANAGED") == "1"' in run_scout and "open_browser = False" in run_scout, "child browser open disabled under Studio"),
        ("studio browser open deduped", "_last_browser_open_at" in studio and "skipping duplicate tab" in studio, "Studio open_scout has debounce"),
    ])

    version = (ROOT / "Core" / "version.py").read_text(encoding="utf-8")
    tests.append(("version advanced", 'ATHENA_VERSION = "0.5.5.5.14"' in version, "0.5.5.5.14"))

    for name, condition, detail in tests:
        if check(name, condition, detail):
            passed += 1
        else:
            failed += 1

    print("\nScout Composition Root Fix Validation")
    print("=" * 45)
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
