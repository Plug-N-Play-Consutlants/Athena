# v0.5.5.5.2 — Studio Log Visibility Hotfix

## Purpose

Small replacement-file hotfix on top of v0.5.5.5.1.

## Changes

- Restores useful Studio log visibility by opening Scout/debug/report output in a scrollable Studio window instead of only pointing to files under Reports.
- Adds Latest Debug to the default Diagnostics section.
- Searches project root, Logs, and Reports for recent debug/report text files.
- Forces Studio subprocess output to UTF-8 with replacement handling to prevent Windows cp1252 Unicode validation crashes.
- Relaxes validators for valid v0.5.5.5.x hotfix release names.
- Accepts live_event_intelligence as a valid public multi-sport event route after the Scout Runtime Acceptance Hotfix.

## Packaging

Patch contains only new/replacement files.
