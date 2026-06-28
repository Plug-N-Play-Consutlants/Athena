# v0.5.3.1.7 — Studio Architecture Governance

## Purpose
Refines Athena Studio repository governance from file inventory toward architecture governance.

## Changes
- Added architecture governance reporting via `Tools/repository_governance.py --architecture`.
- Classified version constants as release, component, schema, generator, internal engine, or other.
- Limited release drift detection to release-version constants only.
- Preserved component/schema/generator versions as catalogued metadata rather than drift failures.
- Replaced duplicate function-name noise with probable duplicate implementation detection using AST body signatures.
- Preserved duplicate content grouping by archive-only, active-with-archive, active-review, and package-marker categories.
- Changed root history archival preview destination to structured `Archive/Documentation/*` folders.
- Added Studio buttons for Architecture Governance, Duplicate Audit, and Cleanup Recommendations.
- Updated repository governance doctor and validator for architecture governance readiness.

## Guardrails
- No source deletion is authorized by this patch.
- Apply-safe-cleanup remains limited to reproducible cache/bytecode cleanup.
- Root history archival is preview-only unless explicitly approved later.
