from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION
from Knowledge.Events.live_intelligence import select_live_evidence
from Scout.conversation.router import route_question


def check(name: str, condition: bool, detail: object = "") -> tuple[str, bool, object]:
    return name, bool(condition), detail


def main() -> int:
    results = []
    results.append(check("athena_version", ATHENA_VERSION >= "0.5.5.5.16", ATHENA_VERSION))
    results.append(check("scout_version", SCOUT_VERSION >= "v0.5.5.5.16", SCOUT_VERSION))

    trade = select_live_evidence("Tell me about this weeks trades", mode="public", allow_network=False, limit=6)
    ignored_reasons = " ".join(" ".join(x.get("reasons", [])) for x in trade.get("ignored_events", []) if isinstance(x, dict))
    results.append(check("trade_filter_excludes_non_transaction_articles", "not_confirmed_transaction_item" in ignored_reasons or trade.get("selected_count", 0) == 0, trade))

    live_answer = route_question("Tell me about this weeks trades", mode="public")
    text = str(live_answer.get("natural_language_response") or live_answer.get("public_comment") or "")
    results.append(check("live_trade_answer_is_narrative", "confirmed NHL trade/transaction" in text or "I do not have" in text, text))
    results.append(check("live_trade_sources_attached", isinstance(live_answer.get("source_links"), list), live_answer.get("source_links")))
    results.append(check("live_trade_not_debug_only", "Scout consumed" not in text, text))

    leafs = route_question("What are the Leafs weaknesses?", mode="public")
    leafs_text = str(leafs.get("natural_language_response") or leafs.get("public_comment") or "")
    results.append(check("leafs_weakness_routes_analytically", leafs.get("intent") in {"public_analytical_route", "public_team_profile"}, leafs.get("intent")))
    results.append(check("leafs_weakness_answer_mentions_weakness", any(term in leafs_text.lower() for term in ["weakness", "risk", "hold them back", "structural"]), leafs_text))
    results.append(check("leafs_weakness_not_generic_profile_only", "Founded in 1917" not in leafs_text[:200], leafs_text))

    app_text = (ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    results.append(check("source_links_can_open_urls", "target=\"_blank\"" in app_text and "showSourcePopup" in app_text, "source renderer"))

    failed = [r for r in results if not r[1]]
    print("Live Event Filtering and Analytical Routing Validation")
    print("=" * 64)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print("-" * 64)
    print(f"Passed: {len(results)-len(failed)}")
    print(f"Failed: {len(failed)}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
