# Athena Alpha UX Lockdown — v0.5.0-drop4e5

## Locked runtime direction
Athena should launch as a simple desktop-style app, not as a Python script. The immediate target remains a BAT launcher, followed by a lightweight executable launcher with: Launch Scout, Stop Scout, Open Browser, Run Doctor, Run Validator, View Logs, and visible runtime status.

## Scout UI stabilization
Scout controls must render responses inside the Scout page. Browser alert popups are not acceptable for normal answers. Button actions must be explicitly bound, wrapped with visible error handling, and resilient to context-load failures.

## Provider defaults
Public Sports is the default provider mode. A user may switch to Fantrax or another provider when they want league-specific/private context.

## Fantrax credential language
Fantrax's private league value should be labeled Personal/Profile Secret ID, not Fan League Secret. League ID and Personal/Profile Secret ID may be shown as guided setup fields. Browser cookies should not be exposed as a normal user concept. Cookie/session capture should move behind a Connect Fantrax authentication flow.

## Future Fantrax auth UX
The desired path is: Connect Fantrax → user logs in through browser/auth flow → Athena detects or receives browser session credential → Athena stores credentials externally → Scout syncs league data. Manual Cookie header entry remains development-only.

## Player experience direction
Scout should become useful and fun. Player questions should eventually show a player header with name, team, position, and relevant stats; an Athena description; a Scout translation; and a Profile button that opens a sports-card-style profile. Future enhancement may include NHL photos and richer visual profile cards.
