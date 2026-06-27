# Sports Intelligence Engine — v0.4.3

## Release Name

Scout Connection + Context Routing

## Summary

This release turns Scout from a passive viewer into the local entry point for Fantrax fantasy-league analysis.

Scout can now accept Fantrax connection details, save local workspace/secrets files, test the connection, infer context from league data, run the full Athena analysis pipeline, and route questions through either Fantasy League or Public Sports mode.

## Added

- Fantrax connection panel.
- League ID input.
- Auth cookie / secret input.
- Test Connection endpoint.
- Context inference from Fantrax league info.
- Fantasy League / Public Sports mode switch.
- Analyze League full pipeline execution.
- Public Sports placeholder routing.
- Improved Scout context pills.

## Changed

- Analyze League now refreshes Athena outputs before showing results.
- Scout no longer reports 0 managers/transactions when canonical outputs can be rebuilt.
- Manager activity answers now support the v0.3.1 nested `observed_facts` / `inferred_profile` structure.

## Validation

- Compile check passed.
- Scout context loading passed.
- Analyze League response now reads 12 managers / 92 transactions from existing outputs.
- Public Sports routing returns a clear limitation-aware response.

## Known Limitations

- Fantrax finance page remains future work.
- Public NHL/NHLPA/CBA reasoning remains future work.
- Browser-cookie authentication remains local-alpha only.
