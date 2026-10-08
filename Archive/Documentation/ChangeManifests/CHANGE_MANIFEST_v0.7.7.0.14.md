# v0.7.7.0.14 — Inquiry Semantic Ownership Hotfix

## Purpose
Restore a single semantic owner for transaction inquiry routing. `InquiryState` now supplies normalized transaction semantics to the Athena capability planner instead of the planner maintaining a competing transaction-phrase vocabulary.

## Changes
- `Athena/Inquiry/state.py`
  - Adds `plausibility_requested` as normalized inquiry state.
  - Canonicalizes protected asset mentions against resolved player subjects.
  - Supports direct protected-subject language such as `without Matthews` only when it resolves to a known transaction subject.
- `Athena/intent_planner.py`
  - Builds and consumes normalized `InquiryState` for public NHL transaction routing.
  - Removes the competing transaction verb/phrase gate for scenario and plausibility selection.
  - Salary-cap waivers and explicit plausibility requests operate on normalized inquiry state.
- `Tests/validate_inquiry_semantic_ownership.py`
  - Validates a paraphrase family across `get`, `acquire`, `trade for`, protected-asset variants, plausibility framing, and cap waiver.
- `Tools/doctor_inquiry_semantic_ownership.py`
  - Makes semantic ownership a Studio-verifiable invariant.
- `Tools/athena_studio.py`
  - Adds the semantic ownership doctor to Verify Build and Doctor Everything sequences without adding a new Studio button.
- Acceptance validators advanced to the current build metadata.

## Acceptance invariant
A normalized transaction inquiry with resolved organization and player subjects must be handled by Athena's transaction/plausibility capabilities. It must not fall through to legacy team-profile routing because of surface wording differences.

## Consumed candidates
- 0.7.7.0.12: discarded after direct `without Matthews` did not canonicalize as a protected resolved asset.
- 0.7.7.0.13: discarded after a stale embedded validator hotfix literal failed the focused gate.
