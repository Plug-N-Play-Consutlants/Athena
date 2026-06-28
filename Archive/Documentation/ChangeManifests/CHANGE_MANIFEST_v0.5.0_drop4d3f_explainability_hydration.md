# Athena v0.5.0-drop4D3f Explainability Hydration Hotfix

Hydrates Historical Graph Bridge nodes with the verified 4D.3e historical signal explainability package.

## Replacement files
- Knowledge/Historical/graph_bridge.py
- Tests/validate_historical_graph_bridge.py
- Tools/doctor_historical_graph_bridge.py

## Fix
- Corrects graph bridge import from the nonexistent `explainability_engine.HistoricalSignalExplainabilityEngine` path to the verified `confidence_engine.HistoricalExplainabilityEngine` path.
- Uses `.to_dict()` from the 4D.3e package instead of `.serialize()`.
- Tightens validation/doctor checks so explainability must be hydrated, not merely present as a key.

## Validation
```python
runfile("Tests/validate_historical_graph_bridge.py", wdir=r"F:\Development\Athena")
runfile("Tools/doctor_historical_graph_bridge.py", wdir=r"F:\Development\Athena")
```
