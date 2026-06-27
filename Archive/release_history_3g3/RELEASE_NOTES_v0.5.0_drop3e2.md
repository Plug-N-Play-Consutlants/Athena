# v0.5.0 Drop 3E.2 — Fantrax Provider Adapter

## Purpose

Introduces the first concrete provider adapter under the provider contract established in 3E.1.

## Added

- `Providers/Fantrax/fantrax_provider.py`
- `Tests/validate_fantrax_provider_adapter.py`

## Updated

- `Providers/Fantrax/__init__.py`
- `Providers/base/registry.py`

## Behavior

- Fantrax is now registered in the provider registry as `fantrax`.
- `FantraxProvider` wraps the existing `FantraxClient`.
- Existing Fantrax fetch/build logic is not changed.
- Athena and Scout behavior are not changed in this drop.

## Notes

The project root may be renamed from `Sports_Intelligence_Engine_2.0` to `Athena`. The code in this patch derives paths from file locations and does not hardcode either root folder name.

- Adds `Core.config.reload_configuration()` compatibility hook required by Athena runtime modules.
