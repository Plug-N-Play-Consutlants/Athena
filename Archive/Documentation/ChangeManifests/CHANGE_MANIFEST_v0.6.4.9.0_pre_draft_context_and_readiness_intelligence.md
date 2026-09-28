# v0.6.4.9.0 — Pre-Draft Context and Readiness Intelligence

## Objective
Create reusable pre-draft intelligence from current league state plus historical evidence, while tightening public team-news relevance through the shared evidence-selection layer.

## Changes
- Added `Knowledge/Intelligence/Fantasy/pre_draft_context.py`.
- Reuses current league profile, keeper/player-pool state, draft-capital ownership, supplied Fantrax FA evidence, and historical draft intelligence.
- Added `fantasy_pre_draft_context` Scout orchestration without replacing longitudinal draft intelligence.
- Configured draft slots remain capacity/ownership evidence and are never treated as future selections.
- Fantrax CSV rows marked FA are contextual evidence, not a live availability guarantee.
- Tightened trusted linked-article team attribution: a passing body mention can no longer resurrect an RSS item rejected for entity mismatch; heading/opening centrality is required.
- Added Studio Verify Build validators for pre-draft context and public team-news relevance. No new Studio button.

## Acceptance
- Current 2026 pre-draft state is discoverable from existing canonical/current evidence.
- Historical draft intelligence is reused rather than duplicated.
- No selection prediction is invented.
- Team-specific public news rejects unrelated-team articles merely containing incidental references.
- Existing historical draft/identity/routing regressions remain PASS.
