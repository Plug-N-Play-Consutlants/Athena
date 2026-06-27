# Athena v0.5.0-drop4d4c — Historical Context Graph Integration

## Added

- `Knowledge/Graph/historical_integration.py`
  - Builds `canonical_context_graph_with_historical_intelligence.json`.
  - Starts from the canonical 4C context graph.
  - Rebuilds/reads 4D.3f historical signal graph outputs.
  - Rebuilds/reads 4D.4b historical intelligence graph outputs.
  - Converts historical signal and historical intelligence nodes into canonical graph nodes.
  - Converts bridge relationships into canonical graph relationships.
  - Normalizes `entity:<id>` bridge endpoints back to canonical entity IDs where possible.

- `Tests/validate_context_graph_historical_integration.py`
  - Validates historical nodes/relationships are integrated into the canonical context graph export.

- `Tools/doctor_context_graph_historical_integration.py`
  - Doctor for 4D.4c historical graph integration.

## Outputs

- `Output/canonical_context_graph_with_historical_intelligence.json`
- `Output/canonical_context_graph_with_historical_intelligence_summary.json`

## Validation

Run:

```python
runfile("Tests/validate_context_graph_historical_integration.py", wdir=r"F:\\Development\\Athena")
runfile("Tools/doctor_context_graph_historical_integration.py", wdir=r"F:\\Development\\Athena")
```
