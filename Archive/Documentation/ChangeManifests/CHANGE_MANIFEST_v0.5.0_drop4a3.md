# Athena v0.5.0-drop4a3 — Public Hockey Knowledge Source Registry

## Objective
Register the NHL Official Rules and NHL/NHLPA MOU as deterministic public hockey knowledge sources that can be consumed by both Public Sports and Fantasy League intelligence modes.

## Added
- `Knowledge/Sources/public_hockey_registry.py`
  - source metadata registry
  - topic pointers for game rules, injuries, penalties, game flow, salary cap, LTI/LTIR, waivers, no-trade lists, retention, contract variability, contract term, recalls, and supplementary discipline
  - document presence detection
  - deterministic topic lookup
- `Tools/register_public_hockey_sources.py`
  - writes `Output/public_hockey_knowledge_registry.json`
  - writes `Reports/public_hockey_knowledge_registry_report.txt`
- `Tests/validate_public_hockey_knowledge_registry.py`
- `Core/version.py` updated to `0.5.0-drop4a3`

## Notes
This patch does not bundle copyrighted source PDFs. Place local copies in:

`Knowledge/Sources/Documents/`

Expected filenames:
- `nhl.pdf`
- `NHLPA-NHL-MOU-June-27-2025.pdf`

The registry works as metadata-only without PDFs and becomes document-backed when the files are present.
