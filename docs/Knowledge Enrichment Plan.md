# Knowledge Enrichment Plan

## Purpose

The Sports Intelligence Engine should improve by adding canonical knowledge, not by allowing downstream Intelligence modules to guess. The current architecture is working. The next objective is to enrich the Knowledge layer so valuation, team direction, trade analysis, scenario analysis, impact analysis, and decision support have better facts to reason over.

## Guiding Rule

Specific data, global model.

Fantrax hockey is the validation environment, but every knowledge object should be designed so other providers, fantasy formats, sports, and real-world scenarios can reuse it.

## Current Proven Chain

```text
Build: league_settings
Knowledge: league_profile
Intelligence: league_archetype
Intelligence: analysis_profile
Knowledge: player_profile
Intelligence: valuation_engine
Knowledge: team_profile
```

## Current Knowledge Wall

The engine can now identify league format, model selection, ownership, positional scarcity, player profiles, and team profiles. However, player and team values are still preliminary because the Knowledge layer lacks differentiated production, age, contract, transaction, trend, injury, and relationship data.

## Priority Knowledge Domains

### 1. Player Production

Needed for:

- player valuation
- team strength
- trade evaluation
- waiver analysis
- start/sit recommendations
- articles and summaries

Canonical facts:

- goals
- assists
- points
- games played
- points per game
- recent production
- season production
- historical production
- projections when available

### 2. Contracts

Needed for contract dynasty valuation.

Canonical facts:

- years remaining
- expiry season
- keeper eligibility
- acquisition source
- reset rules
- salary or cap hit where applicable

### 3. Transaction History

Needed for manager behavior and market intelligence.

Canonical facts:

- trade
- waiver claim
- free-agent signing
- drop
- draft selection
- keeper choice
- IR activation
- contract/keeper expiry events

Each transaction should identify:

- date
- season
- actor/manager
- team
- assets moved
- transaction type
- asset classes involved
- direction of value

### 4. Manager Behavior

Needed for realistic decision support.

Canonical facts:

- trade frequency
- asset preferences
- prospect bias
- pick bias
- veteran bias
- waiver activity
- free-agent activity
- risk appetite
- common partners
- deadline behavior
- buy/sell/rebuild tendencies

The engine should inform managers, not manage for them. Manager behavior should be used to identify options, tradeoffs, and likely opportunities, not to manipulate users or automate decisions.

### 5. League Market Profile

Needed to understand the league economy.

Canonical facts:

- draft pick inflation
- prospect premium
- veteran discount
- positional premiums
- market liquidity
- trade polarization
- buyer/seller distribution
- engagement patterns

### 6. Historical Player Trends

Needed for start/sit and matchup intelligence.

Canonical facts:

- player vs opponent scoring frequency
- recent vs historical trends
- goals/assists split
- home/away split
- schedule-weighted opportunity
- matchup trend delta

Example:

Sidney Crosby scores in 75% of games against Toronto historically, but only 50% in the last two seasons. He has no goals against Vegas. If he plays Toronto twice and Vegas once this week, start/sit advice should weigh matchup history, recency, schedule, and available alternatives.

### 7. Relationship Graph

Needed for chemistry, coaching changes, deployment, and real-world scenario analysis.

Canonical relationships:

- player-player
- player-coach
- player-team
- player-line
- player-power-play unit
- player-organization
- prospect-organization
- coach-team

### 8. Event and Impact Knowledge

Needed for questions such as:

- We just made this trade. What is the impact?
- How does this coaching change affect my team?
- Can Team X realistically trade for Player Y?

Events modify the graph. Impact compares before and after.

## Recommended Implementation Order

1. `Knowledge/knowledge_readiness.py`
2. Normalize player production inputs
3. Normalize contract inputs
4. Normalize transaction history
5. Build manager behavior profiles
6. Build league market profile
7. Build historical player trends
8. Build relationship graph
9. Add event and impact knowledge feeds

## Product Guardrail

The engine is a decision-support system, not an autopilot.

It should identify:

- overvalued assets
- undervalued assets
- surplus areas
- weak positions
- trade potential
- free-agent options
- market conditions
- risks
- tradeoffs

It should not take over the manager role or produce autonomous season plans unless explicitly asked for a scenario simulation.
