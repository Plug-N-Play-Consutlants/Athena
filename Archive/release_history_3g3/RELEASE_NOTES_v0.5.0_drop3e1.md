# v0.5.0 Drop 3E.1 — Provider Foundation + Diagnostics

## Purpose

Introduce the provider-neutral foundation and diagnostics primitives required before migrating Fantrax and future providers onto a single connection lifecycle.

## Added

- `Providers/base/`
  - `provider.py`
  - `registry.py`
  - `session.py`
  - `connection_state.py`
  - `events.py`
  - `__init__.py`
- `Diagnostics/`
  - `diagnostics.py`
  - `events.py`
  - `trace.py`
  - `__init__.py`
- `Tests/validate_provider_foundation.py`

## Behavior change

None. This patch does not alter Scout, Athena connection behavior, or Fantrax runtime behavior.

## Validation

`Tests/validate_provider_foundation.py` passed 6/6 checks in the build environment.
