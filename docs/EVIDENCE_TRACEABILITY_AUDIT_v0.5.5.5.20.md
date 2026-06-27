# Evidence Traceability Audit — v0.5.5.5.20

## Purpose

This checkpoint continues Epic 5A as an audit-first pass. It does **not** add a new intelligence module. The objective is to trace how the current Scout runtime actually moves a user question into evidence, reasoning, composition, rendering, diagnostics, and logs before we consolidate or restructure the program.

The acceptance lesson from v0.5.5.5.15 through v0.5.5.5.19 is clear: many Scout failures are not caused by missing UI polish. They are caused by evidence not being requested, evidence not being transformed into the correct shape, or a broad route intercepting a specific analytical question.

## Current repository inventory

Measured against the uploaded v0.5.5.5.19 snapshot:

```text
Total files:        922
Python files:       573
Python LOC:      ~63,875
Root manifests:     110
Root README files:   12+
Python cache files:   2
```

Top-level concentration:

```text
Root files:      146
Tests:           133
Knowledge:       114
Tools:            98
Archive:          90
Output:           76
Reasoning:        61
Providers:        43
docs:             40
Engine:           33
Intelligence:     27
Athena:           13
Scout:            13
```

Interpretation:

- The repository is noisy, but the file count alone is not the core issue.
- A large share of the count comes from tests, release manifests, archive material, generated output, and operational tooling.
- The functional risk is conceptual overlap between `Scout/conversation`, `Knowledge/Intelligence`, `Knowledge/Events`, `Reasoning`, `Engine`, and `Intelligence`.
- Structural cleanup should follow route traceability, not precede it.

## Actual Scout path under audit

The current high-level runtime path is:

```text
Scout/app.py
  POST /api/ask
    -> load_context(...)
    -> route_question(...)
       -> local Scout handlers
       -> public request router
       -> live event answer path
       -> analytical fallback
       -> gap/failure answer
    -> response(...)
    -> compose/normalize public surface
    -> _record_session_turn(...)
    -> frontend renderAnswer(...)
```

The current public-intelligence path is:

```text
Scout/conversation/router.py
  route_question(...)
    -> Knowledge.Intelligence.Routing.request_router.analyze_public_request(...)
       -> Knowledge.Intelligence.Intent.intent_classifier.classify_intent(...)
       -> Knowledge.Intelligence.Entities.entity_extractor.extract_entities(...)
       -> PublicRoute
    -> Knowledge.Intelligence.Public.public_answers
       -> player_profile_answer(...)
       -> team_profile_answer(...)
       -> player_comparison_answer(...)
       -> team_comparison_answer(...)
       -> gap_answer(...)
```

The current live-event path is:

```text
Scout/conversation/router.py
  _live_events_answer(...)
    -> Knowledge.Events.live_intelligence.live_events_for_question(...)
       -> Knowledge.Events.live_sources.acquire_live_rss_events(...)
       -> event keyword/type filtering
    -> _compose_live_event_narrative(...)
    -> response(...)
```

The current diagnostics/runtime-observability path is:

```text
Scout/conversation/router.py
  _diagnostic_runtime_answer(...)
    -> Intelligence.Runtime.orchestrator.run_runtime_trace(...)
       -> routing
       -> live_intelligence
       -> explainability_pipeline
       -> cross_sport_reasoning
       -> response_assembly
    -> response(...)
```

## Current evidence contract gap

Athena has a lot of evidence-producing subsystems, but public Scout answers do not yet move all of that evidence through a single typed contract.

The required contract for a traceable public answer is:

```text
User Question
Intent
Entity
Question Focus
Evidence Requested
Evidence Available
Evidence Retrieved
Evidence Discarded
Reasoning Applied
Confidence Inputs
Composition Inputs
Public Answer
Diagnostics
```

The missing fields in current behavior are usually:

- `Question Focus`
- `Evidence Requested`
- `Evidence Available but Unused`
- `Evidence Discarded`
- `Reasoning Opportunity Missed`

These fields are exactly what would explain why a good subsystem exists but does not affect the final Scout answer.

## Prompt trace templates

### 1. Public team overview

Example:

```text
Who are the Maple Leafs?
```

Current route:

```text
public_team_profile
```

Current path:

```text
Scout/app.py:/api/ask
Scout.conversation.router.route_question
Knowledge.Intelligence.Routing.analyze_public_request
Knowledge.Intelligence.Public.team_profile_answer
Reasoning.team_reasoning_engine.assess_public_team
Knowledge.Intelligence.Public._compose_public_team_copy
Scout frontend renderAnswer
```

Current known gap:

- The path reaches the right team and avoids fantasy/rulebook leakage.
- The answer still depends mostly on seed profile fields.
- Live roster/cap/event/context evidence is not attached to the public team packet.
- The narrative is coherent but generic.

### 2. Targeted team weakness

Example:

```text
What is the Leafs weakness?
```

Expected route:

