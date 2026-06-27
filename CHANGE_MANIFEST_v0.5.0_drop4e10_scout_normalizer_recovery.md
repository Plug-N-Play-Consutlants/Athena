# Athena v0.5.0-drop4e10 — Scout Normalizer Recovery

## Purpose
Recover from the regressed drop4e9 state using the known-good Scout startup/UI path and add first-pass Scout query normalization.

## Changes
- Fixed Scout version rendering by replacing `{SCOUT_VERSION}` at response time.
- Escaped the JavaScript string containing `Athena\'s` so button binding is not killed by a syntax error.
- Fixed Fantrax connection workspace update collision where inferred provider metadata could pass `provider` twice.
- Added Scout query normalization so `Analyze Auston Matthews`, `Tell me about Auston Matthews`, and `Auston Matthews` route to the same player analysis path.
- Added fuzzy player matching for typo tolerance such as `Austin Mathtwes`.
- Added ambiguity handling for shared names such as Sebastian Aho; Scout now asks which player instead of collapsing identities.
- Added fallback guidance so any user input receives either an answer or a clarifying question.

## Files
- Core/version.py
- Scout/app.py
- Scout/conversation/router.py
- Athena/connect.py
