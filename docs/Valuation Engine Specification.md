# Valuation Engine Specification

## Purpose

The Valuation Engine is the central deterministic scoring service of the Sports Intelligence Engine. It produces multi-dimensional valuations for canonical assets in a specific analytical context.

The engine must not be provider-specific, sport-specific, or league-specific. It receives canonical inputs from Build, Knowledge, and Intelligence layers, then produces reusable valuation outputs that downstream modules can consume.

## Core Principle

Player value is not a fixed player attribute.

Asset value is a function of:

```text
asset
+ league profile
+ analysis profile
+ team / organization context
+ market context
+ relationship context
= valuation vector
```

The Valuation Engine does not answer final user questions. It quantifies assets from multiple perspectives so other Intelligence modules can reason consistently.

## Layer Responsibility

The Valuation Engine belongs in the Intelligence layer.

It consumes deterministic Knowledge and model-selection outputs. It does not fetch data, normalize provider data, or generate prose.

## Primary Inputs

Initial inputs:

```text
Output/player_master.json
Output/league_profile.json
Output/league_archetype.json
Output/analysis_profile.json
```

Future inputs:

```text
Output/team_profiles.json
Output/asset_registry.json
Output/relationships.json
Output/contracts.json
Output/injuries.json
Output/schedule_context.json
Output/market_context.json
Output/team_direction.json
```

## Primary Outputs

Initial outputs:

```text
Output/player_values.json
Output/player_values.csv
```

Future outputs:

```text
Output/asset_values.json
Output/player_value_deltas.json
Output/contextual_asset_values.json
```

## Valuation Object

Canonical valuation output should follow this general shape:

```json
{
  "asset_id": "PLAYER_12345",
  "asset_type": "player",
  "asset_name": "Example Player",
  "league_id": "...",
  "model_key": "contract_dynasty_total_points_points_only",
  "overall_value": 87.4,
  "intrinsic_value": 84.2,
  "situational_value": 78.6,
  "market_value": 82.1,
  "strategic_value": null,
  "dimensions": {
    "current": 86.0,
    "future": 89.0,
    "contract": 82.0,
    "scarcity": 75.0,
    "replacement": 88.0,
    "risk": 18.0,
    "market": 82.1,
    "fit": null,
    "chemistry": null
  },
  "confidence": 0.72,
  "evidence": [
    "High current production",
    "Dynasty model increases future value weighting",
    "Contract value included because league subtype is contract_dynasty"
  ]
}
```

## Canonical Valuation Dimensions

### 1. Current Value

Question: How valuable is the asset today?

Initial fantasy hockey inputs:

- Player production
- Position
- rostered status
- points-only scoring basis

Future inputs:

- usage
- role
- deployment
- line assignment
- power-play usage
- schedule

### 2. Future Value

Question: What is the expected future contribution?

Initial inputs:

- age if available
- dynasty model weight
- prospect/future flags if available

Future inputs:

- age curves
- projections
- prospect grade
- development trajectory
- NHL/AHL/CHL context

### 3. Contract Value

Question: Does the contract increase or reduce the asset's value?

Fantasy inputs:

- contract years remaining
- contract expiry
- keeper/renewal rules

Professional inputs:

- cap hit
- term
- retained salary
- NMC/NTC
- RFA/UFA status

### 4. Scarcity Value

Question: How hard is this asset to replace in this league?

Inputs:

- league size
- roster slots
- position requirements
- replacement pool
- positional scarcity

### 5. Replacement Value

Question: How painful would it be to lose this asset?

Inputs:

- waiver pool
- free agents
- bench depth
- positional alternatives
- organizational depth

### 6. Risk

Question: How uncertain is this asset?

Inputs:

- injury history
- age decline
- role uncertainty
- deployment volatility
- contract expiry
- prospect uncertainty

Risk is a penalty dimension, not a value dimension. Higher risk should reduce overall value unless the selected model explicitly rewards upside volatility.

### 7. Market Value

Question: What is the league likely to pay for this asset?

Inputs:

- age/hype profile
- prospect status
- recent production
- positional demand
- owner tendencies
- market inefficiencies

Market value is not the same as intrinsic value. This distinction is critical for trade analysis.

### 8. Strategic Fit

Question: How valuable is this asset to a specific team or organization?

Inputs:

- team direction
- competitive window
- positional needs
- prospect pipeline
- draft capital
- contract outlook
- organizational philosophy

Strategic fit is contextual. It may differ for every team.

### 9. Chemistry / Relationship Value

Question: Does the asset perform better or worse because of relationships around it?

Inputs:

- linemates
- coach trust
- power-play unit
- system fit
- teammate synergy
- organizational role

This dimension is initially optional because the current Fantrax data does not fully expose it. It must be included in the design because it is essential for real-world scenario analysis and advanced fantasy impact analysis.

## Intrinsic, Situational, Market, and Strategic Layers

The engine should distinguish between four value layers.

### Intrinsic Value

What the asset is independently.

Includes:

- talent
- production
- age
- contract
- role-neutral projection

### Situational Value

What is happening around the asset.

Includes:

- coach
- system
- linemates
- power play
- organizational deployment
- schedule

### Market Value

What others are likely to pay.

Includes:

- hype
- scarcity
- age bias
- recent performance
- owner behavior

### Strategic Value

What the asset is worth to a specific team.

Includes:

- team identity
- competitive window
- roster needs
- future asset balance
- risk tolerance

## Analysis Profile Dependency

The Valuation Engine must be driven by `Output/analysis_profile.json`.

For example:

```json
{
  "model_key": "contract_dynasty_total_points_points_only",
  "weights": {
    "current": 0.72,
    "future": 0.90,
    "contract": 0.82,
    "scarcity": 0.70,
    "replacement": 0.60,
    "risk": 0.55,
    "market": 0.65,
    "fit": 0.75,
    "chemistry": 0.40
  }
}
```

A redraft league and a contract dynasty league may evaluate the same player differently without changing the valuation code.

## Version 1 Implementation Scope

Version 1 should be intentionally limited:

- Players only
- Intrinsic valuation only
- Analysis-profile-driven weights
- Points-only support
- Contract dynasty support
- No AI prose
- Evidence list included

Version 1 should not attempt to fully model coaching chemistry, market behavior, or team-specific strategic fit. It should reserve those dimensions and mark them as unavailable or low-confidence until proper data exists.

## Future Expansion

The Valuation Engine should eventually support:

- draft picks
- prospects
- contracts
- team-specific contextual valuations
- valuation deltas after trades/events
- market inefficiency detection
- relationship graph inputs
- professional salary cap scenarios
- coaching change impact
- AI explanation layer

## Design Rule

No downstream module may calculate player value independently.

Team Profile, Trade Analysis, Waiver Recommendations, Draft Rankings, Scenario Analysis, Impact Analysis, and AI Publishing must consume the canonical valuation outputs.
