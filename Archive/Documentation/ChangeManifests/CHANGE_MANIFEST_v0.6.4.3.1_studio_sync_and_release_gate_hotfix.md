# Athena v0.6.4.3.1 - Studio Sync and Release Gate Hotfix

- Adds Sync League as a first-class Studio operation backed by the canonical Athena sync pipeline.
- Keeps lower-level capability operations behind existing workflows rather than adding new Studio buttons.
- Replaces the stale exact duplicate-basename count assertion with inventory-consistency validation.
- Tolerates the known v0.6.4.3.0 root manifest residue left by overlay extraction until Studio Safe Cleanup archives it.
- Preserves Canonical Draft Knowledge behavior from v0.6.4.3.0.
