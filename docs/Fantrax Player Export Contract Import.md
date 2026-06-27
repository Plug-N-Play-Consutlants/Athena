# Fantrax Player Export Contract Import

The Fantrax player export can be used as the contract source for the current fantasy league.

Save the export into the project as either:

```text
Raw/player_contracts.csv
```

or:

```text
Raw/Fantrax-Players-<league>.csv
```

The builder will scan for both.

## Required export columns

The Fantrax export should include:

```text
ID
Player
Team
Position
Status
Age
Contract
FPts
FP/G
GP
Pt
```

For contract enrichment, the key field is:

```text
Contract
```

In this league, `Contract` is an expiry year, not remaining years.

For active season `2025`:

```text
2025 = expiring / 1 year remaining
2026 = 2 years remaining
2027 = 3 years remaining
```

The builder derives:

```text
contract_expiry_year
contract_years_remaining
contract_status
contract_score
```

## Matching

The preferred match uses the Fantrax player ID from the export, with surrounding asterisks removed.

Example:

```text
*02un4* -> 02un4
```

If ID matching fails, the builder falls back to conservative name/team matching.

## Important behavior

Placeholder contract records are not treated as real contract knowledge.

Contracts are only usable by Intelligence when:

```text
evidence_completeness > 0
has_verified_contract = true
```
