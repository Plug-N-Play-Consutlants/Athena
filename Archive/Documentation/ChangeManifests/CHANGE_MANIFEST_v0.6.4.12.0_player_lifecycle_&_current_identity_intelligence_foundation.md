# v0.6.4.12.0 — Player Lifecycle & Current Identity Intelligence Foundation

- Adds provider-neutral player lifecycle reconciliation so player identity persists across prospect, draft, organizational, professional, and NHL-roster states.
- Preserves older developmental/provider observations instead of overwriting history when newer evidence advances a player's current state.
- Uses recency, evidence authority, identity specificity, and lifecycle state to determine current organizational identity.
- Adds current-news discovery as an additive current-identity evidence source while retaining official/current structured player outputs as preferred evidence when available.
- Adds adaptive public-player composition for players who are not yet represented by the small seeded rich-profile pack.
- Removes the v0.6.4.11.2 McKenna-specific routing guard; bare-player lifecycle handling is generic.
- Keeps established rich seeded/reasoned profiles such as Auston Matthews on their existing player-experience path.
- Developmental statistics are surfaced only when attached evidence provides them; junior, college, minor-league, or NHL production is never invented to fill a lifecycle gap.
- `Public Sports` → `Professional Sports` remains a separate non-blocking terminology TODO and is intentionally not bundled into this foundation.
