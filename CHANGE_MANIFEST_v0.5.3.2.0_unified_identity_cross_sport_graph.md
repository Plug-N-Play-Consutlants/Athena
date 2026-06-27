# AthenaEngine v0.5.3.2.0 — Unified Identity & Cross-Sport Knowledge Graph

## Status
Build candidate for Epic 5 Sprint 3 Patch 2 Hotfix 0.

## Scope
- Added `Knowledge.Identity` as the provider-neutral identity subsystem.
- Added shared `IdentityEntity`, `ExternalIdentifier`, `IdentityRelationship`, `IdentityResolution`, and `IdentityGraphDiagnostics` models.
- Added seeded cross-sport registry covering hockey/NHL, football/NFL, basketball/NBA, baseball/MLB, and soccer/UEFA.
- Added sport-aware identity resolution for overlapping names such as Toronto teams and duplicate player names such as Sebastian Aho.
- Added external identifier resolution without binding Athena's canonical identity model to provider-specific keys.
- Added cross-sport graph relationship mapping between sports, leagues, teams, players, and external identifiers.
- Added Studio-facing identity graph diagnostics payload.
- Added doctor and validation scripts for v0.5.3.2.0.
- Preserved v0.5.3.1.4 Knowledge.Events compatibility exports.

## Validation Entry Points
- `Tools/doctor_unified_identity_cross_sport_graph.py`
- `Tests/validate_unified_identity_cross_sport_graph.py`

## Packaging
Patch ZIP extracts directly into `F:\Development` and contains top-level `AthenaEngine/`.
