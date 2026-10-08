# AthenaEngine v0.7.7.3.4 - Validator Version Contract Hotfix

## Scope
- Replaces stale exact-hotfix assertions in the v0.7.7 validator family with monotonic semantic-version checks.
- Preserves the v0.7.7.3.2 Whole-Picture fix and v0.7.7.3.3 validator alignment intent.
- No runtime reasoning, routing, evidence, or Scout presentation behavior changed.

## Root cause
The prior overlay updated canonical version metadata and expected version strings but left independent assertions requiring RELEASE_HOTFIX == 1. Those assertions necessarily fail on later hotfixes.

## Verification contract
Validators now accept the current build and later hotfixes rather than encoding a contradictory fixed hotfix number.
