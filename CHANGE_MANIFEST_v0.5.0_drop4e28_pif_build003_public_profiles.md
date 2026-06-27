# Athena v0.5.0-drop4e28 — PIF-1 Build 003 Public Profiles

## Scope
- Adds the first seeded public player profile pack.
- Routes public player/profile/comparison questions through public PIF data before fantasy or rulebook retrieval.
- Adds public-mode context pills for public capabilities instead of private Fantrax league status.
- Updates Studio validation/doctor routing to prefer PIF Build 003.
- Makes the Studio reload workflow validator version-resilient.

## Key Fixes
- Public mode no longer shows Fantrax league/auth/data pills.
- Public mode shows public capability pills: Public player profiles, NHL Rules, NHL/NHLPA MOU, RSS feeds.
- Public player questions such as typo variants resolve to public profile answers.
- `Who is Sebastian Aho?` returns a disambiguation answer with two distinct public entities.
- `Compare Matthews and McDavid` uses public comparison output and explicitly skips fantasy owner context.
- Draft/event/prospect gaps are surfaced as intentional knowledge-pack gaps rather than rulebook/MOU answers.

## Validation
- `Tests/validate_pif1_build001.py` PASS
- `Tests/validate_pif1_build002.py` PASS
- `Tests/validate_pif1_build003.py` PASS
- `Tools/doctor_pif1_build001.py` PASS
- `Tools/doctor_pif1_build002.py` PASS
- `Tools/doctor_pif1_build003.py` PASS
- `Tests/validate_athena_studio_phase1.py` PASS
- `Tests/validate_athena_studio_phase2.py` PASS
- `Tools/doctor_athena_studio_phase1.py` PASS
- `Tools/doctor_athena_studio_phase2.py` PASS
- `Tests/validate_studio_reload_workflow.py` PASS
- `Tools/doctor_studio_reload_workflow.py` PASS
