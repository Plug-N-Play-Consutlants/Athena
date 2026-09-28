# v0.6.4.9.2 — Scout Normal Response Composition Hotfix

## Purpose
Restore substantive user-facing Scout answers in Normal Mode without changing accepted 9.1 intelligence, routing, discovery, or evidence-diversity behavior.

## Changes
- Fix live-event response composition so the selected-event narrative enters the shared response composer before `public_comment` is generated.
- Add bounded Normal Mode composition for current pre-draft context so current state, material available-pool evidence, and the bounded conclusion remain visible without Developer Mode diagnostics.
- Preserve Developer Mode as an inspection layer over the same answer rather than the only place substantive content is visible.
- Add Studio Verify Build validation for the Normal Mode response contract.
- No new Studio button or action.

## Acceptance
- `Maple Leafs news` in Normal Mode communicates the selected Leafs developments, not only Source/Details controls.
- `What should I know about the JHLPAA draft going into tomorrow?` in Normal Mode communicates current pre-draft state, material pool context, historical context when available, and bounded interpretation.
- Developer Mode retains diagnostics/provenance without being required to obtain the substantive answer.
