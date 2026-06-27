# Athena v0.5.0-drop4e30 — Public Rule Source Popup + Scout Answer Binding

## Scope
- Ensures public rules questions such as "What is icing?" display the plain-language Scout answer as the primary visible response.
- Keeps raw engine retrieval text in the collapsible Developer / Raw Reasoning Output area.
- Adds source-link buttons for rulebook evidence with a popup containing source title, rule/section reference, Athena explanation, and available knowledge-pack evidence.
- Advances version metadata to v0.5.0-drop4e30.

## Notes
- Current rulebook packs contain section-level topic evidence, not full extracted rulebook prose. The popup therefore displays the authoritative source/section and available Athena evidence. Full rule-text extraction remains a future public knowledge-pack enhancement.

## Validation
- python Tests/validate_scout_public_hockey_answer_binding.py
- python Tests/validate_studio_reload_workflow.py
- python Tests/validate_pif1_build003.py
