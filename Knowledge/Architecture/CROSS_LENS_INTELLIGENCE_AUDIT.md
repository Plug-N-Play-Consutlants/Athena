# Cross-lens intelligence audit — v0.7.10.0.42

## Principle
Fantasy and Professional are interpretive lenses over the same Athena evidence and reasoning capabilities. A mode must never be treated as an authorization boundary for player, team, historical, prospect, contract, transaction, or statistical intelligence. Relevant capabilities should be selected by inquiry semantics; not every module needs to execute on every question.

## Source-observed boundaries
- `Scout/conversation/router.py:route_question` dispatches some league/recap requests before mode-specific branches. Explicit JHLPAA/Fantrax requests are eligible regardless of mode. This is desirable.
- Public NHL semantics can override stale fantasy UI mode. This prevents contamination but is not a shared orchestrator; it currently changes the selected mode.
- Player profiles and comparisons are dispatched through `analyze_public_request` in a `selected_mode == "public"` block. This remains a mode-bound capability path and requires careful refactoring, not removal of working handlers.
- Team current-season evaluation is intercepted by `_is_team_performance_inquiry` and yields an explicit evidence-gap response. This prevents false claims but bypasses existing NHL evidence and remains incomplete.
- JHLPAA weekly reports use authenticated league evidence, but player-period production remains unverified until request attribution, parsing and pagination are resolved.
- Award history and predictive award outcomes are separate capabilities. Predictive awards are not an accepted regression requirement.

## Balanced acceptance matrix (manual Studio prompts)
1. Professional: `Auston Matthews` — current player profile and provenance; no regression in card/season history.
2. Professional: `Auston Matthews vs McDavid` — quantitative and contextual comparison with a conclusion.
3. Professional: `How are the Toronto Maple Leafs looking so far this season? What's working, what isn't, which players are making a difference, and what should management be thinking about going forward?` — no static identity substitution; substantive analysis still pending.
4. Fantasy: `What's happening around the JHLPAA this week?` — standings, transactions and temporal evidence gates.
5. Fantasy: `Auston Matthews vs McDavid` — preserve player-comparison intelligence and apply league scoring only when supported; test for unwanted generic fantasy fallback.
6. Professional: `What can you tell me about the JHLPAA draft over the last 10 seasons?` — explicit league scope should not be suppressed by mode.

## Scope and disposition
This build adds durable cross-lens acceptance sentinels and a source-grounded audit, not a new orchestrator. Existing behavior is intentionally preserved. The next functional pass should address the verified Fantrax period contract and shared module selection without replacing established player/comparison routes. Do not count missing predictive award reasoning as a regression.
