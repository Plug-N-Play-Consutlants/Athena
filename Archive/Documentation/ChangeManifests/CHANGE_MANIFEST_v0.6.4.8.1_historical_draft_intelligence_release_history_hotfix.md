# v0.6.4.8.1 — Historical Draft Intelligence Release History Hotfix

## Scope
Hotfix for the v0.6.4.8.0 Studio Verify Build failure in Consensus Repository Cleanup.

## Defect
Overlay extraction cannot delete or relocate root history files. The cleanup doctor already tolerates known root-history residue pending Studio Safe Cleanup, but the tolerance set did not include the locked v0.6.4.7.0 manifest. This caused `root_history_archived` to fail after applying the v0.6.4.8.0 overlay. The failed 8.0 candidate manifest is likewise expected to remain at root when this hotfix is overlaid.

## Changes
- Advance version metadata to v0.6.4.8.1.
- Preserve the Historical Draft Intelligence implementation from v0.6.4.8.0.
- Extend the Consensus Repository Cleanup doctor overlay tolerance to the known v0.6.4.7.0 and v0.6.4.8.0 root manifests.
- Leave actual archival/removal to the existing Studio Safe Cleanup workflow.
- No new Studio actions or buttons.

## Acceptance
- Consensus Repository Cleanup doctor PASS.
- Consensus Repository Cleanup validator PASS.
- Historical Draft Intelligence validator PASS.
- Historical Scout routing regression PASS.
- Studio Verify Build PASS before runtime acceptance and lock.
