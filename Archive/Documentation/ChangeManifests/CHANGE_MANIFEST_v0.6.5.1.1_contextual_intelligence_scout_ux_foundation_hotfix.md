# Athena v0.6.5.1.1 — Contextual Intelligence & Scout UX Foundation Hotfix

## Scope
Correction hotfix for the v0.6.5.1.0 foundation. No new evidence-provider scope is introduced.

## Changes
- Preserves explicit two-sided `vs` / `versus` player subjects before legacy entity parsing so asymmetric comparisons cannot collapse into a single-player answer.
- Adds regression assertions that both comparison subjects survive into the final response and that the response is not truncated.
- Humanizes Normal-mode focused investigation prose while preserving the structured investigative contract and bounded evidence semantics.
- Sanitizes legacy internal comparison-engine build labels from user-facing comparison limitations.
- Advances version/orchestration metadata to 0.6.5.1.1 under the locked Major.Epic.Sprint.Patch.Hotfix scheme.

## Regression gates
- Contextual Intelligence & Scout UX Foundation validator: PASS.
- Scout Runtime Acceptance Hotfix: 41/41 PASS.
- Scout Intent Orchestration: PASS.

## Deferred
- Career-stat ingestion and NHL.com-style multi-season Stats presentation.
- Deeper live contract/cap/roster evidence acquisition for investigative scenarios.
- Full Relationship Intelligence implementation.
