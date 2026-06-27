# v0.5.5.5.8 Acceptance Display and Analysis Hotfix

## Purpose
Fix immediate Epic 5A acceptance findings from Scout transcripts:

- Studio launch opened two Scout tabs.
- Public Scout rendered diagnostics/cards/engine fields as if they were the answer.
- Public analytical prompts still read like profile dumps instead of analysis.
- Florida Panthers public team prompt did not resolve to a team profile.

## Changed Files

- `Core/version.py`
- `launch.py`
- `Scout/app.py`
- `Scout/conversation/router.py`
- `Knowledge/Intelligence/Public/public_answers.py`
- `Knowledge/Intelligence/Public/public_team_profiles.py`
- `Knowledge/Intelligence/Entities/entity_registry.py`
- `Knowledge/Intelligence/Intent/intent_classifier.py`
- `Tests/validate_scout_runtime_acceptance_hotfix.py`
- `Tests/validate_acceptance_display_and_analysis_hotfix.py`

## Validation

- `Tests/validate_renderer_cleanup.py` PASS
- `Tests/validate_scout_runtime_acceptance_hotfix.py` PASS
- `Tests/validate_acceptance_display_and_analysis_hotfix.py` PASS
