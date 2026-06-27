# Athena v0.5.0-drop4e15 — Runtime Dedupe + Router Fix

## Purpose

Fix the confirmed split-root problem where drop4e14 files were placed under
`Athena/Athena/...` while the launcher served root-level `Scout/app.py` and
`Core/version.py`.

## Changes

- Updates canonical root `Core/version.py` to `0.5.0-drop4e15`.
- Promotes the intended Scout app into canonical root `Scout/app.py`.
- Removes Scout conversation import-time monkeypatching that intercepted
  `Analyze my league` before the router could classify league intent.
- Updates `Scout/conversation/player_route_hotfix.py` so league/team/fantasy
  prompts are never treated as player-analysis prompts.
- Updates `Clean Athena Runtime.bat` to remove misplaced nested runtime folders:
  - `Athena/Core`
  - `Athena/Scout`

## Expected Result

- `type Core\version.py` shows `drop4e15`.
- `Analyze my league` routes to League Intelligence.
- Root-level `Scout/app.py` is the only served Scout UI.
- Nested package `Athena/` remains for engine modules, but no longer contains
  duplicate `Core` or `Scout` runtime folders.
