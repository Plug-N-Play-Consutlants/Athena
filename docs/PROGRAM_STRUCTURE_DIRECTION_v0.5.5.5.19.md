# Program Structure Direction — v0.5.5.5.19

## Principle

Do not reorganize the repository until the evidence path is traceable. Structural cleanup should follow the audit, not precede it.

## Current problem

The repository has accumulated multiple namespaces during rapid Epic 5 development:

```text
Engine/
Intelligence/
Reasoning/
Knowledge/Intelligence/
Scout/conversation/
```

These are not all wrong, but their boundaries are not yet crisp enough. Moving files before defining responsibilities would risk breaking validated behavior while preserving the same conceptual confusion under new paths.

## Target responsibility model

```text
Apps
  Studio and Scout UI/runtime adapters only.

Core
  Versioning, logging, configuration, shared runtime primitives.

Providers
  External-source acquisition and provider-specific normalization.

Knowledge
  Durable facts, public profiles, identity graph, historical data, graph data.

Evidence
  Source-backed bundles, confidence, event sourcing, extraction, provenance.

Reasoning
  Domain analysis over evidence bundles.

Composition
  Public/developer/acceptance answer shaping.

Runtime
  Orchestration, traceability, evidence ledger, diagnostics.

Ops
  Doctors, validators, maintenance commands.
```

## Proposed future structure

```text
src/athena_engine/
  apps/
    studio/
    scout/
  core/
  providers/
  knowledge/
  evidence/
  reasoning/
  composition/
  runtime/
  ops/

tests/
  unit/
  integration/
  acceptance/

docs/
  architecture/
  route_maps/
  history/

workspace/       # local/gitignored
  raw/
  output/
  reports/
  logs/
```

## Do not do yet

- Do not move runtime packages until the first evidence-path vertical slice passes.
- Do not delete `Engine/`, `Intelligence/`, or `Reasoning/` based only on naming overlap.
- Do not replace deterministic routing with a broad natural-language planner until route contracts exist.

## First structural cleanup candidates after audit

1. Move generated reports/logs/output out of the active source tree or gitignore them.
2. Move old change manifests and retired files into `docs/history` or external archive storage.
3. Ensure root-level Python files are launchers or shims only.
4. Consolidate event confidence/timeline/summary into the public live-event Scout path.
5. Reduce `Scout/conversation/router.py` to orchestration and dispatch only.
