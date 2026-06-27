"""Doctor for v0.5.5.5.x Scout runtime acceptance and Studio log visibility hotfixes."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("ATHENA_SCOUT_LIVE_NETWORK", "0")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    return name, bool(condition), detail


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        from Core.version import ATHENA_VERSION, RELEASE_NAME
        checks.append(check("hotfix_version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 5, 5, 5, 1), ATHENA_VERSION))
        checks.append(check("release_name", RELEASE_NAME in {"Scout Runtime Acceptance Hotfix", "Studio Log Visibility Hotfix", "Scout Runtime Continuation Hotfix", "Scout Session Logging Hotfix", "Scout Acceptance Communication Hotfix", "Public Analytical Routing Hotfix", "Response Composition Visibility Hotfix", "Acceptance Repository Cleanup and Pathway Audit", "Diagnostics Log Export Restoration"}, RELEASE_NAME))
    except Exception as exc:
        checks.append(check("version_import", False, str(exc)))
    for rel in [
        "Knowledge/Events/live_intelligence.py",
        "Scout/conversation/router.py",
        "Scout/app.py",
        "Tests/validate_scout_runtime_acceptance_hotfix.py",
    ]:
        checks.append(check(f"required_file:{rel}", (ROOT / rel).exists(), rel))
    try:
        from Knowledge.Events.live_intelligence import live_intelligence_diagnostics, select_live_evidence
        diag = live_intelligence_diagnostics()
        checks.append(check("live_diag_pass_or_warn", diag.get("status") in {"pass", "warn"}, str(diag)))
        evidence = select_live_evidence("What recent NHL events are available?")
        checks.append(check("live_feeds_visible", int(evidence.get("feed_count") or 0) >= 1, str(evidence)))
        checks.append(check("live_events_selected", int(evidence.get("selected_count") or 0) >= 1, str(evidence)))
    except Exception as exc:
        checks.append(check("live_intelligence", False, f"{type(exc).__name__}: {exc}"))
    try:
        from Athena.capabilities import assess_capabilities
        report = assess_capabilities()
        caps = {cap.get("key"): cap for cap in report.get("capabilities", []) if isinstance(cap, dict)}
        checks.append(check("capability_dashboard_has_live_event_sources", "live_event_sources" in caps, str(caps.get("live_event_sources"))))
        checks.append(check("live_event_sources_available", caps.get("live_event_sources", {}).get("status") == "available", str(caps.get("live_event_sources"))))
    except Exception as exc:
        checks.append(check("capability_dashboard", False, f"{type(exc).__name__}: {exc}"))
    try:
        from Scout.conversation.router import route_question
        diag_answer = route_question("What intelligence modules executed?", mode="public")
        leafs_answer = route_question("who are the Maple Leafs", mode="public")
        live_answer = route_question("What recent NHL events are available?", mode="public")
        contender_answer = route_question("Who are the best Stanley Cup contenders right now, and why?", mode="public")
        strongest_answer = route_question("Which NHL teams are strongest right now?", mode="public")
        oilers_contender = route_question("Why are the Oilers contenders?", mode="public")

        leafs_trade = route_question("Maple leafs last trade", mode="public")
        leafs_trade_text = str(leafs_trade.get("natural_language_response", "")) + " " + str(leafs_trade.get("observed_facts", []))
        checks.append(check("leafs_trade_no_unrelated_canadiens", "Canadiens acquire defenseman" not in leafs_trade_text, str(leafs_trade)))
        checks.append(check("leafs_trade_no_match_message", "do not have a confirmed" in str(leafs_trade.get("natural_language_response", "")).lower() or "do not have a matching" in str(leafs_trade.get("natural_language_response", "")).lower() or leafs_trade.get("confidence", 1) < 0.6, str(leafs_trade)))

        help_answer = route_question("", mode="public")
        checks.append(check("diagnostic_prompt_routes", diag_answer.get("intent") == "scout_runtime_diagnostics", str(diag_answer)))
        checks.append(check("team_prompt_continues_past_routing", leafs_answer.get("intent") == "public_team_profile" and leafs_answer.get("title") != "Multi-Sport Scout Routing", str(leafs_answer)))

        aho = route_question("Who is Sebastian Aho?", mode="public")
        aho_text = str(aho.get("natural_language_response", "")) + " " + str(aho.get("observed_facts", []))
        checks.append(check("sebastian_aho_disambiguates", aho.get("intent") == "public_entity_disambiguation", str(aho)))
        checks.append(check("sebastian_aho_profiles_candidates", "Carolina" in aho_text and "Swedish" in aho_text, aho_text))
        leafs_team_text = str(leafs_answer.get("natural_language_response", "")) + " " + str(leafs_answer.get("observed_facts", []))
        checks.append(check("team_answer_contains_history", "1917" in leafs_team_text and "Stanley Cups" in leafs_team_text, leafs_team_text))
        checks.append(check("team_answer_not_meta_presentation", "should be read" not in leafs_team_text.lower() and "should be evaluated" not in leafs_team_text.lower(), leafs_team_text))
        checks.append(check("recent_event_prompt_routes", live_answer.get("intent") == "live_event_intelligence", str(live_answer)))
        checks.append(check("recent_event_has_content", bool(live_answer.get("observed_facts")), str(live_answer.get("observed_facts"))))
        checks.append(check("public_contender_routes", contender_answer.get("intent") == "public_analytical_route", str(contender_answer)))
        checks.append(check("public_contender_not_clarify", contender_answer.get("title") != "Scout needs one more detail", str(contender_answer)))
        checks.append(check("public_strongest_routes", strongest_answer.get("intent") == "public_analytical_route", str(strongest_answer)))
        checks.append(check("public_oilers_contender_routes", oilers_contender.get("intent") == "public_analytical_route" and "Oilers" in str(oilers_contender.get("natural_language_response", "")), str(oilers_contender)))
        cards = help_answer.get("cards") or []
        checks.append(check("option_cards_have_prompts", bool(cards) and all(isinstance(c, dict) and c.get("prompt") for c in cards), str(cards)))
    except Exception as exc:
        checks.append(check("scout_routes", False, f"{type(exc).__name__}: {exc}"))
    scout_app = (ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    checks.append(check("ui_implied_try_cards_clickable", "impliedPrompt" in scout_app and "askCardPrompt" in scout_app, "Scout/app.py"))
    checks.append(check("public_status_uses_live_sources", "live_sources.py" in scout_app and "live_intelligence" in scout_app, "Scout/app.py"))
    checks.append(check("session_log_ui_present", "sessionLogBtn" in scout_app and "/api/session/export" in scout_app and "bindButton('sessionLogBtn', exportSessionLog)" in scout_app, "Scout/app.py"))
    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    checks.append(check("studio_log_viewer_window", "def _open_text_window" in studio and "Latest Debug" in studio, "Tools/athena_studio.py"))
    checks.append(check("studio_subprocess_utf8", "PYTHONIOENCODING" in studio and "errors=\"replace\"" in studio, "Tools/athena_studio.py"))

    failed = [item for item in checks if not item[1]]
    print("Scout Runtime Acceptance Hotfix Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
