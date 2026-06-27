# Change Manifest — v0.5.0-drop3e4.2

## Sprint
3E.4.2 — Scout Evaluation Trace Binding

## Purpose
Bind Scout's supported questions to Athena's deterministic Evaluation Engine and expose the required Developer Mode trace fields without adding Fantrax session/auth work.

## Scope
- Scout routes supported fantasy questions through `Intelligence/evaluation_engine.py`.
- Developer Mode exposes:
  - Question
  - Context
  - Provider
  - Intent
  - Modules Executed
  - Evidence Used
  - Confidence
  - Evaluation
  - Natural Language Response
- Public sports mode remains bounded and intentionally shallow until public rule books and richer NHL data exist.
- Transaction authentication remains a known provider capability limitation and is not required for this validation.

## Files Changed
- `Athena/__init__.py`
- `Intelligence/evaluation_engine.py`
- `Scout/conversation/router.py`
- `Scout/conversation/responses.py`
- `Tests/validate_scout_evaluation_trace_binding.py`

## Validation
Run:

```bash
python Tests/validate_scout_evaluation_trace_binding.py
```

Expected result:

```text
Overall status: PASS
Passed: 9
Warnings: 0
Failed: 0
```

The broader end-to-end validation may still fail on Fantrax transactions if the current session/cookie is not authenticated. That is expected and separate from this trace-binding patch.
