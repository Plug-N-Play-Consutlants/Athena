AthenaEngine v0.5.6.2.3
Safe Cleanup Locked File Handling

This hotfix keeps Studio-first repository cleanup from failing when Studio is actively holding a runtime log file. Locked or in-use files are skipped, recorded in the cleanup report as skipped_locked, and surfaced as warnings rather than fatal cleanup failures.

Use through Studio:
Relaunch Studio -> Reload Build -> Verify Build -> Preview Cleanup -> Apply Safe Cleanup -> Open Cleanup Report
