AthenaEngine v0.7.10.50.4 — Studio Workflow Consolidation

Apply overlay to existing AthenaEngine repository (merge and replace files).
Changes:
- Core Workflow: removes duplicate Verify Build and Export Logs controls; retains View Logs and Open Reports.
- Developer Validation: retains the sole Verify Build control.
- Developer Diagnostics: removes duplicate Open Reports, Doctor Everything, and Acceptance Explorer controls; retains Studio Health and ZIP export.
- Export Diagnostics creates a timestamped ZIP under Reports containing real command logs, other Logs files, visible Studio output and a manifest. View Logs includes an Export Diagnostics ZIP control.
- Updated Studio operations acceptance test to validate the new layout and actual log export code path.

Validation: Studio operations console validator PASS; ZIP export smoke test PASS; full Windows Studio Verify Build pending.
