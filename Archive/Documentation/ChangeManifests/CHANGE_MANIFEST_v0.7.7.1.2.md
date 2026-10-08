# AthenaEngine v0.7.7.1.2 — Investigation Depth Validator Hotfix

## Objective
Repair stale release-version assertions that caused Studio Verify Build to report one failure after v0.7.7.1.1.

## Changed/New Files
- Core/version.py
- Tests/validate_inquiry_semantic_ownership.py
- Tests/validate_whole_picture_investigation.py
- Tests/validate_public_composition_contract_restoration.py
- Tests/validate_adaptive_inquiry_execution.py
- Tests/validate_acceptance_semantic_routing.py
- Tests/validate_inquiry_utilization_adaptive_evidence.py
- Tests/validate_session_acceptance_observability.py
- CHANGE_MANIFEST_v0.7.7.1.2.md

## Behavioral Contract
- No runtime or investigation behavior changes.
- Release metadata advances to v0.7.7.1.2.
- Inquiry Semantic Ownership validator now expects the active hotfix rather than the obsolete hotfix 0 value.
- Other validators carried by the prior patch are aligned to the new release version so Verify Build can validate the current build consistently.
