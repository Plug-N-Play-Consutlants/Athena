# Athena v0.5.0-drop4b1 — Sprint 4B.1 Player Intelligence Foundation

## Summary
Introduces Athena's first canonical entity intelligence module: Player Intelligence. The module evaluates a player using existing public NHL and fantasy-provider outputs without fetching new data or inventing unsupported facts.

## Added
- `Intelligence/Player/player_intelligence.py`
  - canonical player matching
  - identity profile
  - production profile
  - fantasy profile
  - contract profile
  - availability profile
  - trajectory classification
  - confidence calculation
  - bounded no-match behavior
- `Intelligence/Player/__init__.py`
- `Tools/query_player_intelligence.py`
- `Tests/validate_player_intelligence_foundation.py`

## Changed
- `Scout/conversation/router.py`
  - binds “Tell me about …” style player questions to Player Intelligence
  - supports public and fantasy mode player evaluation
  - exposes player evaluation in Developer Mode
- `Core/version.py`
  - updated to `0.5.0-drop4b1`

## Validation
Run:

```python
runfile(
    "Tests/validate_player_intelligence_foundation.py",
    wdir=r"F:\Development\Athena"
)
```

Expected result: PASS 11/11.

## Notes
This sprint does not add line deployment, schedule strength, injury modeling, future projection, betting, or trade logic. It establishes the reusable evaluation object pattern for future intelligence modules.
