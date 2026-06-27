# Evidence Path Audit — v0.5.5.5.19

## Purpose

This document is the first traceability audit for AthenaEngine Epic 5A acceptance work. It maps how Scout currently moves from a user prompt to evidence, reasoning, composition, and display. The intent is to stop patching isolated symptoms and make future fixes evidence-driven.

This is an audit artifact, not a new intelligence feature. It identifies what is actually wired today, what is only validated in isolation, what is duplicated, and where evidence is dropped before it reaches the final Scout answer.

## Current repository inventory

As of this build snapshot:

```text
Total files:        1,056
Python files:         571
Python LOC:        63,875
```

Top-level concentration:

```text
Reports:            141 files
Tests:              132 files
Knowledge:          114 files
Tools:               96 files
Archive:             90 files
Output:              76 files
Reasoning:           61 files
Providers:           43 files
docs:                38 files
Engine:              33 files
Intelligence:         27 files
Scout:               12 files
Athena package:       13 files
Core:                 9 files
```

Interpretation:

- The repository is not “over one thousand runtime files.” A large share is reports, tests, archived history, output data, manifests, and tooling.
- The runtime surface is still too broad. The main logical overlap is between `Engine/`, `Intelligence/`, `Reasoning/`, `Knowledge/Intelligence`, and `Scout/conversation`.
- The current acceptance issue is not simply file count. It is path clarity: several subsystems exist and validate, but not all of them are on the live Scout answer path.

## Current program shape

```text
AthenaEngine/
  Tools/                 Studio, doctors, validators, maintenance scripts
  Scout/                 Flask app, frontend, conversation router/composer
  Athena/                canonical public API/orchestrator package
  Core/                  version/logging/runtime metadata
  Providers/             Fantrax/NHL/Yahoo/ESPN provider adapters/builders
  Knowledge/             generated knowledge, public profiles, events, identity, graph
  Intelligence/          newer explainability/runtime/cross-sport/foundation layers
  Reasoning/             public/team/player/comparison/composition reasoners
  Engine/                event/cross-domain/multi-sport engine families
  Output/Raw/Reports/    generated or runtime data
  Archive/               retired historical materials
  Tests/                 validation suite
  docs/                  engineering documents and product docs
```

Current structural concern:

```text
Scout/conversation/router.py
  still owns too much decision logic.

Knowledge/Intelligence/Routing/request_router.py
  owns public PIF intent/entity routing.

Knowledge/Intelligence/Routing/multi_sport_router.py
  owns sport-aware route metadata.

Intelligence/Runtime/orchestrator.py
  can build a runtime trace, but Scout mostly uses it for diagnostics.

Engine/EventSummarization, EventConfidence, EventTimeline, CrossDomain
  validate independently, but are not consistently consumed by public Scout answers.
```

## Actual prompt-to-answer path

### Runtime entry

```text
Scout/app.py
  POST /api/ask
    -> load_context()
    -> route_question(question, ctx, mode)
    -> compose_answer_payload(answer)
    -> _record_session_turn(...)
    -> JSON response

Scout frontend
  renderAnswer(...)
    public mode: public_comment + source links
    developer mode: public_comment + cards/confidence/diagnostics/developer payload
```

### Current public routing order

```text
route_question(..., mode="public")
  1. Empty prompt / help
  2. Explicit runtime diagnostic prompt
  3. Recent/live event prompt
  4. Explicit fantasy/league operation prompt
  5. Public overview/help prompt
  6. Multi-sport route probe, primarily diagnostic metadata
  7. PIF public request router: analyze_public_request(...)
       - disambiguation
       - player comparison
       - team comparison
       - player profile
       - team profile
       - draft/prospect/event gap
       - rulebook/public hockey pack
  8. Broad public analytical fallback
  9. Player-intelligence fallback
 10. Public hockey retrieval fallback
 11. Clarify/no-silent-failure response
```

Acceptance rule confirmed by this audit:

```text
Specific entity + specific analytical intent must beat broad fallback.
```

