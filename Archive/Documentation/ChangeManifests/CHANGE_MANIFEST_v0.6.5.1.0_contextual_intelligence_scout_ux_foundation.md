# v0.6.5.1.0 — Contextual Intelligence & Scout UX Foundation

## Scope
- Distinguish single-entity temporal comparison from two-entity player comparison.
- Keep generated current-event investigation prompts on live Event Intelligence.
- Route natural fantasy phrasing such as `Analyze my draft` to existing pre-draft intelligence.
- Establish a sport-neutral comparison/relationship semantics contract; NHL is the first intended domain implementation, not a hard-coded architecture.
- Humanize canonical underscore enums in Scout cards and contain long card/prompt values.
- Remove residual `per active manager` presentation wording.
- Add Studio-accessible regression validation for contextual routing and Scout UX.

## Relationship semantics foundation
Comparison shape is classified as temporal, entity, relationship, or unresolved. The relationship evidence contract reserves opponent history, teammate history, shared events, organizational overlap, head-to-head performance, career intersections, documented connections, and cultural/media intersections. No incomplete relationship-intelligence response route is exposed in this release.

## Regression protection
Validated against the session-derived prompts for Matthews career baseline, Matthews vs McDavid, the Maple Leafs/Marchenko investigation, and `Analyze my draft`, plus existing Scout runtime, fantasy contextual routing, Fantrax league-context, normal-response composition, lifecycle, and comparison validators.
- Studio correction: generalized two-player comparison subject resolution to accept canonical public profiles or reconciled lifecycle identities, preventing valid pairs such as Auston Matthews vs Gavin McKenna from falling back to single-player analysis.

## Investigative scenario intelligence contract
Generated investigation prompts are executable analytical contracts, not decorative follow-ups. A focused claim now preserves separate states for the reported claim, corroboration/contradiction, contextual feasibility, bounded scenario analysis, bilateral impact, the current conclusion, and evidence that would revise that conclusion.

The contract explicitly prevents several invalid shortcuts:
- uncorroborated does not mean false;
- plausible does not mean true;
- repetition does not automatically equal independent corroboration;
- source prestige is evidence metadata rather than a truth verdict;
- a later outcome does not retroactively invalidate a conclusion that was properly bounded to the evidence available at the time;
- a defensible conclusion may be superseded when new evidence arrives.

For acquisition or transaction claims, scenario analysis is bilateral. The analytical target is not merely whether the acquiring organization could add the asset, but what financial/contract load must be absorbed, what roster or organizational constraint changes, what assets could realistically move, what the counterparty loses or needs in return, and whether a resulting structure is rules-compliant and mutually coherent. These are explicitly scenario questions until transaction evidence establishes them as facts.

### Temporal investigative case-study requirement
The Pablo Torre / Kawhi Leonard / Los Angeles Clippers reporting sequence is retained as an architecture case study for temporal evidence reasoning, not as basketball-specific logic. Athena must be able to preserve a defensible evidence-state conclusion at each historical point as reporting, skepticism, contradictory information, investigative findings, objections, and later resolution evolve. Earlier analysis is judged against what was knowable then, not against hindsight. The same contract applies to trade rumors, organizational investigations, financial claims, ownership questions, injuries, and other evolving sports claims.

This release establishes the reusable contract and bounded Scout composition. It does not claim that all future contract, cap, roster, finance, rules, relationship, or transaction providers are already attached. Those providers should plug into this contract rather than creating claim-specific response paths.
