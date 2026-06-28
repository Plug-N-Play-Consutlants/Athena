# AthenaEngine v0.5.5.5.18 — Scout Route Map and Targeted Routing Cleanup

## Summary

This acceptance cleanup audits Scout routing and fixes the current root cause behind targeted team questions falling into broad public contender analysis.

## Changes

- Added `docs/SCOUT_ROUTE_MAP_v0.5.5.5.18.md`.
- Added `Tools/doctor_scout_route_map.py`.
- Added `Tests/validate_scout_route_map_and_targeted_routing_v055518.py`.
- Moved broad public analytical fallback behind canonical public intent/entity routing.
- Normalized possessive Leafs shorthand before public entity resolution.
- Expanded public intent classification so weakness/flaw/problem/struggle prompts classify as quality/team analysis.
- Updated targeted team weakness composition to lead with the actual weakness analysis rather than a generic team profile.

## Acceptance Rule

Specific entity + specific analytical intent beats broad public contender/ranking fallback.
