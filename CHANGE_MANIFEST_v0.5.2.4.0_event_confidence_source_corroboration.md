# Change Manifest — 0.5.2.4.0

## Release
Event Confidence & Source Corroboration

## Summary
Adds deterministic confidence scoring and source corroboration to Athena Event Intelligence. This release evaluates source quality, cross-source agreement, conflicts, confidence labels, and Scout-ready confidence explanations.

## Added
- `Engine/EventConfidence/` namespace
- Source confidence profiles
- Corroboration grouping
- Confidence scoring engine
- Scout confidence payload helper
- Corroboration timeline model
- Event Confidence doctor
- Event Confidence validator
- Studio Event Confidence doctor/validator registration

## Updated
- Version metadata to `0.5.2.4.0`
- Aggregate Event Intelligence doctor/validator now target confidence/corroboration
- Knowledge event exports include confidence helpers
- Engine namespace exports include `EventConfidence`

## Validation
- Doctor Event Confidence
- Validate Event Confidence
- Validate Event Intelligence
- Python compile check
