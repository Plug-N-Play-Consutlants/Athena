# Athena v0.5.0-drop4a4 — Public Hockey Knowledge Pack Builder

## Purpose
Convert public hockey authority documents from heavyweight source artifacts into compact, versioned runtime knowledge packs.

## Added
- `Knowledge/Sources/public_hockey_packs.py`
  - Builds compact JSON knowledge packs from the 4A.3 source registry.
  - Records document fingerprints when source PDFs are present.
  - Writes manifest, body, and topic index files for each source.
  - Exposes pack status for Doctor/debug integrations.
- `Tools/build_public_hockey_knowledge_packs.py`
  - CLI/Spyder-friendly builder for public hockey packs.
- `Tests/validate_public_hockey_knowledge_packs.py`
  - Validates pack creation, expected directories, manifest types, document-backed status, topic indexes, body files, summary output, and version.

## Changed
- `Core/version.py` updated to `0.5.0-drop4a4` / `v0.5.0-drop4a4`.
- `Tools/register_public_hockey_sources.py` now avoids stale “place PDFs” wording when source documents are already present.

## Runtime Output
Generated when the builder runs:
- `Knowledge/Packs/NHL/rulebook/2025_2026/manifest.json`
- `Knowledge/Packs/NHL/rulebook/2025_2026/rules.json`
- `Knowledge/Packs/NHL/rulebook/2025_2026/topic_index.json`
- `Knowledge/Packs/NHL/cba/2025_mou/manifest.json`
- `Knowledge/Packs/NHL/cba/2025_mou/provisions.json`
- `Knowledge/Packs/NHL/cba/2025_mou/topic_index.json`
- `Output/public_hockey_knowledge_packs.json`
- `Reports/public_hockey_knowledge_packs_report.txt`

## Design Principle
Source PDFs are staging/acquisition artifacts. Athena runtime uses compact JSON knowledge packs with traceable source metadata.
