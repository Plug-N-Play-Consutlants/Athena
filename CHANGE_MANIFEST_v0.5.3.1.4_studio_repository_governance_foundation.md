# v0.5.3.1.4 — Studio Repository Governance Foundation

## Purpose

Refactor Athena Studio away from a noisy script-button surface and toward a repository governance console that can diagnose, classify, and plan cleanup before further feature work is layered onto the codebase.

## Changed / Added

- Added `Tools/repository_governance.py` as the conservative repository cleanup authority.
- Added `Tools/doctor_repository_governance.py` for Doctor Everything / Developer Mode readiness checks.
- Added `Tests/validate_repository_governance.py` for Validate Everything coverage.
- Updated `Tools/athena_studio.py` Repository area into `Repository Governance` actions:
  - Governance Audit
  - File Audit
  - Duplicate Audit
  - Cleanup Preview
  - Apply Safe Cleanup
  - Archive Preview
  - Governance Reports
- Added governance doctor access in Developer Mode.
- Added repository governance validation into Validate Everything.
- Added repository governance doctor into Doctor Everything.

## Cleanup Safety Rules

Automated apply mode is intentionally limited to reproducible artifacts only:

- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`

Root-level manifest archival is preview-only from Studio unless explicitly run with the archival flag from the tool. Source modules, tests, doctors, validators, reports, manifests, archives, and configuration files are not deleted automatically.

## Governance Classifications

The governance audit classifies files as:

- `KEEP_ACTIVE`
- `KEEP_ENTRYPOINT`
- `KEEP_TEST`
- `KEEP_ARCHIVED`
- `CONSOLIDATE_CANDIDATE`
- `ARCHIVE_CANDIDATE`
- `DELETE_SAFE`
- `MANUAL_REVIEW_REQUIRED`

## Validation

Local validation performed against the uploaded ZIP workspace:

- `python -B Tools/doctor_repository_governance.py` — PASS
- `python -B Tests/validate_repository_governance.py` — PASS

