# Athena v0.5.0-drop4c1 — Context Graph Foundation

## Summary
Introduces the first canonical context graph foundation for Epic 4C. Athena can now build a provider-agnostic graph from existing Knowledge outputs and traverse connected evidence chains.

## Changes
- Added `Knowledge/Graph/canonical_graph.py` with canonical node, relationship, graph walk, and evidence-chain primitives.
- Added `Knowledge/Graph/builder.py` to build `Output/canonical_context_graph.json` from league, team, player, contract, and public hockey knowledge-pack outputs.
- Added `Knowledge/Graph/evidence_chain.py` for evidence-chain retrieval over graph entities.
- Added `Knowledge/Graph/registries.py` with canonical entity and relationship registries.
- Added `Tools/doctor_context_graph.py` for graph doctor validation.
- Added `Tests/validate_context_graph_foundation.py`.
- Restored workspace runtime helpers expected by current orchestration/tests: `repair_workspace_file`, `record_operation_result`, `is_placeholder_league_id`, and `classify_fantrax_auth_secret`.
- Added `ENGINE_LABEL` to version metadata.
- Updated Athena/Scout version metadata to `0.5.0-drop4c1`.

## Graph Output
Current graph build from the uploaded workspace:
- Nodes: 624
- Relationships: 859
- Entity types: player, team, league, contract, knowledge_pack
- Relationship types: rostered_by, plays_for, has_contract, member_of, uses_rules_from

## Validation
- `Tests/validate_context_graph_foundation.py` — PASS 13/13
- `Tools/doctor_context_graph.py` — PASS
- `Tests/validate_one_click_workspace_guard.py` — PASS 7/7 after restoring workspace helpers
- `Tests/validate_one_click_fantrax_connect.py` — PASS 8/8 after restoring workspace helpers

## Notes
Some older validators in the package contain hard-coded version expectations from drop4b1/drop4b2 and should be refreshed or retired as part of validation hygiene. The graph foundation validator is current for drop4c1.
