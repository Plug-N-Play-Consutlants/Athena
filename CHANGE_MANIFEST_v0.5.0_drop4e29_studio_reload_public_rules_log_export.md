# Athena v0.5.0-drop4e29 — Studio Reload + Public Rules UX + Log Export

## Summary
Stabilizes Athena Studio reload behavior, reduces duplicate browser/tab launches, fixes stale version display in runtime audit, adds Studio log export, and improves public rule lookup answers so basic rule questions provide plain-language explanations instead of retrieval-only evidence.

## Changes
- Advanced version metadata to `0.5.0-drop4e29` / `v0.5.0-drop4e29`.
- Studio runtime audit now re-reads `Core/version.py` dynamically instead of using startup-cached version constants.
- Added reload/launch guards to prevent duplicate reload clicks and duplicate Scout launch attempts.
- Scout browser opening now requests browser reuse (`new=0`) and keeps cache-bust/build metadata.
- Added **Export Studio Log** developer action.
- Exported Studio log includes Studio output, history, Scout log tail, runtime/version metadata.
- Public hockey rule responses now include plain-language explanations for common rule lookups such as icing, offside, and faceoffs while preserving source evidence.
- Updated stale validators so they validate version metadata dynamically instead of expecting old fixed drop strings.

## Validation
- `python Tests/validate_pif1_build003.py` — PASS
- `python Tests/validate_athena_studio_phase1.py` — PASS
- `python Tests/validate_athena_studio_phase2.py` — PASS
- `python Tests/validate_studio_reload_workflow.py` — PASS
- `python Tests/validate_scout_ux_cleanup.py` — PASS
- `python Tests/validate_scout_public_hockey_answer_binding.py` — PASS
- `python Tools/doctor_athena_studio_phase2.py` — PASS
- `python Tools/doctor_pif1_build003.py` — PASS

## Notes
This drop does not implement the full Studio Beta visual redesign. It prepares the runtime/control foundation for the next Studio UI polish sprint.
