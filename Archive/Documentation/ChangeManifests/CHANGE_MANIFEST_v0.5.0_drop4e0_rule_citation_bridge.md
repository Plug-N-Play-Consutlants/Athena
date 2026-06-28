# Athena v0.5.0-drop4e0 — Rule Citation Bridge Preflight

## Purpose
Prepare Scout and the upcoming Reasoning layer to expose league-rule evidence as first-class, viewable citations when answers rely on NHL rulebook or NHL/NHLPA CBA/MOU knowledge-pack topics.

## Added
- `Knowledge/Sources/rule_citations.py`
  - Builds stable rule citation IDs from compact knowledge-pack evidence.
  - Converts retrieval evidence into Scout-renderable rule cards.
  - Provides `lookup_rule_citation(...)` for rule/provision drill-down views.
- `Tests/validate_rule_citation_cards.py`
  - Validates Scout rule citations on public LTIR answers.
  - Validates stable IDs, authority references, view URLs, drill-down lookup, and no false citations for unsupported questions.

## Changed
- `Scout/conversation/router.py`
  - Public hockey answers now attach top-level `rule_citations` whenever retrieval evidence includes rulebook/CBA/MOU topics.
  - Developer trace now includes the same citation records.
- `Scout/app.py`
  - Scout UI now renders a `Rule Evidence` section with compact rule cards.
  - Rule cards include source title, authority reference, summary, and a drill-down link.
  - Added `/api/rules/public-hockey?source_id=<id>&topic_key=<topic>` endpoint.

## Validation
- `python Tests/validate_rule_citation_cards.py` → PASS, 8 passed, 0 failed.
- `python -m py_compile Scout/app.py Scout/conversation/router.py Knowledge/Sources/rule_citations.py` → PASS.

## Note
Existing `Tests/validate_scout_public_hockey_answer_binding.py` still passes behavior checks but fails its stale historical version gate because the uploaded snapshot's `Core/version.py` reports `0.5.0-drop4d2d` while later 4D manifests are present. This patch does not change version metadata.
