# Change Manifest — v0.6.4.1.0 Adaptive Investigation Runtime Integration

## Purpose
Make the v0.6.4 investigation strategy operational at runtime while preserving rich analytical experiences.

## Added
- Runtime strategy bridge.
- Entity-safe recent-evidence fallback with explicit freshness metadata.
- Session-scoped investigation continuation.
- Runtime validator and doctor.
- Sports Ecosystem Investigative Intelligence added to the future roadmap.

## Behavioral contract
- A missing live/current match is a fallback condition, not automatically a cold stop.
- Fallback may use only relevant trustworthy evidence for the requested entity/context.
- Unrelated teams/entities and validation samples must not be substituted.
- Fallback freshness/limitations must remain explicit.
- Rich player/team/comparison strategies retain rich output.
