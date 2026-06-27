# Sports Intelligence Engine 2.0 — Knowledge Model Implementation Roadmap

## Purpose

This roadmap translates the Canonical Knowledge Model into implementation phases. It is intended to prevent drift as the engine grows from the current Fantrax/NHL fantasy hockey proof of concept into a broader sports decision intelligence platform.

## Current Working Vertical Slice

```text
Fantrax league settings
NHL skater summary
Fantrax/NHL identity bridge
        ↓
League Profile
League Archetype
Analysis Profile
Player Production
Player Profile
Valuation Engine
Team Profile
Team Direction
```

Current outputs include:

- Output/league_settings.json
- Output/league_profile.json
- Output/league_archetype.json
- Output/analysis_profile.json
- Output/player_master.json
- Output/player_identity_map.json
- Output/player_production.json
- Output/player_profiles.json
- Output/player_values.json
- Output/team_profiles.json
- Output/team_direction.json
- Output/knowledge_readiness.json

## Phase 1 — Stabilize Current Knowledge Pipeline

Goal: ensure the current pipeline can be reliably rerun.

Tasks:

1. Confirm build_all.py ordering.
2. Confirm fetch_all.py does not overwrite valid Raw files with Fantrax error payloads.
3. Add or update run documentation for current successful sequence.
4. Re-run knowledge_readiness after every enrichment.
5. Keep CSV outputs for inspection/debugging.

Success criteria:

- Full current pipeline runs without manual intervention.
- Fantrax error payloads are blocked from replacing valid data.
- NHL production enrichment works through player_identity_map.

## Phase 2 — Player Enrichment Pipeline

Goal: move from production-backed valuation to richer player knowledge.

Modules:

- Knowledge/player_identity_resolver.py — done
- Knowledge/player_production.py — done
- Knowledge/player_age_profile.py — future
- Knowledge/player_contract_profile.py — future
- Knowledge/player_game_logs.py — future
- Knowledge/player_trends.py — future
- Knowledge/injury_availability.py — future
- Knowledge/player_relationships.py — future

Priority order:

1. Age / birthdate
2. Contracts / contract years remaining
3. Game logs
4. Historical player trends
5. Schedule context
6. Injury availability
7. Relationship graph / chemistry

Why this order:

- Age and contracts are critical for dynasty valuation.
- Game logs unlock trend analysis and start/sit support.
- Injuries and relationships improve week-to-week recommendations.

## Phase 3 — Asset Registry

Goal: unify players, draft picks, contracts, and future assets into a single asset catalog.

Module:

- Knowledge/asset_registry.py

Inputs:

- player_profiles.json
- player_values.json
- draft_picks.json
- future contract profiles

Outputs:

- Output/asset_registry.json
- Output/asset_registry.csv

Asset classes:

- player
- prospect
- draft_pick
- contract
- future_consideration

## Phase 4 — Team and Organization Intelligence

Goal: make team direction more accurate by adding future-oriented context.

Modules:

- Knowledge/team_profile.py — done
- Intelligence/team_direction.py — preliminary
- Intelligence/competitive_window.py — future
- Intelligence/organizational_needs.py — future

Inputs needed:

- player values
- contracts
- age curves
- draft capital
- positional depth
- prospect/future value
- transaction history

Outputs:

- team_direction.json
- organizational_needs.json
- league_power_map.json

## Phase 5 — Transaction and Manager Behavior

Goal: understand the league economy and manager tendencies.

Modules:

- Providers/Fantrax/fetch/fetch_transactions.py
- Providers/Fantrax/build/transaction_master.py
- Knowledge/transaction_history.py
- Knowledge/manager_profile.py
- Intelligence/manager_behavior.py
- Intelligence/league_market.py

Key questions:

- Which managers buy or sell?
- Which managers overvalue draft picks?
- Are veterans discounted?
- Are prospects overpriced?
- Who trades frequently?
- Which asset classes are liquid?
- Is the league market polarized?

Outputs:

- transaction_history.json
- manager_profiles.json
- league_market.json

## Phase 6 — Scenario, Impact, and Decision Support

Goal: support common user prompts without turning the engine into an autopilot.

Modules:

- Intelligence/scenario_engine.py
- Intelligence/impact_engine.py
- Intelligence/decision_support.py

Supported prompts:

- What is the impact of this trade?
- Can Team X realistically trade for Player Y?
- How does this coaching change affect my team?
- What are the salary cap implications?
- How can I improve my team?
- Who should I consider trading with?
- Which assets are overvalued or expendable?

Decision-support guardrail:

The engine should surface options, risks, tradeoffs, and likely opportunities. It should not autonomously manage the user's team.

## Phase 7 — AI Explanation Layer

Goal: turn deterministic outputs into useful communication.

AI consumes:

- valuation evidence
- team direction evidence
- scenario deltas
- impact summaries
- decision-support options

AI produces:

- plain-language explanations
- reports
- public articles
- commissioner summaries
- fantasy decision briefings

AI does not invent analysis. It explains deterministic results.

## Provider Strategy

### Fantrax

Owns fantasy-specific data:

- league settings
- fantasy rosters
- managers
- contracts
- draft picks
- transactions
- waivers
- keeper history

### NHL

Owns public hockey data:

- player identity
- production
- game logs
- schedule
- standings
- teams
- public player stats

### Future providers

Potential enrichment sources:

- MoneyPuck
- Natural Stat Trick
- Daily Faceoff
- PuckPedia
- HockeyDB
- Sportradar
- Stats Perform

## Immediate Next Recommendation

Before building new intelligence, stabilize and document the current run sequence, then enrich player knowledge with age and contracts.

Recommended next modules:

1. build_all.py to orchestrate current Build outputs.
2. Knowledge/asset_registry.py to unify players and picks.
3. Knowledge/player_age_profile.py using NHL identity data.
4. Knowledge/contract_profile.py using Fantrax/manual league rules.
5. Intelligence/team_direction.py v0.2 using production + age + contract + picks.
