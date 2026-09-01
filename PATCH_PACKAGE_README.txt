AthenaEngine v0.6.4.1.1 patch package

This package is intentionally a source patch rather than a reconstructed repository archive.
It was produced against the current public GitHub v0.6.4.1.0 source after the attachment
mount repeatedly failed.

Apply from the AthenaEngine repository root:

    git apply AthenaEngine_v0.6.4.1.1.patch

Then run the four focused checks listed in README_v0.6.4.1.1_apply_notes.txt after application.

Files changed/added by the patch:
- Core/version.py
- Knowledge/Events/live_intelligence.py
- Scout/conversation/router.py
- Tests/validate_live_evidence_fallback_routing.py
- Tools/doctor_live_evidence_fallback_routing.py
- README_v0.6.4.1.1_apply_notes.txt
