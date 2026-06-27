# Athena 4E.2 Finish Patch

Root-drop patch. Extract directly into `F:/Development/Athena`.

Adds:
- Reasoning adapter over existing Player Intelligence outputs
- Evidence-backed PlayerAssessment model
- More authoritative deterministic player assessment narrative
- Scout player route uses ReasoningEngine when available
- Completion validator and doctor

Run:
`%runfile F:/Development/Athena/Tests/validate_4e2_epic_completion.py --wdir`

Then:
`%runfile F:/Development/Athena/Tools/doctor_4e2_player_reasoning.py --wdir`
