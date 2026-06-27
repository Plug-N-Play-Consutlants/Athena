# Athena v0.5.0-drop4e14 — Scout Fantasy Mode Routing + UX Cleanup

## Purpose
Targeted repair for Scout remaining in player-analysis routing when the user asks league questions, plus UX cleanup for Fantasy/Public mode switching.

## Changes
- Fixed the legacy player-route hotfix so `Analyze my league` and similar prompts are no longer intercepted as player prompts.
- Preserved player prompt normalization for `Auston Matthews`, `Analyze Auston Matthews`, and similar player queries.
- Updated version metadata to `v0.5.0-drop4e14`.
- When switching to Fantasy League mode, Scout opens and scrolls to the Fantrax login panel.
- Fantrax sync button and operation history stay hidden in Public Sports mode.
- Added floating jump controls for top and prompt/end navigation.

## Test Targets
1. Start Scout and confirm header shows `v0.5.0-drop4e14`.
2. Public Sports: Fantrax panel, Sync League, and Operation History should be hidden.
3. Switch to Fantasy League: Fantrax panel should open and scroll into view.
4. Ask: `Analyze my league` should produce League analysis, not Player intelligence unavailable.
5. Ask: `Analyze Auston Matthews` should still produce player intelligence.
