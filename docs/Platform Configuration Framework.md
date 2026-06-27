# Platform Configuration Framework

Sprint 1.1c introduces a standardized configuration and local-secrets convention.

## Configuration Files

```text
Configuration/
├── config.json
├── workspace.json
├── secrets.local.json
├── secrets.example.json
└── README.md
```

## Rules

- Shared provider/platform settings live in `config.json`.
- Active league/workspace settings live in `workspace.json`.
- Secrets live in `secrets.local.json`.
- `secrets.local.json` is ignored by Git and should never be committed.
- Providers access secrets through `Core.config.get_secret_value()`.

## Core API

`Core/config.py` exposes:

- `get_config_value()`
- `get_workspace_value()`
- `get_secret_value()`
- `reload_configuration()`

Providers should not read JSON configuration files directly.

## Fantrax

Private Fantrax endpoints, including transaction history, require a browser-session cookie. Store it in:

```json
{
  "fantrax": {
    "cookie": "PASTE_FANTRAX_COOKIE_HERE"
  }
}
```

The Fantrax provider reads this using:

```python
get_secret_value("fantrax.cookie")
```
