# Engineering Principles

## Architecture First

All development follows the canonical pipeline:

```text
Providers → Fetch → Build → Knowledge → Reasoning → Intelligence → Context Selection → Response Composition → Experience → Discovery → Scout
```

No future work should bypass the pipeline.

## Module-Adaptive Design

Athena should be module-adaptive, not module-dependent.

New capabilities should be inserted through contracts, registries, adapters, orchestration hooks, validation gates, and shared context interfaces. The existing structure should discover, evaluate, route, and compose registered module outputs rather than ignore them or require hard-coded rewrites.

Preferred implementation patterns:

- Registries over imports.
- Contracts over hardcoding.
- Adapters over rewrites.
- Capability discovery over hidden feature flags.
- Validation gates over assumptions.
- Shared context objects over one-off payloads.
- Composition hooks over custom responses.

## Module Insertion Contract

Every expandable module should declare:

- Module identity.
- Capability family.
- Supported sports and domains.
- Required inputs.
- Produced outputs.
- Evidence contract.
- Context contract.
- Reasoning hooks.
- Composition hooks.
- Validation gates.
- Limitations.

## Deterministic First

Athena's core behavior should be deterministic and validated. AI may explain, synthesize, and communicate, but it should not silently replace evidence collection, pipeline state, or validation.


## Adaptive Investigation Contracts

Investigation strategy is declarative. New intents and experiences should register strategy requirements rather than hard-code module calls. Capability requirements are resolved through module contracts and registries. A concise update strategy must not globally reduce rich profile or comparison composition. A rich strategy must not force every prompt into exhaustive analysis.
