# AthenaEngine Change Manifest

## Version
0.5.1.4.0

## Release
Official Feed Connectors - NHL Foundation

## Scope
Introduces the first official league connector foundation for Event Intelligence, centered on NHL official feed profiles and deterministic, network-safe connector normalization.

## Added
- `Knowledge/Events/feeds.py`
  - Feed Registry
  - Feed Definition
  - Feed Health
  - Refresh Policy
  - Rate Limit Policy
  - Feed discovery helpers
  - Seeded NHL official and trusted NHL feed profiles
- `Knowledge/Events/acquisition.py`
  - Canonical `FeedResult`
  - Connector registry
  - Static/JSON/RSS/REST/provider connector abstractions
  - Feed Acquisition Engine
- `Knowledge/Events/nhl_official.py`
  - `NhlOfficialApiConnector`
  - Official NHL feed identifiers
  - Schedule payload normalization
  - Standings/team snapshot normalization
  - Network-safe sample acquisition
  - NHL connector summary
- `Tools/doctor_official_nhl_feed_connectors.py`
- `Tests/validate_official_nhl_feed_connectors.py`

## Updated
- `Core/version.py`
  - Version advanced to `0.5.1.4.0`
  - Release metadata updated for Epic 5, Sprint 1, Patch 4
- `Knowledge/Events/__init__.py`
  - Exposes feed/acquisition/NHL connector contracts
- `Knowledge/Events/registry.py`
  - Event Intelligence version advanced
  - Adds `team_snapshot` to event taxonomy
- `Knowledge/Events/event_graph.py`
  - Event graph version advanced
- `Knowledge/Events/source_intelligence.py`
  - Source intelligence version advanced
- `Tests/validate_event_registry_source_intelligence.py`
  - Keeps Event Registry validator compatible with later Sprint 1 patches
- `Tools/doctor_event_registry_source_intelligence.py`
  - Keeps Event Registry doctor compatible with later Sprint 1 patches
- `Tools/athena_studio.py`
  - Event doctor/validator routing now prefers the latest NHL connector checks
  - Event status card reflects registry/feed/NHL connector availability

## Validation
Local targeted validation passed:
- `Tools/doctor_official_nhl_feed_connectors.py`
- `Tests/validate_official_nhl_feed_connectors.py`
- `Tools/doctor_event_registry_source_intelligence.py`
- `Tests/validate_event_registry_source_intelligence.py`
- Regression smoke checks for Renderer, Team Reasoning, Comparison, and PIF Build 004
- Python compile check for changed modules

## Packaging
Packaged for extraction into:

```text
F:\Development
```

Archive root:

```text
AthenaEngine/
```
