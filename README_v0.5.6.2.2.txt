AthenaEngine v0.5.6.2.2
Repository Cleanup Studio Integration

Purpose
- Restore Studio-first workflow for Phase 4A repository cleanup.
- No CLI steps are required for normal operation.
- No Scout intelligence behavior changes.
- No source/module renames.

Studio actions added/verified
- Preview Cleanup
- Apply Safe Cleanup
- Open Cleanup Report

Verify Build includes
- Doctor Repository Safe Cleanup
- Validate Repository Safe Cleanup
- Updated Studio Operations Console doctor/validator

Expected workflow
Relaunch Studio -> Reload Build -> Verify Build -> Repository Audit -> Preview Cleanup -> review report -> Apply Safe Cleanup
