# v0.7.7.0.0 — Inquiry Utilization & Adaptive Evidence

## Objective
Establish one shared inquiry-state contract used by professional and fantasy paths so Athena preserves user scope and constraints through routing and execution.

## Changed / new files
- `Core/version.py`
- `Athena/Inquiry/__init__.py`
- `Athena/Inquiry/state.py`
- `Athena/intent_planner.py`
- `Athena/capability_handlers.py`
- `Scout/conversation/router.py`
- `Tests/validate_inquiry_utilization_adaptive_evidence.py`
- `Tests/validate_organizational_environment_plausibility.py`

## Acceptance targets
- Preserve multiple named subjects while selecting the actual transaction subject.
- Preserve protected assets such as "without Matthews".
- Treat explicit salary-cap waivers as analytical-frame changes that outrank cap routing.
- Normalize explicit temporal windows including last week, last N seasons, career and opening-career windows.
- Expose evidence requirements for time-scoped fantasy summaries, including standings.
- Reconcile fantasy active/quiet teams by stable team identity or normalized team name.
- Do not silently satisfy a requested statistical window with a shorter default window.

## Deliberately deferred
- Finished Fantasy League Pulse presentation.
- Standings acquisition/history and movement/race detection.
- Full free-agent movers/shakers and trade-target intelligence.
- Full constructive multi-party transaction graph.
- Persistent investigation/evidence evolution (0.7.8 target).
