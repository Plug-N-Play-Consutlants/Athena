# Change Manifest: v0.6.3.0.0 — Foundational Governance and Module Adaptivity

## Purpose

Lock Athena's product philosophy and modular expansion rule into the repository as a permanent governance layer.

## Added

- `Foundations/Athena_Constitution.md`
- `Foundations/Athena_Manifesto.md`
- `Foundations/Athena_Intelligence_Model.md`
- `Foundations/Scout_Principles.md`
- `Foundations/Engineering_Principles.md`
- `Foundations/Product_Vision.md`
- `Foundations/Roadmap.md`
- `Foundations/Decision_Record_Template.md`
- `Intelligence/Foundation/module_contracts.py`
- `Tools/doctor_foundational_governance.py`
- `Tests/validate_foundational_governance.py`

## Changed

- Advanced version metadata to `0.6.3.0.0`.
- Exported module insertion contracts from `Intelligence.Foundation`.

## Architectural Rule

Athena is now explicitly module-adaptive. Future modules should declare capability, evidence, context, reasoning, composition, and validation contracts so the existing architecture can discover and route them without hard-coded rewrites.
