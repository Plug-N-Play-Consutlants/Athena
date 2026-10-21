AthenaEngine v0.7.10.50.3 — Registered Diagnostics & Studio Logs Repair

Apply: extract into F:\Development\AthenaEngine, preserving AthenaEngine/ relative paths (the archive has AthenaEngine as its top-level folder). Overwrite the three modified files. Reload Build, Relaunch Studio, Verify Build.

Changed:
- Scout/conversation/router.py: registered Athena execution for named league recap and diagnostic inquiries.
- Tools/athena_studio.py: visible View Logs action, in-app list/view of actual log files and export action; Reports stays separate.
- Core/version.py and pyproject.toml: version 0.7.10.50.3.

Verification (local extraction): 16/17 Studio suites passed. Epic 4 Public acceptance was attempted but exceeded the execution time limit, not confirmed pass or fail. Fantasy and historical checks initially lacked Output data in extraction; reran with Output restored and passed. The two previously failing suites passed. Full verification on canonical Windows repository required before locking.

No historical evidence or canonical Output files are modified.
