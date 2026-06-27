# Athena v0.5.0-drop4a5 — Public Hockey Knowledge Retrieval

## Purpose
Expose deterministic retrieval over compact public hockey knowledge packs so Scout can answer public hockey rule/CBA questions from bounded evidence instead of falling back to a generic “public mode planned” response.

## Added
- `Knowledge/Sources/public_hockey_retrieval.py`
  - Loads compact packs under `Knowledge/Packs/NHL/...`.
  - Retrieves evidence by topic/token match.
  - Supports both `public_sports` and `fantasy_league` modes.
  - Returns source, authority, section/provision reference, summary, confidence, and limitations.
  - Provides a Scout-style bounded answer shape and Developer Mode trace.
- `Tools/query_public_hockey_knowledge.py`
  - Spyder/CLI-friendly query tool for testing pack retrieval.
- `Tests/validate_public_hockey_knowledge_retrieval.py`
  - Validates LTIR, waivers, icing, fantasy access to public hockey knowledge, bounded unsupported questions, retrieval reports, and version.

## Changed
- `Core/version.py` updated to `0.5.0-drop4a5` / `v0.5.0-drop4a5`.

## Notes
- This patch does not implement full cap/LTIR/waiver calculations.
- It creates the retrieval bridge needed for Scout and future intelligence modules to use authoritative NHL/NHLPA knowledge packs.
- Source PDFs remain staging artifacts only; runtime retrieval reads compact JSON packs.
