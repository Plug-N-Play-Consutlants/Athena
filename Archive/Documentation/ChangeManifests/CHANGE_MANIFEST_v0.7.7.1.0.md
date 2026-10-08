# AthenaEngine v0.7.7.1.0 — Whole-Picture Investigation & NHL Capability Expansion

## Objective
Finish the core 0.7.7 execution model: missing local NHL evidence must trigger registered acquisition before Athena reports it unavailable, and transaction hypotheticals must use acquired roster/player evidence for fit/cost reasoning rather than stop at a requirements list.

## Changed/New Files
- Core/version.py
- Providers/NHL/nhl_client.py
- Providers/NHL/capabilities.py
- Knowledge/Organizations/__init__.py
- Knowledge/Organizations/nhl_roster_evidence.py
- Athena/Investigation/__init__.py
- Athena/Investigation/state.py
- Athena/Investigation/nhl_transaction.py
- Athena/capability_handlers.py
- Scout/conversation/composition.py
- Scout/app.py
- Tools/athena_studio.py
- Tools/doctor_whole_picture_investigation.py
- Tests/validate_whole_picture_investigation.py
- Tests/validate_inquiry_semantic_ownership.py
- Tests/validate_public_composition_contract_restoration.py
- Tests/validate_adaptive_inquiry_execution.py
- Tests/validate_acceptance_semantic_routing.py
- Tests/validate_inquiry_utilization_adaptive_evidence.py
- Tests/validate_session_acceptance_observability.py

## Behavioral Contract
- InquiryState remains semantic authority.
- InvestigationState records required/satisfied/acquisition/partial/waived/unresolved states.
- Existing NHLClient remains the provider boundary; no parallel NHL connection was introduced.
- NHL provider now exposes current/historical roster, roster seasons, prospects, current/historical club stats, goalie summary, and generic skater/goalie/team reports.
- Current transaction investigation attempts Toronto and target-team roster/prospect/club-stat acquisition before declaring those evidence families unavailable.
- Named candidate assets are evidence-backed roster/prospect records, not claims of front-office interest or sufficient trade value.
- Fit and Toronto opportunity cost are Athena analytical conclusions from player/organizational evidence.
- Salary-cap waiver remains scoped: it changes the scenario frame without erasing other evidence or reasoning.
- Expired pre-opening roster limitation is suppressed from current transaction presentation.
- Static Scout helper note above the conversation is removed.

## Studio Verification
Doctor Everything includes `Doctor Whole-Picture Investigation`; no new Studio button was added.

## Acceptance Focus
1. `Auston Matthews`
2. `Show me Auston Matthews over the last five seasons.`
3. `Could the Leafs get McDavid without trading Matthews?`
4. `Forget the salary cap. How could Toronto get McDavid without giving up Matthews?`

For prompts 3–4, PASS requires evidence that NHL roster/prospect acquisition was attempted and that Scout receives named non-protected assets when the provider supplies them. A requirements-only answer is a FAIL.
