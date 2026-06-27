# Sports Intelligence Engine 2.0 — Canonical Knowledge Model

## Purpose

The Canonical Knowledge Model defines the provider-neutral, sport-neutral objects that power the Sports Intelligence Engine. Providers fetch data. Build modules normalize provider-specific payloads. Knowledge modules enrich canonical objects. Intelligence modules reason over those objects. AI explains the deterministic outputs.

This document is the authoritative reference for what the engine knows, how facts are represented, and which future modules should enrich each object.

## Locked Pipeline

```text
Fetch
  ↓
Build
  ↓
Knowledge
  ↓
Intelligence
  ↓
AI
```

No layer skips another layer.

## Core Principle

Providers do not own meaning. Canonical knowledge objects own meaning.

A player is not a Fantrax player or an NHL API player. A player is a canonical asset enriched by Fantrax, NHL, historical databases, transaction logs, relationship graphs, injury feeds, and future providers.

## Canonical Object Families

### 1. League

Represents the competitive environment.

Current fields:

- league_id
- league_name
- sport
- season
- team_count
- scoring_model
- scoring_detail
- roster_continuity
- league_subtype
- competition_model
- lineup_model
- planning_horizon
- lineup_slots
- draft_model
- asset_classes
- evidence
- confidence

Future fields:

- waiver rules
- trade deadline rules
- playoff rules
- keeper rules
- contract rules
- salary cap or auction rules
- historical season count
- competitive balance metrics
- market inflation indicators

Primary providers:

- Fantrax
- Yahoo
- ESPN
- CBS
- Sleeper
- user-supplied scenario profile

Primary consumers:

- league_archetype
- analysis_profile
- valuation_engine
- team_direction
- decision_support

---

### 2. Analysis Profile

Represents the selected operating mode for Intelligence.

This is not merely a league label. It is a model selector.

Current fields:

- model_key
- archetype_label
- planning_horizon
- valuation_weights
- supported_decisions
- confidence
- evidence

Example:

```json
{
  "model_key": "contract_dynasty_total_points_points_only",
  "planning_horizon": "multi_year",
  "valuation_weights": {
    "current": 0.76,
    "future": 0.90,
    "contract": 0.82,
    "scarcity": 0.70,
    "replacement": 0.62,
    "risk": 0.58,
    "market": 0.68,
    "fit": 0.78,
    "chemistry": 0.35
  }
}
```

Primary consumers:

- valuation_engine
- team_direction
- trade analysis
- waiver analysis
- start/sit analysis
- scenario analysis
- impact analysis

---

### 3. Player

Represents a real player as a canonical asset.

Current fields:

- canonical player id
- Fantrax player id
- NHL player id
- name
- normalized name
- position
- NHL team
- fantasy team
- fantasy team id
- production summary
- valuation vector
- evidence completeness
- confidence

Future fields:

- birthdate
- age
- height / weight
- handedness
- experience
- contract status
- contract years remaining
- keeper eligibility
- acquisition cost
- draft pedigree
- prospect status
- injuries
- availability
- NHL schedule
- game logs
- opponent splits
- home / away splits
- recent form
- historical trend deltas
- usage
- time on ice
- power play usage
- penalty kill usage
- line assignment
- coach relationship
- teammate chemistry
- market value
- trade history
- waiver history
- replacement tier

Primary providers:

- Fantrax: fantasy ownership, contracts, league transactions, keeper status
- NHL: player identity, production, game logs, schedule, teams
- future: MoneyPuck, Natural Stat Trick, Daily Faceoff, PuckPedia, HockeyDB

Primary consumers:

- valuation_engine
- team_profile
- team_direction
- player_trends
- start/sit decision support
- trade impact
- waiver recommendations
- article generation

---

### 4. Draft Pick

Represents a future selection asset.

Current fields:

- pick id
- season / year
- round
- original owner
- current owner
- provider source
- evidence completeness

Future fields:

- expected value curve
- historical pick outcome distribution
- trade frequency
- pick liquidity
- league market premium / discount
- positional replacement value
- prospect expectation
- contract replacement impact

Primary providers:

- Fantrax
- manual imports if provider unavailable

Primary consumers:

- valuation_engine
- team_profile
- team_direction
- trade analysis
- manager_behavior
- league_market

---

### 5. Fantasy Team / Organization

Represents a manager-controlled fantasy organization.

Current fields:

- fantasy team id
- team name
- manager / owner name when available
- rostered players
- roster size
- positional depth
- total team value
- average player value
- confidence

Future fields:

- contract distribution
- keeper pressure
- draft capital
- prospect pipeline
- age curve
- injury exposure
- positional surplus
- positional deficits
- future strength
- current strength
- competitive window
- organizational strategy
- risk posture
- market position

Primary providers:

