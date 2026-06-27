# Release v0.4.2 — Scout Local Web Foundation

## Purpose

Rebuild Scout Alpha away from Streamlit into a zero-dependency local web application that better reflects the long-term Scout/Athena architecture.

Scout remains intentionally simple: one page, one question box, one Analyze League action, and Developer Mode.

## Naming/architecture

- Athena Engine is the deterministic intelligence engine.
- Scout is the experience/conversation layer.
- Athena thinks. Scout communicates.

## Added / Changed

- Replaced Streamlit Scout app with a minimal local web application using Python's standard library.
- Added local JSON API endpoints:
  - `GET /api/context`
  - `POST /api/ask`
  - `POST /api/analyze`
- Updated `Scout/run_scout.py` so Spyder launches Scout without Streamlit or command-line use.
- Updated Scout README with the new local launch flow.
- Preserved the existing deterministic Scout question router.
- Preserved Developer Mode metadata in responses.

## Removed dependency

- Scout Alpha no longer requires Streamlit.
- No FastAPI, Flask, Node, React, or frontend build tooling is required.

## Run

```python
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Scout/run_scout.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
```

Then open:

```text
http://localhost:8765
```

The launcher opens this automatically.

## Validation

- Compile check passed.
- Scout Alpha deterministic router validation passed.
- Standard-library web server import check passed.

## Known limitations

- Scout Alpha is local only.
- Conversation history is browser-session only.
- Supported questions are still template-routed.
- Authentication/user accounts are not implemented.
- Finance page is not yet fetched as the authoritative money source.
