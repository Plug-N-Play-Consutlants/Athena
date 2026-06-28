# Athena v0.5.0-drop4c3 Change Manifest

## Sprint
Epic 4C.3 — Reasoning Engine

## Summary
Adds a graph reasoning layer above the canonical context graph and evidence-chain engine. The reasoning engine ranks connected evidence paths by relevance for a requested context profile and focus, enabling Scout and Intelligence consumers to ask which graph evidence matters most rather than merely walking all connected evidence.

## Added
- `Knowledge/Graph/reasoning_engine.py`
  - `build_reasoning_package(...)`
  - `write_reasoning_report(...)`
  - Context profile traversal preferences for Fantasy, Public, Projection, and Odds.
  - Focus hints for contract, keeper, team, roster, fantasy value, rules, schedule, coach, achievement, and public context.
  - Weighted, breadth-first, and depth-first ranking modes.
  - Relevance scoring and normalized confidence.
  - Known gap reporting when requested focus lacks direct graph evidence.
- `Tools/doctor_reasoning_engine.py`
- `Tests/validate_reasoning_engine.py`
- Scout developer API endpoint:
  - `/api/graph/reasoning?entity_id=<id>&context_profile=fantasy&focus=contract,team&max_depth=3&traversal=weighted`

## Modified
- `Knowledge/Graph/__init__.py` exports reasoning engine APIs.
- `Scout/app.py` imports reasoning package builder, exposes reasoning endpoint, and updates visible Scout build label.
- `Core/version.py` advances Athena and Scout to drop4c3.
- `Athena/__init__.py` advances package metadata.
- `Tests/validate_context_intelligence_profiles.py` updates the current-version assertion to drop4c3.

## Validation
- Reasoning Engine: PASS 16/16
- Reasoning Engine Doctor: PASS 8/8
- Context Graph Foundation: PASS 13/13
- Evidence Chain Engine: PASS 13/13
- Context Graph Doctor: PASS
- Evidence Chain Doctor: PASS
- One-click Workspace Guard: PASS 7/7
- One-click Fantrax Connect: PASS 8/8
- Context Intelligence Profiles: PASS 13/13
- Player Intelligence Foundation: PASS 11/11

## Known Limitations
- Reasoning is currently limited by available graph relationships. Schedule, coach, achievement, deployment, game, and odds-specific evidence are supported as reasoning concepts but not yet broadly populated in the graph.
- Relevance scoring is deterministic and explainable, but weights are still foundational defaults. Future sprints should tune them against richer historical/context evidence.
- Scout exposes the reasoning package through developer API, but main narrative responses are not yet bound to the reasoning package.

## Recommended Next Sprint
4C.4 — Scout Reasoning Binding: route Player Intelligence and Context Profile responses through the reasoning package so Scout can consistently present Evidence → Context → Conclusion → Confidence → Known Limitations.