A targeted team question must never become a league-wide ranking unless the user explicitly asks for a ranking/comparison.

## Evidence path matrix

| User prompt family | Current route | Evidence actually used | Evidence not reliably used | Main gap |
|---|---|---|---|---|
| Public player profile | `analyze_public_request` -> `player_profile_answer` | public entity registry, seeded public player profile, selected profile facts | live events, official current stats, historical/trend modules, runtime trace evidence | Profile answers are composed from limited seeded profile evidence. |
| Public team profile | `analyze_public_request` -> `team_profile_answer` | public team seed profile, team reasoning seed, profile risks/strengths | live roster, cap, injuries, current standings, recent transactions | Team answers can frame identity but not current-state quality. |
| Targeted team weakness | PIF/team profile or analytical fallback depending entity match | seeded team risks, analytical read, roster context | current performance data, cap, injuries, lineup/deployment, goalie/defense metrics | Targeted weakness is now routed better but still evidence-light. |
| Broad contender/chances | `_public_analytical_answer` | seeded public team profiles and deterministic seed score | standings, odds/consensus, current team metrics, injuries | This is a bounded profile ranking, not true live contender analysis. |
| Recent trades/events | `_live_events_answer` before PIF | RSS/live event selector, configured feeds, source links when present | EventSummarization, EventConfidence, EventTimeline, CrossDomain propagation, official transaction feed | RSS headline/event selection is not enough for structured trade analysis. |
| Draft/prospect | `draft_intelligence_gap` / `prospect_intelligence_gap` | route classification and conservative public gap language | pick inventory, prospect rankings, team draft board, official draft order | The source path is missing, not just the wording. |
| Fantasy league analysis | Scout deterministic league handlers | Output JSON files: league, team profiles, player master, transactions, market, manager behavior | some newer public/cross-sport runtime layers | Fantasy path is separate and older but functional. |
| Runtime diagnostics | `_diagnostic_runtime_answer` -> `run_runtime_trace` | multi-sport router, explainability, cross-sport reasoning, evidence ledger | final public answer path | Strong trace tooling exists, but it is diagnostic rather than canonical answer assembly. |

## Public player profile path

```text
Question: "Tell me about Auston Matthews"

Scout/app.py
  -> route_question(..., public)
  -> analyze_public_request(question)
  -> entity resolution
  -> route = player_intelligence / public_player_profile
  -> public_player_profiles seed
  -> public_answers.player_profile_answer(...)
  -> Scout response(...)
  -> compose_answer_payload(...)
  -> frontend render
```

Current strength:

- Entity resolution and public/fantasy separation are substantially improved.
- Public language is no longer dominated by internal diagnostics.

Current evidence weakness:

- The answer mostly uses seed profile fields and selected cards/facts.
- Current live events, official current-season stats, historical trend modules, injury/deployment context, and international achievement evidence are not consistently queried before composition.

Required next fix type:

```text
Evidence Request Contract for player_profile:
  identity
  biography
  achievements
  current production
  multi-year trend
  injuries/availability
  role/deployment
  recent events
  fantasy lens only when requested
```

## Public team analysis path

```text
Question: "What is the Leafs weakness?"

Scout/app.py
  -> route_question(..., public)
  -> normalize public query text
  -> analyze_public_request(...)
  -> team entity resolution
  -> route = team_intelligence / public_team_profile
  -> public_team_profiles seed
  -> public_answers.team_profile_answer(...)
  -> team_reasoning_engine seed assessment
  -> compose_answer_payload(...)
```

Current strength:

- Entity shorthand such as `Leafs` / `Leaf's` is now better normalized.
- A single-team question no longer intentionally falls to broad contender ranking when entity resolution succeeds.

Current evidence weakness:

- `team_profile_answer` and `_public_analytical_answer` still depend on seed profiles.
- Team weakness answers can name risks but cannot support them with current data.
- The answer does not yet ask for or receive an evidence bundle covering current roster construction, team statistics, deployment, injuries, cap, goalie/defense performance, or recent transaction context.

