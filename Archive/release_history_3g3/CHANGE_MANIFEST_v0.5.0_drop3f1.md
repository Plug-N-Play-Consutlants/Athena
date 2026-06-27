# CHANGE MANIFEST — v0.5.0 Drop 3F.1

## Sprint
3F.1 — Scout Connection Feedback & Workspace Prefill Stabilization

## Purpose
Prevent Scout from failing quietly during Fantrax connection tests and reduce confusion caused by stale provider-registry placeholder league IDs in the connection form.

## Changed Files
- `Scout/app.py`
- `Scout/run_scout.py`
- `Athena/workspace.py`
- `Tests/validate_scout_connection_feedback.py`
- `Reports/scout_connection_feedback_validation_report.json`
- `Reports/scout_connection_feedback_validation_report.txt`

## Functional Changes
- Added visible connection status feedback inside Scout's Fantrax connection panel.
- Changed the connection button label to `Test & Save Connection`.
- Connection attempts now show an in-progress state and always end with a visible success/failure message.
- Scout's local POST helper no longer throws away failed response bodies before the UI can render them.
- Ask/sync/connect actions now render visible error cards instead of silently stopping.
- Scout recognizes `test_league_id_provider_registry` as a stale placeholder.
- Scout now prefills the Fantrax League ID field from the effective configured league ID when the workspace still contains a placeholder.
- Scout warns when it is ignoring a stale placeholder and prompts the user to test/save the real connection.
- Version bumped to `v0.5.0-drop3f1` / `0.5.0-drop3f1`.

## Validation
Run from repository root:

```python
runfile(
    "Tests/validate_scout_connection_feedback.py",
    wdir=r"F:\\Development\\Athena"
)
```

Expected result:

```text
Overall status: PASS
Passed: 7
Warnings: 0
Failed: 0
```

## Notes
This patch does not implement a new Fantrax authentication/session strategy. It only makes the current alpha connection path observable and easier to validate.
