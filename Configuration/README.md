# Configuration

The platform separates shared configuration, workspace context, and local secrets.

## Files

- `config.json` — shared non-secret provider/platform settings.
- `workspace.json` — active workspace context, such as league ID, sport, and season.
- `secrets.local.json` — local-only secrets. This file is ignored by Git.
- `secrets.example.json` — committed template showing the expected secret shape.

## Fantrax cookie

Private Fantrax endpoints, including transaction history, require a logged-in browser-session cookie.

Create `Configuration/secrets.local.json` from `Configuration/secrets.example.json` and paste the Fantrax request cookie there:

```json
{
  "fantrax": {
    "cookie": "PASTE_FANTRAX_COOKIE_HERE"
  }
}
```

Do not commit `secrets.local.json`.
