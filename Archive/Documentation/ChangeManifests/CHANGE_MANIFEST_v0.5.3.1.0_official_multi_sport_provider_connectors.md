# Change Manifest — v0.5.3.1.0 Official Multi-Sport Provider Connectors

## Summary
Adds the first official multi-sport provider connector framework on top of the validated multi-sport event framework.

## Added
- `Engine/MultiSport/` package with sport, league, taxonomy and connector models.
- Official offline-safe connector profiles for NHL, NFL, NBA, MLB, UEFA and FIFA.
- Canonical event-type alias normalization for sport-specific terminology.
- Knowledge-facing multi-sport summary and sample acquisition helpers.
- `Tools/doctor_multi_sport_provider_connectors.py`.
- `Tests/validate_multi_sport_provider_connectors.py`.

## Updated
- Version metadata to `0.5.3.1.0`.
- Event Intelligence aggregate doctor/validator now targets multi-sport connectors.
- Studio Doctor/Validate Everything registration includes multi-sport connectors.
- Event summarization validators accept forward-compatible Epic 5 versions.

## Packaging
Extract ZIP directly into `F:\Development`; archive contains top-level `AthenaEngine/`.