Required next fix type:

```text
Evidence Request Contract for team_weakness:
  team identity
  roster/core
  current standings/team stats
  defense/goaltending metrics
  injuries
  cap constraints
  recent trades/signings
  historical playoff pattern
  explicit risk synthesis
```

## Live event/trade path

```text
Question: "Tell me about this week's trades"

route_question(...)
  -> live/recent event detector
  -> _live_events_answer(...)
  -> Knowledge.Events.live_intelligence
  -> RSS feed selection/filtering
  -> Scout response with source_links if URL exists
  -> compose_answer_payload(...)
```

Current strength:

- The live path is no longer random; it selects event-like evidence from configured feeds.
- Trade prompts now filter out obvious rumor/grades/roundup/mock items more aggressively.

Current evidence weakness:

- RSS articles are not normalized transaction records.
- A headline containing a trade is not the same as a structured trade object.
- EventConfidence, EventTimeline, EventSummarization, and CrossDomain impact engines exist and validate but are not consistently part of the Scout event answer path.

Observed underuse:

```text
Engine/EventSummarization
Engine/EventConfidence
Engine/EventTimeline
Engine/CrossDomain
```

These modules are validated by tests/doctors but are not the default public event-answer pipeline in Scout.

Required next fix type:

```text
Event Answer Contract:
  event discovery
  event type classification
  source profile/confidence
  structured event extraction
  date normalization
  entity linking
  duplicate/corroboration check
  event summary
  public source links
```

## Draft/prospect path

```text
Question: "Leafs upcoming draft"

route_question(...)
  -> analyze_public_request(...)
  -> draft_intelligence_gap
  -> public_answers.gap_answer(...)
  -> compose_answer_payload(...)
```

Current strength:

- Athena no longer hallucinates draft targets.
- It now frames the missing evidence as an analyst would, rather than saying “knowledge pack needed.”

Current evidence weakness:

- No current pick inventory path.
- No official draft order path.
- No prospect ranking path.
- No team draft-board or public prospect evidence path.
- Existing `Raw/draft_results.json` and `Raw/draft_picks.json` are expected but absent in the current debug exports.

Required next fix type:

```text
Draft Evidence Contract:
  team pick inventory
  draft order
  prospects/rankings
  team needs
  traded-pick context
  recent draft-related events
  confidence/source summary
```

## Runtime orchestration path

```text
Diagnostic prompt
  -> _diagnostic_runtime_answer(...)
  -> Intelligence.Runtime.run_runtime_trace(...)
       routing
       live_intelligence
       explainability_pipeline
       cross_sport_reasoning
       response_assembly
```

Current strength:

- The runtime trace is the closest existing implementation to the Evidence Path Audit concept.
- It produces stage names, evidence ledger, confidence, and reasoning metadata.

Current integration gap:

- The runtime trace is used mainly for diagnostics, not as the canonical public answer assembly path.
- This means strong cross-sport/explainability evidence can exist without influencing the public answer.

Required next fix type:

```text
Scout should either:
  A. promote runtime orchestration to the canonical answer pipeline, or
  B. use the same evidence ledger contract inside existing public routes.

Do not add another parallel pipeline until this decision is made.
```

## Redundancy and consolidation findings

### Runtime-data bloat

`Reports/`, `Output/`, `Raw/`, and `Logs/` contain generated or runtime data. Some of this is useful for local development, but long-term program structure should separate runtime artifacts from source code.

Recommendation:

```text
Keep in repo only fixtures and intentional samples.
Move runtime exports/logs/reports to a local workspace path or gitignored data directory.
```

### Archive bloat

`Archive/` preserves useful historical context but should not be part of the active runtime tree forever.

Recommendation:

```text
Move release history and retired code into docs/history or an external archive package.
Keep active source tree small.
```

### Root-level compatibility files

Most root-level Python files are now shims to `Athena/`, which is good. The root package metadata was stale and should remain tied to `Core.version` so it cannot drift again.

