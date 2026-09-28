# Athena v0.6.4.2.0 - Authenticated Draft Source Discovery

## Purpose
Establish an evidence-backed Fantrax draft-pick acquisition path before integrating Draft Knowledge into sync.

## Changes
- Registered `general/getDraftPicks` as the Fantrax draft-pick endpoint.
- Added `FantraxClient.get_draft_picks()` using Athena's existing authenticated session.
- Added a safe discovery runner that captures the raw provider payload locally and emits only credential-redacted structural diagnostics.
- Added Studio Developer Diagnostics action `Discover Draft Source`.
- Added focused validation for the discovery increment.

## Safety
The discovery output never prints Cookie headers, Secret IDs, authorization values, tokens, passwords, or session values. Credentials remain local.

## Next gate
Run discovery from Studio and inspect the returned schema before modifying the existing draft-pick builder or adding Draft Knowledge to Sync League.
