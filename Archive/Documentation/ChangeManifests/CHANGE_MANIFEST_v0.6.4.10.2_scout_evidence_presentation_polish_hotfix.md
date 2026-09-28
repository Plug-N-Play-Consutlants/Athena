# v0.6.4.10.2 — Scout Evidence Presentation Polish Hotfix

## Scope
Public Scout evidence-presentation polish only. Fantasy intelligence and Investigate Further behavior are unchanged.

## Changes
- Explicitly enforce collapsed hidden state for More Results despite the shared source grid display rule.
- Preserve toggle behavior between More Results and Fewer Results.
- Derive publisher metadata from discovery article titles when the upstream source label is the internal Current News Discovery adapter.
- Remove the publisher suffix from the displayed headline when it is promoted to publisher metadata.
- Format parseable RSS dates as concise user-facing dates.
- Replace result-count/engine language with a natural coverage introduction.

## Validation
Covered by the Scout evidence-presentation validator and existing public/Scout regression validators.
