# v0.6.5.1.3 — Scout Routing Safety & Investigation Continuity Hotfix

Status: Candidate, pending Studio/runtime verification.
Baseline: v0.6.5.1.2.

## Scope
- Reject question-shaped strings as player identities before lifecycle/news evidence can establish a player.
- Preserve rule/knowledge routing for natural-language hockey questions such as `What is icing`.
- Render actionable disambiguation cards in Normal mode; Sebastian Aho choices submit canonical resolving prompts.
- Keep follow-up prompts inside an active investigation instead of returning to unrelated news discovery.
- Preserve contextual surname comparison resolution and prior card containment/value humanization.
- Keep internal Athena mechanics out of the public disambiguation conclusion.

## Regression fixtures
- `What is icing` must not route to player profile/lifecycle and lifecycle returns `not_person_query`.
- Sebastian Aho produces at least two actionable canonical choices and Studio renders action cards in Normal mode.
- Matthews vs McKenna remains a public player comparison with Gavin McKenna assumption visible.
- Acquisition-story investigation follow-ups deepen cap/roster/bilateral/evidence scenarios.
- Scout runtime acceptance remains 41/41.
