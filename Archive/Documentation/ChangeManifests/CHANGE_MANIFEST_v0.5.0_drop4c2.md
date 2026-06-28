# Athena v0.5.0-drop4c2 Change Manifest

## Sprint
Epic 4C — Context Graph Intelligence  
Sprint 4C.2 — Evidence Chain Engine

## Purpose
Turn the canonical context graph from a generated data structure into an explainability engine that can answer: "Why does Athena believe this?"

## Added
- `Knowledge/Graph/chain_engine.py`
  - `build_evidence_chain(...)`
  - `write_evidence_chain_report(...)`
  - relationship weighting
  - node-type weighting
  - path scoring
  - confidence propagation
  - developer evidence trace
  - bounded not-found response
- `Tools/doctor_evidence_chain.py`
  - validates sample entity evidence-chain availability
  - validates confidence normalization
  - validates scored paths, evidence nodes, and developer trace
  - writes JSON and TXT doctor reports
- `Tests/validate_evidence_chain_engine.py`
  - validates the new 4C.2 evidence-chain engine
  - validates relationship filtering
  - validates missing-entity behavior
  - validates report generation

## Updated
- `Core/version.py` advanced to `0.5.0-drop4c2`
- `Athena/__init__.py` advanced to `0.5.0-drop4c2`
- `Knowledge/Graph/__init__.py` exports new evidence-chain APIs
- `Scout/app.py`
  - added developer endpoint: `/api/graph/evidence-chain?entity_id=<id>&max_depth=2`
  - defaults to first available player if no entity is supplied
- Existing validation suites refreshed from stale hard-coded drop4b/drop4c1 version checks to drop4c2:
  - `Tests/validate_context_graph_foundation.py`
  - `Tests/validate_one_click_fantrax_connect.py`
  - `Tests/validate_one_click_workspace_guard.py`
  - `Tests/validate_context_intelligence_profiles.py`
  - `Tests/validate_player_intelligence_foundation.py`

## Generated / Included Runtime Reports
- `Reports/evidence_chain_doctor_report.json`
- `Reports/evidence_chain_doctor_report.txt`
- `Output/evidence_chain_player_003kg.json`

## Validation Results
- Evidence Chain Engine: PASS 13/13
- Evidence Chain Doctor: PASS
- Context Graph Foundation: PASS 13/13
- Context Graph Doctor: PASS
- One-click Fantrax Connect: PASS 8/8
- One-click Workspace Guard: PASS 7/7
- Context Intelligence Profiles: PASS 13/13
- Player Intelligence Foundation: PASS 11/11

## Current Graph State
- Nodes: 624
- Relationships: 859
- Node types: player, team, league, contract, knowledge_pack
- Relationship types: has_contract, plays_for, rostered_by, member_of, uses_rules_from

## Notes
This sprint intentionally does not add more graph node types. It makes the graph consumable by Intelligence and Scout first.

Next recommended sprint: 4C.3 — Intelligence Graph Binding, where Player Intelligence and Context Profiles consume `build_evidence_chain(...)` directly instead of only exposing it through developer tooling.
