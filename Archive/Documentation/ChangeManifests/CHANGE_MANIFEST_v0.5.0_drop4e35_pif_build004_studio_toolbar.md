# Athena v0.5.0-drop4e35 — PIF Build 004 + Studio Toolbar

## Summary

This drop continues PIF-1 by adding public team profile seed coverage, richer public player comparison structure, and a compact primary-action toolbar in Athena Studio.

## Engine changes

- Added `Knowledge/Intelligence/Public/public_team_profiles.py`.
- Added public team profile answer routing for prompts such as `Tell me about the Leafs`.
- Expanded public comparison answers to include career identity, style, differentiators, and public-context-first guardrails.
- Fixed Sebastian Aho profile mapping so the Carolina/Finnish center and Swedish defenseman resolve as distinct public profiles.
- Added event-context intent handling for team/news prompts such as coaching hires and impact questions, routing them to Event Intelligence gaps instead of inventing answers.

## Studio changes

- Added a compact primary runtime toolbar for Launch, Reload, Stop, Open Scout, Refresh, and Restart Studio.
- Moved maintenance/runtime diagnostic actions into the Runtime Center tiles.
- Added toolbar validation and doctor utilities.
- Updated Studio/PIF validation paths to prefer PIF Build 004.

## Validation

Validated locally:

- `Tests/validate_runtime_cleanup.py`
- `Tests/validate_pif1_build004.py`
- `Tests/validate_pif1_build003.py`
- `Tests/validate_athena_studio_phase2.py`
- `Tests/validate_studio_reload_workflow.py`
- `Tests/validate_studio_browser_self_refresh.py`
- `Tests/validate_athena_studio_beta_ui.py`
- `Tests/validate_athena_studio_tile_ui.py`
- `Tests/validate_athena_studio_toolbar.py`
- `Tests/validate_scout_public_hockey_answer_binding.py`
- `Tools/doctor_pif1_build004.py`
- `Tools/doctor_athena_studio_toolbar.py`
- `Tools/doctor_athena_studio_tile_ui.py`
- `Tools/doctor_athena_studio_beta_ui.py`
