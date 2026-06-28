# CHANGE MANIFEST — v0.5.3.1.2

Release: Event Registry Compatibility Repair

## Purpose
Repair the Event Registry compatibility surface required by Event Intelligence, Cross-Domain Impact, Event Timeline, Event Confidence, Event Summary, and Multi-Sport Connectors.

## Changes
- Restored `canonical_event_types()` in `Knowledge/Events/registry.py`.
- Re-exported `canonical_event_types` from `Knowledge/Events/__init__.py`.
- Updated version metadata to `0.5.3.1.2`.

## Scope
Hotfix only. No new feature behavior.
