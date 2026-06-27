# Athena v0.5.0 Drop 3E.3 — Athena Uses Provider Registry

## Summary

Routes Athena connection through the provider registry introduced in 3E.1 and the Fantrax provider adapter introduced in 3E.2.

## Changes

- Athena `connect()` now resolves providers through `Providers.base.registry`.
- `connect_fantrax()` remains as a compatibility wrapper.
- Athena no longer imports `FantraxClient` directly in `Athena/connect.py`.
- Athena status now exposes registered providers and active provider status.
- Workspace now stores `provider_key` for registry resolution.
- Added validation for provider-registry-based Athena connection.

## Notes

This patch is root-folder-name agnostic. It does not hardcode `Sports_Intelligence_Engine_2.0` or `Athena` as the project root folder name.
