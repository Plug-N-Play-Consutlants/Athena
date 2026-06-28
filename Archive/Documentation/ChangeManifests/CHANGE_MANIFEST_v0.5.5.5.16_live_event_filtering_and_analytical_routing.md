# AthenaEngine v0.5.5.5.16 — Live Event Filtering and Analytical Routing Cleanup

## Purpose
Acceptance cleanup for two observed Scout issues:

1. Recent trade/event answers were selecting headlines that merely contained the word `trade`, including rumor/grades/roundup articles, instead of prioritizing confirmed transaction items.
2. Targeted team analytical prompts such as `Leafs weaknesses` could still route into a broad team profile instead of a weakness/risk-oriented analytical answer.

## Changed Files

- `Core/version.py`
- `Knowledge/Events/live_intelligence.py`
- `Scout/conversation/router.py`
- `Scout/app.py`
- `Tests/validate_scout_runtime_acceptance_hotfix.py`
- `Tests/validate_live_event_filtering_and_analytical_routing_v055516.py`
- `CHANGE_MANIFEST_v0.5.5.5.16_live_event_filtering_and_analytical_routing.md`

## Behavioral Changes

- Adds confirmed-transaction filtering for trade prompts.
- Excludes rumor, grades, report-card, roundup, mock/preview, and generic buzz articles from trade-specific event answers.
- Live-event public answers now compose readable event summaries instead of saying only that Scout consumed evidence.
- Event answers attach `source_links` for clickable/source-popup rendering.
- Scout source-link rendering now opens real URLs in a new tab when URLs are available, while retaining details popups.
- Public analytical routing now detects weakness/problem/flaw prompts.
- Team weakness prompts produce risk/support-structure analysis instead of generic team identity profiles.

## Validation

- `Tests/validate_live_event_filtering_and_analytical_routing_v055516.py` PASS
- `Tests/validate_response_composition_visibility.py` PASS
- `Tests/validate_scout_runtime_acceptance_hotfix.py` PASS
