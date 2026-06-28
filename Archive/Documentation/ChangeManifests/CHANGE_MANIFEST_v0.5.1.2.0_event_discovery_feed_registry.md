# Athena Sports Intelligence Platform

## Version
0.5.1.2.0

## Release
Event Discovery & Feed Registry

## Summary
Adds the first operational Event Intelligence discovery layer: feed registry, feed discovery, feed health, and deterministic ingestion planning.

## Changes
- Added `Knowledge/Events/feeds.py` with feed definitions, feed registry, feed health, discovery results, ingestion plans, and static payload ingestion.
- Exported feed registry contracts through `Knowledge.Events`.
- Updated version metadata to `0.5.1.2.0` using the locked `major.epic.sprint.patch.hotfix` scheme.
- Added `Tools/doctor_event_discovery_feed_registry.py`.
- Added `Tests/validate_event_discovery_feed_registry.py`.
- Updated Studio Event Intelligence routing so Doctor/Validate Events use the feed registry validation first while preserving older Event Registry validation compatibility.
- Updated Event Registry/Source Intelligence validators to preserve lineage compatibility across Sprint 1 Event Intelligence patches.

## Validation
Expected Studio gate:

```text
Doctor Everything
Validate Everything
```

## Packaging
Extract this patch ZIP directly into:

```text
F:\Development
```

It contains a top-level `AthenaEngine/` folder and lands in the canonical repository root.
