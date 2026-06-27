# v0.4.0 — Scout Alpha

## Summary

Introduces Scout, the first minimal local experience layer powered by Athena Engine.

This release intentionally prioritizes usability over polish. The goal is to let a user open a browser, ask a small set of natural questions, click Analyze League, and see Athena's current deterministic outputs without reading JSON files.

## Naming locked conceptually

- Athena Engine: deterministic sports intelligence engine.
- Scout: prompt/conversation and experience layer.
- Brand relationship: Scout, powered by Athena Engine.
- Philosophy: Athena thinks. Scout communicates.

## Added

- `Scout/app.py` local Streamlit UI.
- `Scout/conversation/context.py` output context loader.
- `Scout/conversation/router.py` deterministic alpha question router.
- `Scout/conversation/responses.py` response helper format.
- `Scout/README.md` run instructions and scope.
- `Tests/validate_scout_alpha.py` router validation without Streamlit dependency.

## Scout Alpha capabilities

- Ask Scout with a simple input box.
- Analyze League button.
- Developer Mode toggle.
- Answer format:
  - Engine Conclusion
  - Observed Facts
  - Known Limitations
- Developer Mode shows:
  - intent
  - context loaded
  - knowledge used
  - intelligence used
  - files read
  - missing or limited domains

## Supported first questions

- Who are the most active managers?
- Show the league market.
- Show expiring contracts.
- Compare Alien Agenda to league average.
- What are the known limitations?
- Analyze my league.

## Known limitations

- Scout Alpha uses deterministic templates, not generative explanation.
- The Fantrax finance page is not integrated yet.
- Team context detection is intentionally basic.
- Public Sports profile is not wired yet.
- Production authentication and multi-user state are not implemented.

## Run

From the project root:

```bash
streamlit run Scout/app.py
```

If Streamlit is missing:

```bash
pip install streamlit
```
