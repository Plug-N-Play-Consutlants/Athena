# AthenaEngine v0.7.7.3.2 — Analytical Study Validator Hotfix

## Objective
Repair the stale Whole-Picture Investigation verification contract exposed by Studio Verify Build on v0.7.7.3.1 without changing runtime analytical behavior.

## Changes
- Advances the build to v0.7.7.3.2 because v0.7.7.3.1 failed Studio verification.
- Updates `validate_whole_picture_investigation.py` to validate the current analytical-study public composition contract.
- Replaces the obsolete requirement for `Strongest named construction from current evidence:` with semantic checks for the current study presentation: Scenario Assessment, Assets on the Table, Proposed Construction, and Athena's Verdict.
- Retains the investigation-completion contract that requires a constructed named package from current evidence.
- Explicitly rejects both obsolete internal/public prompt phrases.
- No runtime reasoning or Scout composition behavior changed.
- No new Studio button.
