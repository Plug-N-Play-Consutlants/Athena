# Event and Impact Model Specification

## Purpose

The Event and Impact model allows the Sports Intelligence Engine to answer consequence-based questions.

Examples:

- We just made this trade. What is the impact?
- Can Team X realistically trade for Player Y?
- How does this coaching change affect my team?
- What are the salary cap implications?
- What changes if this prospect is called up?

The engine should not merely summarize sports news. It should determine what changed in the sports ecosystem and explain the consequences using deterministic evidence.

## Core Principle

The engine evaluates graph changes.

```text
before state
+ event
= after state

before valuation
vs.
after valuation
= impact
```

## Event vs Scenario vs Impact

### Event

Something that happened or is being considered.

Examples:

- completed trade
- proposed trade
- injury
- coaching change
- free-agent signing
- contract extension
- player call-up
- player demotion
- salary cap change
- rule change

### Scenario

A hypothetical event or set of events.

Question pattern:

```text
What if...?
```

### Impact

The deterministic difference between before and after.

Question pattern:

```text
Now that this happened, what changed?
```

## Canonical Event Object

```json
{
  "event_id": "EVENT_2026_0001",
  "event_type": "trade_completed",
  "event_status": "completed",
  "sport": "NHL",
  "league_id": "...",
  "effective_date": "2026-06-17",
  "actors": [
    {
      "actor_type": "team",
      "actor_id": "TEAM_A",
      "role": "sending_team"
    },
    {
      "actor_type": "team",
      "actor_id": "TEAM_B",
      "role": "receiving_team"
    }
  ],
  "assets": [
    {
      "asset_id": "PLAYER_123",
      "asset_type": "player",
      "from_team_id": "TEAM_A",
      "to_team_id": "TEAM_B"
    },
    {
      "asset_id": "PICK_2027_1_TEAM_B",
      "asset_type": "draft_pick",
      "from_team_id": "TEAM_B",
      "to_team_id": "TEAM_A"
    }
  ],
  "terms": {
    "retained_salary": null,
    "conditions": []
  },
  "source": {
    "source_type": "manual_input",
    "confidence": 1.0
  }
}
```

## Canonical Impact Object

```json
{
  "impact_id": "IMPACT_EVENT_2026_0001",
  "event_id": "EVENT_2026_0001",
  "event_type": "trade_completed",
  "model_key": "contract_dynasty_total_points_points_only",
  "affected_assets": [],
  "affected_teams": [],
  "valuation_deltas": [],
  "team_identity_deltas": [],
  "cap_deltas": [],
  "strategic_deltas": [],
  "market_deltas": [],
  "overall_impact_score": 0.0,
  "confidence": 0.0,
  "evidence": []
}
```

## Event Types

### trade_completed

Used when a trade has happened.

Primary questions:

- Who gained current value?
- Who gained future value?
- Which team improved strategically?
- Which team increased risk?
- Which roster holes were created or solved?

### trade_proposed

Used when a trade is hypothetical.

Primary questions:

- Is it fair?
- Is it strategically aligned?
- Is it realistic?
- Which side should adjust?

### coaching_change

Used when a coach is fired, hired, or changes role.

Primary questions:

- Which players gain deployment opportunity?
- Which players lose role security?
- How does system fit change?
- Does team direction shift?

### injury

Used when a player is injured or returns.

Primary questions:

- Who absorbs the usage?
- How does depth change?
- What replacement options exist?
- What is the team-level impact?

### salary_cap_change

Used for professional sports salary cap changes.

Primary questions:

- Which teams gain flexibility?
- Which teams remain constrained?
- Which trade/free-agent scenarios become feasible?

### rule_change

Used for league rule changes.

Primary questions:

- Which asset classes gain or lose value?
- Which managers/teams benefit?
- Which strategies become stronger?

## Impact Engine Responsibilities

The Impact Engine should:

1. Load the current canonical state.
2. Apply the event or scenario.
3. Recalculate relevant valuation vectors.
4. Compare before and after.
5. Produce deterministic evidence.
6. Leave final prose explanation to the AI layer.

## Non-Responsibilities

The Impact Engine should not:

- fetch external data
- normalize provider payloads
- generate article prose
- make unsupported predictions
- pretend low-confidence data is certain

## Initial Fantrax MVP Scope

The first impact use case should be fantasy trade impact.

Inputs:

```text
Output/player_values.json
Output/team_profiles.json
manual event payload
```

Outputs:

```text
Output/event_impacts.json
```

Initial supported impact dimensions:

- current value delta
- future value delta
- contract value delta
- positional balance delta
- team direction alignment

## Design Rule

Scenario and Impact modules must use the Valuation Engine output. They should not independently recalculate player values.
