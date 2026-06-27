"""Validate Scout public route ordering and targeted team analysis cleanup."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME  # noqa: E402
from Knowledge.Intelligence.Routing.request_router import analyze_public_request  # noqa: E402
from Scout.conversation.router import route_question  # noqa: E402


def check(name: str, condition: bool, detail: object = "") -> tuple[str, bool, object]:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return name, condition, detail


def main() -> int:
    results = []
    results.append(check("version", ATHENA_VERSION == "0.5.5.5.18", ATHENA_VERSION))
    results.append(check("release_name", "Route Map" in RELEASE_NAME or "Routing" in RELEASE_NAME, RELEASE_NAME))

    leaf_possessive_route = analyze_public_request("What is the Leaf's weakness?")
    results.append(check("leaf_possessive_routes_team", leaf_possessive_route.route == "team_intelligence", leaf_possessive_route.to_dict()))

    leaf_answer = route_question("What is the Leaf's weakness?", mode="public")
    leaf_text = str(leaf_answer.get("public_comment") or "")
    results.append(check("leaf_weakness_title", "weakness" in str(leaf_answer.get("title", "")).lower(), leaf_answer.get("title")))
    results.append(check("leaf_weakness_is_single_team", "Edmonton Oilers" not in leaf_text and "Carolina Hurricanes" not in leaf_text and "Colorado Avalanche" not in leaf_text, leaf_text[:300]))
    results.append(check("leaf_weakness_mentions_risks", any(term in leaf_text.lower() for term in ["risk", "weakness", "defensive depth", "cap pressure", "playoff translation"]), leaf_text[:300]))

    broad_answer = route_question("Who are the strongest NHL teams?", mode="public")
    broad_text = str(broad_answer.get("public_comment") or "")
    results.append(check("broad_query_uses_broad_analysis", broad_answer.get("intent") == "public_analytical_route", broad_answer.get("title")))
    results.append(check("broad_query_can_list_multiple_teams", "Edmonton Oilers" in broad_text and "Carolina Hurricanes" in broad_text, broad_text[:300]))

    draft_answer = route_question("Evaluate the Leafs upcoming draft this year", mode="public")
    draft_text = str(draft_answer.get("public_comment") or "")
    forbidden = ["knowledge pack", "Route:", "Allowed domains", "Blocked domains"]
    results.append(check("draft_gap_public_language", not any(term.lower() in draft_text.lower() for term in forbidden), draft_text[:300]))
    results.append(check("draft_gap_team_framed", "Toronto" in draft_text or "Leafs" in draft_text, draft_text[:300]))

    doc_path = ROOT / "docs" / "SCOUT_ROUTE_MAP_v0.5.5.5.18.md"
    results.append(check("route_map_doc_exists", doc_path.exists(), doc_path))

    failed = [name for name, ok, _ in results if not ok]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    if failed:
        print("Failed:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
