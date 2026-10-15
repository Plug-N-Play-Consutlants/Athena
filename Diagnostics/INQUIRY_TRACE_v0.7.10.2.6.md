# v0.7.10.2.6 — Request execution diagnostic contract

This is an **instrumentation-only** release. It deliberately does not change routing, evidence selection, specialist execution, fallback behavior, or public response composition.

## What is measured

On a successful `Athena.request_execution.execute_request()` call, inspect `answer.developer.inquiry_execution_trace`:

- `selection.route`, `selection.selected_by`, `selection.registered`: chosen route, selection mechanism, and registry presence.
- `invocation.owner`, `invocation.handler`, `invocation.completed`, `invocation.duration_ms`: selected specialist or legacy adapter, with elapsed time.
- `evidence.status`, `evidence.sources`, `evidence.missing`, `evidence.attached_to_context`, `evidence.acquisition_duration_ms`: request-scoped acquisition and handoff.
- `result.intent`, `result.confidence`, `result.public_fields_present`, `result.limitations_present`: output characteristics, not an independent quality score.
- `result.inquiry_completeness_verified` and `result.evidence_consumption_verified`: **always false** until verified by a separate requirement/consumption audit. Do not interpret a specialist's confidence as whole-inquiry confidence.
- `continuation` and `total_duration_ms`: context rewriting decision and request execution time.

No question text, raw source material, credentials, or private league data are duplicated in this trace. The pre-existing answer and diagnostic payloads are unchanged otherwise.

## Known boundaries / why this is not a complete lifecycle trace

- This trace covers calls that reach `Athena.request_execution.execute_request()`. A Scout path that bypasses this entry is not observed. Compare with existing Scout session diagnostics to identify bypasses.
- The trace is attached only after a successful specialist return. Exceptions are not recorded here; existing error/Doctor mechanisms still own failure diagnostics.
- `sources` indicates bundle acquisition, **not evidence consumption by the specialist**.
- `completed` means the handler returned, **not that all inquiry clauses were answered**.
- This version does not introduce multi-specialist orchestration, follow-up repair, or live acquisition.

## Studio regression protocol

Run the same four prior questions, unchanged, in the relevant public/fantasy modes, then export the Scout session log. Compare `developer.athena_request` and `developer.inquiry_execution_trace` for each turn. If the trace is absent, investigate whether the response bypassed the Athena request boundary, or whether the session export strips the diagnostic field. Compare route, source inventory, missing items, confidence and actual answer coverage; do not equate a missing trace with a proven bypass.

## Automated acceptance

`python Tests/validate_inquiry_trace_contract.py` exercises registered specialist and legacy adapter cases hermetically. CI now runs this test in addition to its existing smoke and hygiene checks. This is a diagnostic contract regression, not a semantic completeness certification.
