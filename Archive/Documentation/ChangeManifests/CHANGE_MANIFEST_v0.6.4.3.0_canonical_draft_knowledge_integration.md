# Athena v0.6.4.3.0 — Canonical Draft Knowledge Integration

## Purpose
Promote the authenticated Fantrax draft-pick source discovered in v0.6.4.2.0 into the normal Fetch -> Build -> Knowledge -> Scout pipeline.

## Changes
- Fetch `general/getDraftPicks` during normal Fantrax sync.
- Normalize `currentDraftPicks` and `futureDraftPicks` into provider-neutral `Output/draft_picks.json` and CSV.
- Preserve observed current ownership without inventing current-year original ownership or transaction provenance.
- Preserve observed original/current ownership for Fantrax future-pick records.
- Register `draft_assets` in Knowledge readiness and capability assessment.
- Add dedicated Scout routing for league draft order / draft-pick ownership questions.
- Distinguish known manager population from observed manager behavioral evidence when the current season has zero transactions.
- Replace brittle exact release-name gates in the affected Experience/Scout doctors and validators with release-name presence checks.
- Add focused Draft Knowledge validation to Studio Verify Build.

## Expected live acceptance
After Sync League against JHLPAA 2026, current Fantrax evidence should normalize 280 current picks across 20 rounds and 126 future draft assets. Scout question `What is the league draft order?` should route to `fantasy_draft_order` and report the Fantrax current board by round.