- Fantrax
- enriched player profiles
- draft pick registry
- transaction history

Primary consumers:

- team_direction
- decision_support
- trade analysis
- market intelligence
- AI summaries

---

### 6. Manager

Represents the human decision-maker behind a fantasy team.

This object is behavioral, not merely administrative.

Future fields:

- manager id
- name / alias
- active seasons
- trade frequency
- waiver frequency
- free-agent frequency
- draft style
- prospect preference
- draft pick preference
- veteran preference
- risk tolerance
- buy/sell tendency
- deadline behavior
- favorite trade partners
- avoided trade partners
- positional preferences
- transaction timing
- typical asset exchange pattern
- market influence
- negotiation style indicators
- engagement level
- evidence completeness
- confidence

Primary providers:

- Fantrax transaction history
- draft history
- waiver history
- trade history

Primary consumers:

- manager_behavior
- league_market
- trade opportunity discovery
- decision_support

Guardrail:

Manager behavior should inform decision support, not manipulate users. The engine should preserve manager agency and surface tendencies, tradeoffs, and likely opportunities.

---

### 7. League Market

Represents the economic behavior of a fantasy league.

Future fields:

- draft pick inflation
- prospect premium
- veteran discount
- positional premiums
- trade liquidity
- market polarization
- buyer/seller distribution
- transaction velocity
- asset class demand
- manager clustering
- market efficiency
- engagement risk

Primary sources:

- transaction history
- manager profiles
- trade outcomes
- draft history
- waiver activity

Primary consumers:

- valuation_engine market dimension
- trade analysis
- decision_support
- commissioner insights
- AI article generation

---

### 8. Real-World Team / Organization

Represents a professional sports organization.

Future fields:

- organization id
- league
- roster
- depth chart
- coach
- management
- salary cap
- contracts
- injuries
- prospects
- draft picks
- schedule
- standings
- playing style
- system profile
- competitive window
- cap flexibility
- transaction feasibility

Primary providers:

- NHL API
- future salary cap provider
- future line-combination provider
- future prospect provider

Primary consumers:

- scenario_engine
- impact_engine
- public sports decision assistant
- article generation

---

### 9. Relationship

Represents a connection between two or more canonical objects.

Future relationship types:

- player ↔ player chemistry
- player ↔ coach deployment
- player ↔ team system fit
- player ↔ power play unit
- player ↔ line combination
- player ↔ opponent
- manager ↔ manager trade relationship
- manager ↔ asset class preference
- team ↔ competitive window

Primary consumers:

- valuation_engine chemistry / fit dimensions
- scenario_engine
- impact_engine
- start/sit analysis
- public speculation analysis

---

### 10. Event

Represents something that happened or might happen.

Event types:

- trade_completed
- trade_proposed
- waiver_claim
- free_agent_add
- player_drop
- injury
- injury_return
- coaching_change
- prospect_callup
- contract_extension
- salary_cap_change
- rule_change
- draft_pick_trade

Primary consumers:

- scenario_engine
- impact_engine
- decision_support
- AI explanation layer

---

### 11. Impact

Represents deterministic before/after consequences of an event.

Future fields:

- event_id
- event_type
- before_state_reference
- after_state_reference
- affected_assets
- affected_teams
- affected_managers
- valuation_delta
- strategic_delta
- market_delta
- confidence
- evidence

Primary consumers:

- AI explanations
- trade impact analysis
- commissioner summaries
- public content generation

## Evidence Completeness vs Confidence

Every major object should carry both values.

Evidence completeness answers:

> How much of the desired knowledge do we currently have?

Confidence answers:

> How reliable/current is the knowledge we do have?

These are not the same. An object may be sparse but reliable, or complete but stale.

## Current Implementation State

As of the current project state:

Ready or functional:

- League settings
- League profile
- League archetype
- Analysis profile
- Player master
- Player identity resolver
- NHL production enrichment
- Player profiles
- Player values
- Team profiles
- Preliminary team direction
- Knowledge readiness

Missing or future:

- Contracts
- Transaction history
- Manager behavior
- League market
- Historical game logs
- Player trends
- Relationship graph
- Injury availability
- Real-world salary cap
- Scenario engine
- Impact engine
- Decision support engine
- AI explanation layer

## Design Guardrails

1. Provider modules never contain business logic.
2. Build modules normalize provider payloads into canonical outputs.
3. Knowledge modules enrich canonical facts.
4. Intelligence modules reason over canonical facts.
5. AI explains deterministic outputs.
6. The engine informs managers; it does not manage for them.
7. Recommendations should be advisory, not command-oriented.
8. Unknown data should remain unknown. Do not invent facts to fill gaps.
9. Every derived conclusion should include evidence and confidence.
10. Every new provider should enrich canonical objects, not create separate object definitions.