Recommendation:

```text
Root-level modules should be launchers or compatibility shims only.
No business logic should live at repository root.
```

### Naming overlap

Repeated names like `models.py` and `registry.py` are acceptable inside packages, but the conceptual overlap is not yet clean:

```text
Engine/EventReasoning
Engine/EventSummarization
Engine/EventConfidence
Intelligence/Reasoning
Reasoning/team_reasoning_engine.py
Reasoning/comparison_reasoning_engine.py
Knowledge/Intelligence/Public/public_answers.py
Scout/conversation/router.py
```

Recommendation:

```text
Do not delete yet.
First decide the canonical responsibilities:
  Knowledge = facts and normalized records
  Evidence = source-backed bundles
  Reasoning = domain analysis
  Composition = public/developer answer shaping
  Scout = UI/runtime adapter only
```

## Primary gaps identified

1. **No canonical Evidence Request Contract.** Routes call answer builders directly instead of requesting a typed evidence bundle first.
2. **Runtime orchestration is diagnostic, not canonical.** The best traceability mechanism exists but does not consistently drive public answers.
3. **Event intelligence modules are underused.** Live Scout event answers use RSS selection but not the validated event summarization/confidence/timeline/cross-domain stack.
4. **Team/player public answers are seed-heavy.** They are cleaner but not yet evidence-rich.
5. **Draft/prospect intelligence is a true source gap.** The conservative answer is correct, but the path needs pick/prospect feeds.
6. **Scout router owns too much.** `Scout/conversation/router.py` combines routing, fallback selection, some analysis, and operational answers.
7. **Generated artifacts are mixed with source.** Reports/output/archive inflate the repository and obscure the actual program structure.

## Recommended next engineering sequence

### Step 1 — Freeze new intelligence modules

No new major intelligence subsystem until these existing paths are connected or consciously retired.

### Step 2 — Define Evidence Request Contracts

Create typed contracts for:

```text
player_profile
player_current_form
player_legacy
team_profile
team_weakness
team_draft_outlook
recent_trades
draft_projection
fantasy_trade
league_market
```

Each contract should specify:

```text
required evidence
optional evidence
source priority
fallback behavior
public answer shape
developer diagnostics
```

### Step 3 — Wire one vertical slice fully

Do not fix all routes at once. Pick one acceptance prompt and trace it end-to-end.

Recommended first slice:

```text
What is the Leafs weakness?
```

Why this one:

- Entity resolution is known.
- Team seed profile exists.
- Current answer is contextually improved but analytically thin.
- It exposes whether current team stats, roster, events, and historical patterns can reach composition.

### Step 4 — Promote or reuse runtime trace

Choose one:

```text
A. make Intelligence.Runtime the canonical evidence/reasoning pipeline for Scout, or
B. extract its evidence ledger concept into the existing PIF/public routes.
```

Avoid a third parallel system.

### Step 5 — Program structure cleanup

Only after the evidence paths are documented and one vertical slice is proven:

```text
src/athena_engine/
  apps/
    studio/
    scout/
  core/
  providers/
  knowledge/
  evidence/
  reasoning/
  composition/
  runtime/
  ops/
  tests/
  docs/
```

Keep generated data outside active source:

```text
workspace/
  raw/
  output/
  reports/
  logs/
```

## Acceptance gates for future patches

A future acceptance patch should not be considered complete unless it answers these questions:

1. What route did the prompt take?
2. What evidence bundle was requested?
3. Which source families contributed evidence?
4. Which evidence was available but unused?
5. Which fallback was triggered, if any?
6. Did the public answer use only the public surface?
7. Did developer diagnostics preserve the full trace?

## Immediate conclusion

Athena does not primarily need another part yet. It needs a canonical evidence path. The existing system already contains much of the needed machinery, but too much of it is either diagnostic-only, seed-only, or bypassed by older Scout paths. The next engineering work should make one analytical vertical slice prove the full path before any larger reorganization.
