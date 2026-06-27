# Athena v0.5.0-drop4e39 — Team Reasoning Engine

## Purpose
Adds the first public Team Reasoning Engine so team answers move beyond seed profile rendering into deterministic reasoning sections.

## Changes
- Added `Reasoning/team_reasoning_engine.py`.
- Updated public team answers to invoke Team Reasoning before Scout presentation.
- Added sections for Executive Summary, Historical Context, Organizational Identity, Strengths, Weaknesses, Current Direction, and Future Outlook.
- Added `Tests/validate_team_reasoning_engine.py`.
- Added `Tools/doctor_team_reasoning_engine.py`.
- Registered Team Reasoning validation and doctor actions in Athena Studio.
- Advanced version metadata to `v0.5.0-drop4e39`.
- Kept renderer cleanup validators compatible with the new build.

## Guardrails
- Public team answers must not use provider-specific fantasy owner context by default.
- Team profiles remain Knowledge facts; Team Reasoning owns conclusions; Scout owns presentation.
- Live standings, cap, injuries, transactions and event feeds remain future inputs.
