# v0.7.7.0.11 — Public Composition Contract Restoration Hotfix

- Restores final public composition at `/api/ask` before logging/return.
- Separates `display_contract=public_comment_only` from `experience_contract=athena_response_v1`.
- Adds explicit public composers for 0.7 NHL economic, contract, cap, transaction, plausibility, asset-state, and temporal-comparison intents.
- Preserves the specialist narrative as `diagnostics.internal_narrative` rather than treating it as the public body.
- Adds shared follow-up generation for these public analytical routes.
- Strengthens the existing Renderer Cleanup Doctor so Studio Verify fails if the public/internal composition contract regresses.
- No new Studio button.
