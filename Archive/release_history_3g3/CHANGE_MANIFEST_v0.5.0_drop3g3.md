# CHANGE MANIFEST — v0.5.0-drop3g3

## Sprint
3G Phase 3 — Final Hygiene Pass

## Purpose
Finish the repository cleanup chapter before returning to feature cadence. This pass removes remaining root-level release/change clutter, hardens Doctor as the single health report, and verifies that validation/test residue cannot remain in runtime workspace/configuration.

## Added
- `Tools/cleanup_3g_phase3_final_hygiene.py`
- `Tests/validate_3g_phase3_final_hygiene.py`

## Changed
- `Core/version.py` updated to `0.5.0-drop3g3` / `v0.5.0-drop3g3`.
- `Tools/doctor.py` expanded to report:
  - duplicate roots
  - root release/change residue
  - placeholder contamination
  - workspace/version health
  - credential split status
  - generated artifact counts
  - raw/output health signals
- root `doctor.py` remains the convenience launcher.

## Cleanup behavior
The cleanup script:
- removes duplicate legacy project roots
- removes Python cache artifacts
- archives root-level release/change/history markdown files into `Archive/release_history_3g3/`
- sanitizes placeholder IDs in workspace/config
- refreshes workspace `engine_version`
- preserves `Configuration/secrets.local.json`
- preserves `Raw/`, `Output/`, `Reports/`, and `Logs/`

## Expected validation
Run:

```python
runfile(
    "Tools/cleanup_3g_phase3_final_hygiene.py",
    wdir=r"F:\Development\Athena"
)

runfile(
    "Tests/validate_3g_phase3_final_hygiene.py",
    wdir=r"F:\Development\Athena"
)
```
