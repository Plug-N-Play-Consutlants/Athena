# v0.5.3.1.5 — Studio Governance Review Buckets

## Purpose
Refine Athena Studio repository governance so Studio can reduce ambiguous manual review, produce focused duplicate reports, generate cleanup recommendations, and detect version drift before any cleanup or consolidation is attempted.

## Changed Files
- `Tools/repository_governance.py`
- `Tools/athena_studio.py`
- `Tools/doctor_repository_governance.py`
- `Tests/validate_repository_governance.py`

## New Governance Classifications
- `DYNAMIC_IMPORT_REVIEW`
- `LEGACY_TOOL_REVIEW`
- `ROOT_DOC_REVIEW`
- `RUNTIME_DATA_REVIEW`
- `UNREFERENCED_SOURCE_REVIEW`

These replace broad manual-review ambiguity wherever the tool can make a safer, more useful diagnostic distinction.

## Studio Changes
- Duplicate Audit now uses `repository_governance.py --duplicates` instead of repeating the full governance audit.
- Added Repository Cleanup Recommendations button using `repository_governance.py --recommendations`.
- Existing safe cleanup remains conservative and limited to reproducible cache/bytecode artifacts.

## Governance Tool Changes
- Added focused duplicate-content and duplicate-function report writers.
- Added prioritized cleanup recommendation report writer.
- Added version-drift detection against `Core/version.py` canonical values.
- Preserved no-delete-by-default behavior.

## Validation
Local validation performed:
- `python -B Tools/doctor_repository_governance.py` PASS
- `python -B Tests/validate_repository_governance.py` PASS
- `python -B Tools/repository_governance.py --duplicates` PASS
- `python -B Tools/repository_governance.py --recommendations` PASS

## Guardrail
Do not delete, archive, or consolidate active source files from this patch. The goal is better diagnosis and recommendation quality before cleanup execution.
