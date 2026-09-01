AthenaEngine v0.6.4.1.0 — Adaptive Investigation Runtime Integration

Apply this patch over the current v0.6.4.0.0 tree.
Then: Relaunch Studio -> Reload Build -> Verify Build -> Validate Everything -> Doctor Everything.
Focused checks:
  python -B Tests/validate_adaptive_investigation_runtime.py
  python -B Tools/doctor_adaptive_investigation_runtime.py

Acceptance focus:
- news/update stays concise
- no live match can degrade to most recent trustworthy relevant evidence
- unrelated evidence is never substituted
- fallback freshness is explicit
- rich profile/comparison output remains protected
- compatible follow-ups retain bounded working investigation state
