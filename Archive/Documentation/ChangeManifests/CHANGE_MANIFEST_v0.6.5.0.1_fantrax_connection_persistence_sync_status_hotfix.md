# v0.6.5.0.1 — Fantrax Connection Persistence & Sync Status Hotfix

## Changed/new files
- `Athena/workspace.py`
- `Core/version.py`
- `Scout/app.py`
- `Tests/validate_fantrax_connection_persistence_sync_status_hotfix.py`
- Current-release validators updated for v0.6.5.0.1 metadata.
- `CHANGELOG.md`

## Scope
- Active `Configuration/workspace.json` Fantrax league ID is authoritative.
- Legacy `Configuration/config.json` provider league ID is synchronized to the valid active workspace ID, preventing stale fallback/reversion.
- Placeholder/test league IDs are never mirrored into live provider configuration.
- Successful sync presentation is not downgraded merely because a downstream capability has limited evidence.
- v0.6.5.0.0 transaction acquisition/classification behavior is unchanged.
