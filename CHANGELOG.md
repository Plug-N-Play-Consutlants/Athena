# Changelog

## v0.5.3.1.3 — Event Registry Normalizer + Studio Scrollbar Hotfix

- Added `canonical_event_payload` compatibility alias to restore Event package imports.
- Kept `canonical_event_types` compatibility surface intact.
- Relaxed older Event doctor/validator release-name gates for later hotfix releases.
- Added a scrollbar to the Athena Studio output panel.


## v0.5.2.2.0 — Cross-Domain Event Impact

- Added deterministic Cross-Domain Event Impact engine.
- Added event-to-domain propagation rules for player, team, fantasy, prospect, historical and organizational intelligence.
- Added graph delta generation for event-driven Knowledge Graph updates.
- Added Cross-Domain doctor and validator.
- Updated Event Intelligence aggregate validation and Athena Studio registration.


## 0.5.1.0.1 — Version Compatibility Hotfix

- Advanced release metadata to `0.5.1.0.1`.
- Updated legacy Epic 4 validators to accept the locked numeric version schema.
- Added shared validator helper `Tests/version_compat.py`.
- No Event Intelligence behavior changes.

# v0.5.0-drop4e33 — Athena Studio Tile UI Polish

- Refined Athena Studio command controls into compact dashboard tiles.
- Added tile-specific Studio validation and doctor checks.
- Preserved Studio grouped panels, tooltips, runtime reload flow, public rule bindings, and PIF Build 003.


## v0.4.2 — Scout Local Web Foundation

- Rebuilt Scout Alpha as a zero-dependency local web application.
- Removed Streamlit requirement from the Scout launcher.
- Added local JSON API endpoints for context, ask, and analyze.
- Preserved simple Ask / Analyze / Developer Mode UX.


## v0.4.0 — Scout Alpha

- Added Scout, the first minimal local conversation/experience layer powered by Athena Engine.
- Added deterministic question routing for initial league, manager, market, contract, and limitation questions.
- Added Analyze League button flow in Streamlit.
- Added Developer Mode response metadata.
- Added Scout Alpha validation script.

# Changelog

## v0.3.1 — Intelligence Refinement

- Refined transaction-derived manager behavior into observed facts, inferred profiles, and limitations.
- Added explainable league market liquidity with score, confidence, drivers, and limitations.
- Renamed ambiguous fee totals to observed transaction fee totals.
- Marked Fantrax finance page as the authoritative future source for official money balances.


## Sprint 1.1c — Platform Configuration Framework

- Added `Configuration/secrets.example.json`.
- Added `Configuration/README.md`.
- Added `.gitignore` protection for `Configuration/secrets.local.json`.
- Extended `Core/config.py` with `get_secret_value()` and `reload_configuration()`.
- Updated Fantrax cookie loading to prefer `secrets.local.json`.
- Updated Fantrax diagnostics and provider validation to report local secret status.
- Preserved legacy cookie fallback paths for compatibility.


## 2.0.0
- Initial clean architecture scaffold.

## v0.2.0 - Fantrax Provider 2.0

- Added Fantrax authentication package.
- Added Fantrax endpoint registry.
- Refactored Fantrax client around provider transport responsibilities.
- Added fxpa/req support for authenticated transaction history.
- Added provider diagnostics script.
- Updated transaction fetch to report returned row counts.

## Sprint 1.1b — Fantrax Provider Validation Harness

- Added `Tests/validate_fantrax_provider.py`.
- Added one-command validation of Fantrax provider configuration, authentication setup, fetch calls, raw output writes, and transaction payload shape.
- Added JSON and plain-text validation reports under `Reports/`.
- Added provider validation documentation.

This sprint does not add product UX. It provides a developer validation checkpoint before continuing into canonical transaction modeling.

## v0.2.2 - Repository Cleanup Baseline - 2026-06-18

- Archived obsolete Fantrax fetches for invalid legacy endpoints.
- Consolidated active Fantrax fetch path to league, player pool, and transactions.
- Updated provider validation harness to validate canonical fetches only.
- Rebuilt `player_master.py` as a compatibility output derived from `player_pool_master.py`.
- Updated `transaction_master.py` to parse Fantrax `table.rows` transaction payloads.
- Archived root-level duplicate scripts and patch-note files.
- Removed Python cache files and local secrets from release output.

## v0.3.0 — Canonical Transaction Engine

- Added canonical transaction grouping by Fantrax `txSetId`.
- Added canonical asset movement model for player adds/drops.
- Added transaction history Knowledge output.
- Added manager behavior Intelligence output.
- Added league market Intelligence output.
- Added transaction pipeline validation harness.
- Updated Knowledge Readiness to recognize current transaction, manager behavior, and league market outputs.

## v0.3.0 — Canonical Transaction Engine

- Added canonical transaction grouping by Fantrax `txSetId`.
- Added canonical asset movement model for player adds/drops.
- Added transaction history Knowledge output.
- Added manager behavior Intelligence output.
- Added league market Intelligence output.
- Added transaction pipeline validation harness.
- Updated Knowledge Readiness to recognize current transaction, manager behavior, and league market outputs.

## v0.4.1 — Scout Spyder Launcher

- Added `Scout/run_scout.py` as the canonical local launcher for Scout Alpha.
- Updated Scout documentation for the Anaconda/Spyder workflow.
- Kept Streamlit as an implementation detail behind the launcher.


## v0.5.0-drop4e26
- Scout UX cleanup: Fantrax provider-state persistence, password-manager field support, local credential restore fallback, and collapsed raw reasoning output.

## v0.5.0-drop4e32 — Athena Studio Beta UI

- Converted Athena Studio from a flat button launcher into a grouped Beta command center.
- Added Runtime Center, Validation Center, Doctor Center, Intelligence Tools, and Logs & Diagnostics panels.
- Added Microsoft-style icon labels, status cards, clearer bottom status strip, and hover tooltips for core controls.
- Preserved existing runtime, validation, doctor, reload, PIF, provider, and log-export workflows.
- Added Studio Beta UI validator and doctor.
## v0.5.0-drop4e35

- Added PIF Build 004 public team profile seed pack.
- Added public team answers and richer public comparison structure.
- Added Studio primary runtime toolbar and toolbar validation/doctor utilities.
- Updated public event-context routing to avoid invented current-news/team-impact answers.

## 0.5.2.2.1 — Cross-Domain Event Impact Import Hotfix

- Fixed Event Intelligence import surface for Cross-Domain Impact validation.
- Added canonical event compatibility helpers.
- Repackaged complete Knowledge.Events module set to overwrite stale local files.

## 0.5.2.3.0 — Event Timeline Intelligence

- Added Engine/EventTimeline as a first-class deterministic timeline engine.
- Added timeline node, link, timeline, and batch result models.
- Added subject-based event grouping, chronological ordering, followed-by relationship generation, and timeline narrative helpers.
- Added timeline reasoning payloads and risk flags for availability/context sequences.
- Added Studio buttons and aggregate Doctor/Validate Everything registration.
- Added Event Timeline doctor and validator.
