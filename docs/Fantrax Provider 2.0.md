# Fantrax Provider 2.0

Sprint 1 promotes Fantrax from a collection of fetch scripts into a more mature provider adapter while preserving the locked platform architecture.

## Scope

This sprint stays entirely inside the Provider layer.

It does not change the platform pipeline:

Fetch → Build → Knowledge → Intelligence → AI

## Added Provider Components

```text
Providers/Fantrax/
    auth/
        session.py
        cookie_manager.py
        auth_validator.py
    endpoints.py
    diagnostics.py
```

## Responsibilities

### auth/session.py

Creates a Fantrax `requests.Session` with browser-compatible headers and local-only authentication cookies.

### auth/cookie_manager.py

Loads a browser-session cookie from one of the supported local configuration sources:

- `FANTRAX_COOKIE`
- `provider.auth.cookie`
- `provider.cookie`
- `provider.headers.Cookie`
- `provider.headers.cookie`

Cookie values are never logged.

### auth/auth_validator.py

Detects Fantrax authentication failures such as `WARNING_NOT_LOGGED_IN` and returns deterministic diagnostics.

### endpoints.py

Centralizes provider endpoint defaults and Fantrax `fxpa/req` method names.

### diagnostics.py

Produces provider configuration and authentication diagnostics without parsing league data.

## Transactions

Fantrax transaction history is served through the private web-message endpoint:

```text
https://www.fantrax.com/fxpa/req
```

using method:

```text
getTransactionDetailsHistory
```

The fetch layer saves the raw provider payload to:

```text
Raw/transactions.json
```

Normalization remains the responsibility of the Build layer.

## Authentication Note

Transaction history requires a valid browser-session cookie from `www.fantrax.com`. This should remain local and must not be committed to source control.
