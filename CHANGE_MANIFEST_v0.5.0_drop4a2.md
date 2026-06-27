# Athena v0.5.0 Drop 4A.2 — Scout Chat Layout & Fantrax Auth Bridge

## Purpose
Improve Scout's human reading flow after authenticated Fantrax transaction validation proved successful.

## Changes
- Moves the Scout prompt into a sticky bottom prompt dock.
- Keeps the conversation above the prompt so newest responses appear directly above the input.
- Adds visible messaging that manual Cookie header entry is an advanced validation bridge, not the final Fantrax auth UX.
- Adds an `Open Fantrax Login` button and local endpoint to open Fantrax in the system browser as the first step toward a guided session-capture flow.
- Updates single version source to `0.5.0-drop4a2` / `v0.5.0-drop4a2`.

## Validation
Run:

```python
runfile(
    "Tests/validate_scout_chat_layout_and_auth_bridge.py",
    wdir=r"F:\Development\Athena"
)
```
