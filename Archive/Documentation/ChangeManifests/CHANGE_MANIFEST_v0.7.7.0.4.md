# v0.7.7.0.4 — Acceptance Observability Hotfix

## Purpose
Make Scout acceptance logs distinguish the browser-visible response from Athena/Scout's internal structured execution result.

## Changes
- Browser posts the actual rendered answer text back to the session transcript after each successful ask.
- Session turns record normal vs developer presentation mode.
- TXT export prints USER-VISIBLE RESPONSE first and INTERNAL EXECUTION RESULT separately.
- JSON export retains both `user_visible_text` and the complete internal `answer` payload.
- Missing browser capture is explicit rather than silently substituting internal evidence.

## Acceptance intent
A temporal comparison whose internal result contains season rows but whose normal UI shows only a coverage sentence must be diagnosable as presentation loss directly from one exported session log.
