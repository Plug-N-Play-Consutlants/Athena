# Athena v0.5.0 drop4d4b fix3

## Files
- REPLACE `Knowledge/Historical/intelligence_graph_bridge.py`

## Purpose
- Make source signal extraction tolerant of actual 4D.4 historical intelligence payload shapes.
- Fall back to `Output/historical_intelligence.json` when needed.
- Preserve validator/doctor compatibility.
