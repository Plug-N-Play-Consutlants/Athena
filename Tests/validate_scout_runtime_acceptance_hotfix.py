"""Validation for v0.5.5.5.x Scout Runtime Acceptance Hotfix / Studio Log Visibility Hotfix."""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _safe_detail(value: object) -> str:
    text = str(value)
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

os.environ.setdefault("ATHENA_SCOUT_LIVE_NETWORK", "0")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def record(results: list[tuple[str, bool, str]], name: str, condition: bool, detail: str = "") -> None:
    results.append((name, bool(condition), detail))


def main() -> int:
    results: list[tuple[str, bool, str]] = []
    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME
    from Knowledge.Events.live_intelligence import LIVE_INTELLIGENCE_CONSUMPTION_VERSION, live_intelligence_diagnostics, select_live_evidence
    from Athena.capabilities import assess_capabilities, capability_dashboard
    from Scout.conversation.router import route_question

    record(results, "athena_version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 5, 5, 5, 1), ATHENA_VERSION)
    record(results, "athena_build", tuple(map(int, ATHENA_BUILD.split("."))) >= (0, 5, 5, 5, 1), ATHENA_BUILD)
    record(results, "release_name_available", bool(RELEASE_NAME), RELEASE_NAME)
    record(results, "live_consumption_version", tuple(map(int, LIVE_INTELLIGENCE_CONSUMPTION_VERSION.split("."))) >= (0, 5, 5, 5, 1), LIVE_INTELLIGENCE_CONSUMPTION_VERSION)

    evidence = select_live_evidence("What recent NHL events are available?", mode="public")
    record(results, "live_feed_count", evidence.get("feed_count", 0) >= 1, str(evidence))
    record(results, "live_selected_count", evidence.get("selected_count", 0) >= 1, str(evidence))
    record(results, "live_evidence_ledger", bool(evidence.get("evidence_ledger")), str(evidence.get("evidence_ledger")))
    diag = live_intelligence_diagnostics()
    record(results, "live_diag", diag.get("status") in {"pass", "warn"}, str(diag))

    report = assess_capabilities()
    dashboard = capability_dashboard(report)
    live_caps = [cap for cap in report.get("capabilities", []) if isinstance(cap, dict) and cap.get("key") == "live_event_sources"]
    record(results, "capability_live_present", len(live_caps) == 1, str(dashboard.get("lines")))
    record(results, "capability_live_available", live_caps and live_caps[0].get("status") == "available", str(live_caps))
    record(results, "dashboard_line_mentions_rss", any("RSS feeds configured" in str(line) for line in dashboard.get("lines", [])), str(dashboard.get("lines")))

    diagnostic = route_question("What intelligence modules executed?", mode="public")
    record(results, "diagnostic_not_clarify", diagnostic.get("intent") == "scout_runtime_diagnostics", str(diagnostic))
    record(results, "diagnostic_trace", bool((diagnostic.get("developer") or {}).get("runtime_trace")), str(diagnostic.get("developer")))
    evidence_answer = route_question("What evidence did you use?", mode="public")
    record(results, "evidence_prompt_not_clarify", evidence_answer.get("intent") == "scout_runtime_diagnostics", str(evidence_answer))

    leafs = route_question("who are the Maple Leafs", mode="public")
    record(results, "team_prompt_continues_past_routing", leafs.get("intent") == "public_team_profile", str(leafs))
    record(results, "team_prompt_not_routing_summary", leafs.get("title") != "Multi-Sport Scout Routing", str(leafs.get("title")))
    record(results, "team_prompt_has_team_answer", "Toronto Maple Leafs" in str(leafs.get("engine_conclusion", "")) or "Toronto Maple Leafs" in str(leafs.get("title", "")), str(leafs))

    aho = route_question("Who is Sebastian Aho?", mode="public")
    aho_text = str(aho.get("natural_language_response", "")) + " " + str(aho.get("observed_facts", []))
    record(results, "sebastian_aho_disambiguates", aho.get("intent") == "public_entity_disambiguation", str(aho))
    record(results, "sebastian_aho_profiles_candidates", "Carolina" in aho_text and "Swedish" in aho_text, aho_text)

    leafs_team_text = str(leafs.get("natural_language_response", "")) + " " + str(leafs.get("observed_facts", []))
    record(results, "team_answer_contains_history", "1917" in leafs_team_text and "Stanley Cups" in leafs_team_text, leafs_team_text)
    record(results, "team_answer_not_meta_presentation", "should be read" not in leafs_team_text.lower() and "should be evaluated" not in leafs_team_text.lower(), leafs_team_text)

    recent = route_question("What recent NHL events are available?", mode="public")
    record(results, "recent_events_route", recent.get("intent") == "live_event_intelligence", str(recent))
    record(results, "recent_events_content", bool(recent.get("natural_language_response")) and ("recent NHL event" in recent.get("natural_language_response", "").lower() or "found" in recent.get("natural_language_response", "").lower()), str(recent))
    record(results, "recent_events_developer", bool((recent.get("developer") or {}).get("live_evidence")), str(recent.get("developer")))

    contenders = route_question("Who are the best Stanley Cup contenders right now, and why?", mode="public")
    strongest = route_question("Which NHL teams are strongest right now?", mode="public")
    improved = route_question("Who improved the most this offseason?", mode="public")
    oilers = route_question("Why are the Oilers contenders?", mode="public")
    record(results, "public_contender_routes", contenders.get("intent") == "public_analytical_route", str(contenders))
    record(results, "public_contender_not_clarify", contenders.get("title") != "Scout needs one more detail", str(contenders))
    record(results, "public_contender_bounded", "live standings" in str(contenders.get("natural_language_response", "")).lower(), str(contenders))
    record(results, "public_strongest_routes", strongest.get("intent") == "public_analytical_route", str(strongest))
    record(results, "public_improved_bounded", improved.get("intent") == "public_analytical_route" and "transaction" in str(improved.get("natural_language_response", "")).lower(), str(improved))
    record(results, "public_oilers_contender_routes", oilers.get("intent") == "public_analytical_route" and "Oilers" in str(oilers.get("natural_language_response", "")), str(oilers))

    leafs_trade = route_question("Maple leafs last trade", mode="public")
    leafs_trade_text = str(leafs_trade.get("natural_language_response", "")) + " " + str(leafs_trade.get("observed_facts", []))
    record(results, "leafs_trade_no_unrelated_canadiens", "Canadiens acquire defenseman" not in leafs_trade_text, str(leafs_trade))
    record(results, "leafs_trade_clear_no_match", "do not have a confirmed" in str(leafs_trade.get("natural_language_response", "")).lower() or "do not have a matching" in str(leafs_trade.get("natural_language_response", "")).lower() or leafs_trade.get("confidence", 1) < 0.6, str(leafs_trade))

    from Scout import app as scout_app
    scout_app.SESSION_TRANSCRIPT.clear()
    scout_app._record_session_turn("Who are the Maple Leafs?", "public", leafs)
    session_result = scout_app._write_session_log()
    record(results, "session_log_written", session_result.get("ok") and Path(session_result.get("text_path", "")).exists(), str(session_result))
    text = Path(session_result.get("text_path", "")).read_text(encoding="utf-8")
    record(results, "session_log_contains_prompt_response", "Who are the Maple Leafs?" in text and "Toronto Maple Leafs" in text, text[:500])

    help_answer = route_question("", mode="public")
    cards = help_answer.get("cards") or []
    record(results, "help_cards_clickable", bool(cards) and all(c.get("prompt") and c.get("action") == "ask_prompt" for c in cards), str(cards))

    app = (ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    record(results, "ui_try_cards_clickable", "impliedPrompt" in app and "action-card" in app, "Scout/app.py")
    record(results, "public_status_live_sources", "live_sources.py" in app and "live_intelligence" in app, "Scout/app.py")
    record(results, "session_log_button_present", "sessionLogBtn" in app and "/api/session/export" in app and "bindButton('sessionLogBtn', exportSessionLog)" in app, "Scout/app.py")
    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    record(results, "studio_log_viewer_window", "def _open_text_window" in studio and "Latest Debug" in studio, "Tools/athena_studio.py")
    record(results, "studio_subprocess_utf8", "PYTHONIOENCODING" in studio and "errors=\"replace\"" in studio, "Tools/athena_studio.py")

    failed = [item for item in results if not item[1]]
    print("Scout Runtime Acceptance Hotfix Validation")
    print("=" * 64)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {_safe_detail(detail)}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
