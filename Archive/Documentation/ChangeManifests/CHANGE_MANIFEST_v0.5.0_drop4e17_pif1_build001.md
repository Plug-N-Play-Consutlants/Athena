# Athena v0.5.0-drop4e17 — PIF-1 Build 001

## Scope
First build of Public Intelligence Foundation: Intent & Entity Intelligence.

## Added
- `Knowledge/Intelligence/Intent/intent_types.py`
- `Knowledge/Intelligence/Intent/intent_classifier.py`
- `Knowledge/Intelligence/Entities/entity_registry.py`
- `Knowledge/Intelligence/Entities/entity_extractor.py`
- `Knowledge/Intelligence/Entities/fuzzy_match.py`
- `Knowledge/Intelligence/Entities/disambiguation.py`
- `Knowledge/Intelligence/Routing/request_router.py`
- `Tests/validate_pif1_build001.py`
- `Tools/doctor_pif1_build001.py`

## Updated
- `Core/version.py`
- `Scout/conversation/router.py`

## Behavior
- Public prompts now classify intent before retrieval.
- Public player aliases and spelling variants resolve before Player Intelligence.
- `Sebastian Aho` returns an ambiguity path instead of merging separate players.
- Public comparisons no longer use fantasy-owner context as the primary answer.
- Draft/news/prospect prompts now return explicit intelligence-gap responses instead of unrelated NHL rulebook/CBA topics.

## Validation
Run from the Athena root:

```cmd
python Tests\validate_pif1_build001.py
python Tools\doctor_pif1_build001.py
```
