"""Validate v0.5.5.5.8 acceptance display and analytical response fixes."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def main() -> int:
    print("Acceptance Display and Analysis Hotfix Validation")
    print("=" * 56)

    from Core.version import ATHENA_VERSION, SCOUT_VERSION, RELEASE_NAME
    check("version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0,5,5,5,8) and SCOUT_VERSION.startswith("v"), f"{ATHENA_VERSION} / {SCOUT_VERSION}")
    check("release name", RELEASE_NAME in {"Acceptance Display and Analysis Hotfix", "Scout Composition Root Fix"}, RELEASE_NAME)

    app_text = (ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    check("public renderer helper", "function isDeveloperModeActive()" in app_text, "developer helper present")
    check("public hides engine conclusion", "if (developerActive)" in app_text and "Engine Conclusion" in app_text, "engine conclusion suppressed outside Developer Mode")
    check("public hides facts", "if (developerActive)" in app_text and "Observed Facts" in app_text, "observed facts hidden outside Developer Mode")
    check("public hides cards", "diagnosticBlock" in app_text and "cards" in app_text, "diagnostic cards hidden outside Developer Mode")

    launch_text = (ROOT / "launch.py").read_text(encoding="utf-8")
    check("studio launch does not double-open", "ATHENA_STUDIO_MANAGED" in launch_text and "open_browser=not managed" in launch_text, "managed launch disables launcher browser open")

    from Scout.conversation.router import route_question
    from Scout.conversation.context import load_context
    ctx = load_context()

    oilers = route_question("Why have the Edmonton Oilers struggled defensively despite their offensive talent?", ctx, mode="public")
    oilers_text = oilers.get("natural_language_response", "")
    check("oilers analytical answer", "support-structure problem" in oilers_text and "defensive-zone exits" in oilers_text, oilers_text[:140])
    check("oilers no module leak", "Athena is combining" not in oilers_text and "PIF Build" not in oilers_text, oilers_text[:140])

    panthers = route_question("Tell me about the Florida Panthers.", ctx, mode="public")
    check("florida team route", panthers.get("intent") == "public_team_profile", str(panthers.get("intent")))
    check("florida public copy", "real-world NHL organization" in panthers.get("natural_language_response", ""), panthers.get("natural_language_response", "")[:140])

    ovi = route_question("Describe Alex Ovechkin's legacy.", ctx, mode="public")
    ovi_text = ovi.get("natural_language_response", "")
    check("legacy composition", "goal-scoring" in ovi_text.lower() and "Athena is combining" not in ovi_text, ovi_text[:140])

    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
