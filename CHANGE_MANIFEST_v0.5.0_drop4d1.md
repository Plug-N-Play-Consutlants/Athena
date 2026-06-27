# Athena v0.5.0-drop4d1 Change Manifest

## Sprint
Epic 4D.1 — Temporal Intelligence Foundation

## Purpose
Make time a first-class dimension in Athena without distorting objective evaluation. Historical evidence is represented as canonical temporal events and can be attached to the context graph as traversable evidence.

## Added
- `Knowledge/Graph/temporal_intelligence.py`
  - `build_temporal_evidence(...)`
  - `enrich_graph_with_temporal_events(...)`
  - `timeline_for_entity(...)`
  - `TemporalEvent` canonical event model
- `Tools/doctor_temporal_intelligence.py`
- `Tests/validate_temporal_intelligence.py`
- Scout developer endpoint:
  - `/api/graph/timeline?entity_id=<id>&limit=20`

## Temporal Event Types
- `production_snapshot`
- `contract_snapshot`
- `transaction`
- `asset_movement`
- `knowledge_pack_snapshot`

## Outputs Produced
- `Output/temporal_evidence_timeline.json`
- `Output/temporal_evidence_summary.json`
- `Output/canonical_context_graph_temporal.json`
- `Output/canonical_context_graph_temporal_summary.json`

## Version
- `Core/version.py` advanced to `0.5.0-drop4d1`
- `Athena/__init__.py` advanced to `0.5.0-drop4d1`
- Stale validator version gates refreshed to `drop4d1`

## Verified Results
- Temporal Intelligence: PASS 18/18
- Temporal Doctor: PASS 9/9
- Context Graph Foundation: PASS 13/13
- Evidence Chain Engine: PASS 13/13
- Reasoning Engine: PASS 16/16
- Context Graph Doctor: PASS
- Evidence Chain Doctor: PASS
- Reasoning Doctor: PASS 8/8
- One-click Workspace Guard: PASS 7/7
- One-click Fantrax Connect: PASS 8/8
- Context Intelligence Profiles: PASS 13/13
- Player Intelligence Foundation: PASS 11/11

## Current Temporal Build Metrics
- Temporal events: 788
- Temporal event subjects: 424
- Temporal graph nodes: 1,412
- Temporal graph relationships: 1,828
- Temporal event nodes: 788
- `has_temporal_event` relationships: 624
- `temporally_related_to` relationships: 345

## Known Limitations
- Some transaction-derived events do not have fully parsed dates and are retained with missing temporal anchors.
- Production snapshots are season-anchored to October 1 for deterministic ordering.
- Temporal graph is generated as a separate enriched graph artifact; the base canonical graph remains unchanged.
