# Fantasy Sports Intelligence

Fantasy Sports Intelligence is a product built on top of the shared Sports Intelligence Engine.

It consumes canonical league, roster, player, draft asset, transaction and market intelligence to help users evaluate fantasy teams and league context.

## Product Responsibilities

- League rule interpretation
- Team and roster analysis
- Player valuation
- Trade exploration
- Waiver and free-agent opportunity analysis
- Draft preparation
- Keeper and contract planning
- Manager behaviour analysis
- League market analysis

## Decision-Support Principle

The product informs managers. It does not autonomously manage teams.

Preferred language:

- "This player appears overvalued relative to the team window."
- "This roster has surplus defensive assets."
- "This manager historically acquires veterans near the deadline."

Avoid command language such as "make this trade" unless the user explicitly asks for a generated scenario.
