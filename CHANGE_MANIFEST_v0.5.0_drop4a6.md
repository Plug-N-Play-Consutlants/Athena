# Athena v0.5.0-drop4a6 — Scout Public Hockey Answer Binding

## Purpose
Bind Scout public-sports questions to Athena's compact public hockey knowledge retrieval layer.

## Added / Changed
- `Scout/conversation/router.py`
  - Public mode now routes non-overview questions to `retrieve_public_hockey_knowledge`.
  - Scout returns bounded public hockey answers from NHL Rulebook / NHL-NHLPA MOU knowledge packs.
  - Developer Mode exposes retrieval status, packs checked, and evidence used.
  - Unsupported public questions return bounded no-match guidance instead of generic public-mode placeholder text.
- `Scout/app.py`
  - UI build label updated to Drop 4A.6.
- `Tests/validate_scout_public_hockey_answer_binding.py`
  - Validates LTIR/CBA answers, icing/rulebook answers, unsupported no-invention behavior, overview routing, and version binding.
- `Core/version.py` updated to `0.5.0-drop4a6`.

## Expected prerequisite
Run the public hockey knowledge-pack builder first if packs are missing:

`Tools/build_public_hockey_knowledge_packs.py`

## Design guardrail
Scout can cite retrieved public hockey knowledge-pack evidence, but it does not yet perform full cap, waiver, LTIR, or legal calculations.
