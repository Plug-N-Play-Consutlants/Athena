# Scout Alpha

Scout is the minimal local experience layer powered by Athena Engine.

Athena performs deterministic analysis. Scout communicates Athena's results through a simple browser interface.

## Run from Spyder

```python
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Scout/run_scout.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
```

The launcher starts a local server and opens:

```text
http://localhost:8765
```

No Streamlit, FastAPI, Node, React, or external web framework is required for this alpha.

## Current capabilities

- Ask Scout a supported question.
- Analyze League with one click.
- View answers as Engine Conclusion, Observed Facts, and Known Limitations.
- Toggle Developer Mode to inspect intent/context/module metadata.

## Current supported prompts

- `Analyze my league`
- `Who are the most active managers?`
- `Show the league market`
- `Show expiring contracts`
- `Compare Alien Agenda to league average`
- `What are the known limitations?`

Scout Alpha intentionally starts simple. Unsupported questions return guidance instead of invented answers.

## v0.4.3 Notes

Scout now includes a simple Fantrax connection panel.

Required user-entered connection fields:

- Fantrax League ID
- Fantrax auth cookie / secret

Scout/Athena infer sport, season, league name, team count, and available rule context from the Fantrax league response where possible.

The Analyze League button now runs the canonical Athena pipeline before rendering the response.

## v0.4.3 Notes

Scout now includes a simple Fantrax connection panel.

Required user-entered connection fields:

- Fantrax League ID
- Fantrax auth cookie / secret

Scout/Athena infer sport, season, league name, team count, and available rule context from the Fantrax league response where possible.

The Analyze League button now runs the canonical Athena pipeline before rendering the response.
