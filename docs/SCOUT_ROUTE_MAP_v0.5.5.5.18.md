# Scout Route Map — v0.5.5.5.18

## Purpose

This audit maps the current Scout execution path so acceptance fixes are grounded in code paths rather than assumptions. The key finding is that Scout has the right major subsystems, but several public prompts were being intercepted by broad fallback routes before the canonical public intent/entity router could resolve the user’s actual question.

## Runtime Entry Path

```text
Scout/app.py
  POST /api/ask
    -> load_context()
    -> route_question(question, ctx, mode)
    -> response(...)
       -> compose_answer_payload(...)
          -> public_comment / diagnostics split
    -> _record_session_turn(...)
    -> JSON response to frontend

Scout/app.py frontend renderAnswer(...)
  public mode:
    title + public_comment + source_links
  developer mode:
    public_comment + confidence + cards + diagnostics + raw developer payload
```

## Canonical Public Routing Order

```text
route_question(..., mode="public")
  1. Empty prompt -> help_response
  2. Explicit diagnostic prompt -> _diagnostic_runtime_answer
  3. Recent/live event prompt -> _live_events_answer
  4. Fantasy/league operations that are explicit -> league handlers
  5. Public overview/help -> public_sports_overview
  6. Multi-sport routing probe -> diagnostic context only, not final answer unless required
  7. PIF public request router -> analyze_public_request
       a. disambiguate_entity -> disambiguation_answer
       b. player_comparison -> player_comparison_answer
       c. team_comparison -> team_comparison_answer
       d. player_intelligence -> player_profile_answer
       e. team_intelligence -> team_profile_answer
       f. draft/prospect/event/public gap -> public gap answer
       g. rulebook_knowledge -> public_hockey_answer
  8. Broad public analytical fallback -> _public_analytical_answer
       Used only after canonical public routing fails.
  9. Player-intelligence fallback
 10. Public hockey pack fallback
 11. No-silent-failure response
```

## Current Public Answer Surfaces

```text
Reasoning/public answer payload
  -> natural_language_response / public_comment
  -> engine_conclusion
  -> observed_facts
  -> known_limitations
  -> cards
  -> developer

compose_answer_payload(...)
  public_comment = canonical public answer
  natural_language_response = public_comment
  response_text = public_comment
  scout_message = public_comment
  diagnostics = engine_conclusion + observed_facts + known_limitations + developer
  display_contract = public_comment_only

Frontend
  public mode shows public_comment only, plus source links
  developer mode additionally shows confidence/cards/diagnostics/developer JSON
```

## Route Path Findings

### 1. Broad analytical fallback was too early

Before this cleanup, `_is_public_analytical_query(...)` ran before `analyze_public_request(...)`. A targeted prompt such as `What is the Leaf's weakness` could be captured by the broad contender-analysis fallback and return multiple teams. That was the root cause of the “why is it talking about three other teams?” behavior.

Current correction: canonical public entity/intent routing now runs before broad seeded contender fallback.

### 2. Possessive fan shorthand was not normalized consistently

`Leafs weakness` could resolve, but `Leaf's weakness` could miss the team entity because the apostrophe variant was not normalized everywhere. The miss then cascaded into broad public analytical fallback.

Current correction: public routing normalizes `leaf's`, `Leaf’s`, and `maple leaf's` to `leafs` / `maple leafs` before entity resolution.

### 3. Team weakness was treated as a generic team profile

The team profile composer had risk information, but the answer started from identity/history and then eventually mentioned risks. For targeted questions, the answer should lead with the asked dimension.

Current correction: targeted weakness prompts now route to a team profile answer titled `Toronto Maple Leafs weakness analysis` and lead with the specific weakness/risk read.

### 4. Live event path is functional but still limited by source shape

`_live_events_answer(...)` can select live/cached RSS evidence and attach `source_links`. The event selector now filters out obvious rumour/grades/roundup items for trade prompts. The remaining limitation is that RSS headlines are not the same as a structured transaction feed. Exact assets, dates, teams, cap impact, and official transaction confirmation still require a structured transaction source.

### 5. Draft questions are correctly conservative but need richer future source integration

Draft/prospect prompts route to a public gap answer instead of hallucinating. That is correct until draft-board, pick-order, prospect-ranking, and team-pick feeds are attached. The public answer should explain the evidence gap without exposing route names or implementation terms.

## Remaining Gaps

1. Analytical depth is still constrained by seed profiles for many teams.
2. Draft intelligence is a source gap, not just a composition gap.
3. Live event intelligence needs structured event normalization beyond RSS headline parsing.
4. Team-specific analytical sub-intents should continue to be expanded: weakness, strength, draft outlook, trade needs, offseason evaluation, cap risk, coaching/system fit.
5. Public answer quality should be evaluated using real Scout transcripts, not only validators.

## Acceptance Principle

Before adding new architecture, Scout should preserve this ordering:

```text
specific entity + specific analytical intent
  beats
broad public contender/ranking fallback
```

A targeted question about one team should never return a multi-team ranking unless the user explicitly asks for rankings or comparisons.
