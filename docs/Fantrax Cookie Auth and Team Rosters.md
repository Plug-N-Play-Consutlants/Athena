# Fantrax Cookie Auth and Team Rosters

## Purpose

Fantrax league-specific state should be live where possible:

- fantasy ownership
- roster status
- waiver/free-agent state
- contract expiry year
- team roster membership

The engine now tests the likely live route:

```text
general/getTeamRosters
```

It also tests:

```text
general/getLeagueInfo
```

as a fallback source for embedded roster/player data.

## Authentication

Private leagues may require browser-session authentication. Do not paste cookies into ChatGPT and do not commit them to source control.

Preferred local setup in Command Prompt:

```bash
set FANTRAX_COOKIE=your_cookie_header_here
```

PowerShell:

```powershell
$env:FANTRAX_COOKIE="your_cookie_header_here"
```

Then rerun:

```python
runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Providers/Fantrax/fetch/fetch_player_pool.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)
```

Alternative local-only config:

```json
{
  "provider": {
    "auth": {
      "cookie": "your_cookie_header_here"
    }
  }
}
```

Use a local ignored config file if the project later adds one.

## Expected Behavior

If live access works:

```text
Source Type: fantrax_live_team_rosters
Live Source: True
Rows: > 0
```

If live access fails, the module falls back to:

```text
Raw/Fantrax-Players*.csv
```

and marks:

```text
Live Source: False
```

## Diagnostics

Review:

```text
Logs/fantrax_player_pool_fetch.json
```

It records which endpoint/method/params were tried, whether cookie auth was attached, and any Fantrax error payloads. It does not print or store the cookie value.
