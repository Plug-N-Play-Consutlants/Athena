# AthenaEngine v0.5.3.1.8 — Cleanup Approval UX + Architecture Review Queue

## Scope

Studio repository governance now supports category-based cleanup approval and a dedicated architecture review queue.

## Changes

- Added grouped cleanup action summaries for safe cleanup previews.
- Added category-safe cleanup flags:
  - `--apply-delete-safe`
  - `--archive-root-history`
  - `--apply-archive-root-history`
- Kept `--apply-safe-cleanup` as a compatibility alias for delete-safe cache cleanup only.
- Added `--review-queue` architecture review report.
- Added Studio button: `Review Queue`.
- Added review queue categories for root history, legacy doctors, cleanup/patch scripts, dynamic/provider entrypoints, stubs/placeholders, package markers, and general review items.
- Updated repository governance and file usefulness version markers.
- Extended repository governance validation to verify review queue and grouped cleanup summaries.

## Guardrails

- No source deletion is authorized.
- Root history archival requires explicit archive flag plus explicit apply flag.
- Delete-safe cleanup remains limited to reproducible cache/bytecode artifacts.
