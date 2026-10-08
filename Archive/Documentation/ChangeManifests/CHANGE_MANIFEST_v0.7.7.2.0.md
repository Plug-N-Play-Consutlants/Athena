# v0.7.7.2.0 — Organizational Asset Rights and Transaction Evaluation

## Objective
Make organizational control, transferable rights, and transaction eligibility explicit before Athena can use a player in a proposed NHL transaction; then require a bounded evaluation of the package Athena constructs.

## Changes
- Adds `OrganizationalRightsState` separating playing relationship from NHL organizational control.
- Distinguishes controlled roster players, controlled NHL-provider prospects, and players for whom control is not established.
- Prevents uncontrolled players from entering transaction construction.
- Represents prospect transfer objects as rights-or-contract when the exact mechanism is not yet established instead of inventing an SPC.
- Adds organizational asset discovery/eligibility public route for Leafs asset and prospect-tradeability questions.
- Requires transaction investigations to record organizational control, transaction eligibility, package evaluation, and unresolved draft-capital evidence.
- Adds an explicit post-construction analytical verdict without pretending seller acceptance or comparative market sufficiency is known.
- Adds Studio Verify doctor and validator for rights/control invariants.

## Known bounded gaps
- Current NHL provider association establishes current organizational relationship but not every exact underlying SPC/unsigned-rights mechanism or expiry date.
- Complete NHL draft-pick ownership is not yet acquired on this path.
- Full Toronto SPC/cap ledger remains a separate known evidence gap.
