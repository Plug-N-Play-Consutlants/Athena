# AthenaEngine v0.7.7.0.1 — Inquiry Utilization and Adaptive Evidence Hotfix

## Scope
Targeted hotfix for the failed v0.7.7.0.0 Verify Build. No new intelligence module or feature surface is introduced.

## Corrections
- Live-event public composition now includes the strongest selected event evidence in the normal Scout response instead of returning only a generic evidence lead-in.
- Consensus repository cleanup doctor now recognizes root-history files already classified as safe by the canonical Repository Safe Cleanup doctor as pending cleanup rather than structural failures.
- Unexpected root-history files remain failures.
- Studio Preview Cleanup / Apply Safe Cleanup remains the canonical user-facing cleanup path. Root `CHANGE_MANIFEST_*.md` files are previewed as safe candidates and archived to `Archive/Documentation/ChangeManifests` when applied.

## Acceptance
1. Reload Studio and verify v0.7.7.0.1.
2. Preview Cleanup: root change manifests must appear as safe cleanup candidates.
3. Apply Safe Cleanup: manifests must move to `Archive/Documentation/ChangeManifests` without manual file operations.
4. Verify Build must pass the consensus cleanup doctor/validator and Scout intent orchestration validation.
5. Continue to Scout acceptance only after Verify Build passes.