```text
public_team_profile + targeted risk lens
```

Current path:

```text
Scout.conversation.router.route_question
Knowledge.Intelligence.Routing.analyze_public_request
Knowledge.Intelligence.Public.team_profile_answer
Knowledge.Intelligence.Public._compose_public_team_copy
```

Current known gap:

- This should not fall into contender ranking.
- The route now resolves better, but targeted sub-intent is not a first-class typed route.
- The answer depends on seed risk fields rather than a true weakness evidence packet.
- The correct next vertical slice is to make `question_focus=weakness_analysis` explicit and traceable.

### 3. Team draft question

Example:

```text
Leafs upcoming draft
```

Current route:

```text
draft_intelligence_gap
```

Current path:

```text
Scout.conversation.router.route_question
Knowledge.Intelligence.Routing.analyze_public_request
Knowledge.Intelligence.Public.gap_answer
```

Current known gap:

- Public wording improved, but the engine does not have a verified pick/prospect/draft-board feed attached.
- It can frame what would matter but cannot evaluate actual draft inventory.
- This is a data-path gap, not a renderer problem.

### 4. Recent trade events

Example:

```text
Tell me about this week's trades
```

Current route:

```text
live_event_intelligence
```

Current path:

```text
Scout.conversation.router._live_events_answer
Knowledge.Events.live_intelligence.live_events_for_question
Knowledge.Events.live_sources.acquire_live_rss_events
Scout.conversation.router._compose_live_event_narrative
```

Current known gap:

- RSS acquisition works.
- Trade filtering improved.
- The path still lacks normalized transaction objects with structured teams, assets, pick numbers, dates, and source URLs as first-class output fields.
- The answer can summarize event items, but it cannot yet behave like a transaction ledger.

### 5. Public player profile

Example:

```text
Tell me about Auston Matthews
```

Current route:

```text
public_player_profile
```

Current path:

```text
Scout.conversation.router.route_question
Knowledge.Intelligence.Routing.analyze_public_request
Knowledge.Intelligence.Public.player_profile_answer
Knowledge.Intelligence.Public._compose_public_player_copy
```

Current known gap:

- Player answers are materially better than early Scout builds.
- Career achievements and style descriptors can appear from seed context.
- Verified live public achievements, recent injuries, international events, and external citations are not consistently attached to the evidence packet.
- Historical Intelligence exists but its public-profile contribution is inconsistent.

## Evidence Available but Unused — suspected areas

These are not deletion candidates yet. They are traceability targets.

| Area | Suspicion | Audit action |
|---|---|---|
| Historical Intelligence | Validates independently but is not always requested by public profile answers | Trace whether player/team public answers request historical records |
| Event Intelligence | Produces items but public answers often use only title/summary | Trace whether events become structured evidence or remain headlines |
| Confidence | Often assigned after routing rather than changing answer strategy | Trace confidence inputs and downstream effects |
| Runtime Orchestration | Observes paths but is not the active answer pipeline | Decide whether it remains diagnostics-only or becomes canonical orchestration |
| Team Reasoning | Produces sections, but composition can still fall back to seed copy | Trace which fields are used in public answer text |
| Public gap answers | Now user-facing but still terminate instead of requesting alternate evidence | Trace whether gaps can be transformed into scoped partial analyses |

## Route priorities that must be preserved

1. Explicit diagnostics must stay developer/diagnostic-only.
2. Live-event prompts should use live/event paths before generic public profile routes.
3. Canonical public entity routing should run before broad analytical fallback.
4. Targeted team questions must not become multi-team rankings.
5. Fantasy context must only be used when fantasy/league context is explicit.
6. Draft/prospect questions must not hallucinate if verified draft evidence is missing.
7. Public answers must not expose route names, modules, build numbers, or knowledge-pack language.

## First vertical slice to trace next

Target prompt:

```text
What is the Leafs weakness?
```

Reason:

- It is narrow enough to trace completely.
- It exercises entity resolution, targeted analytical intent, team evidence, reasoning, composition, and rendering.
- It exposes whether Athena can answer the *actual question* instead of the closest profile template.

Required trace fields:

```text
intent
entity
question_focus
evidence_requested
evidence_available
evidence_retrieved
evidence_discarded
reasoning_outputs
composition_inputs
public_answer
diagnostics
```

Acceptance condition:

Athena should answer only about Toronto's weaknesses, not list contender teams, not print implementation details, and not merely dump seed fields. If evidence is missing, the answer should explain the uncertainty in analyst language and still provide the best bounded analysis from verified local evidence.

## Do not reorganize yet

This is the reorg guardrail: document actual path behavior before moving code.

## No-reorganization rule

Do not move `Engine/`, `Intelligence/`, `Reasoning/`, `Knowledge/Intelligence`, or `Scout/conversation` yet.

The next safe step is not folder movement. It is one fully traced vertical slice with a typed evidence packet. Once that passes, consolidation can begin with evidence instead of assumptions.
