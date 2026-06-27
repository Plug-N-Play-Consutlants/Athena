# Transaction Pipeline

The transaction pipeline extends the shared Sports Intelligence Engine without changing the locked architecture.

Raw provider transaction data is fetched, normalized into canonical transaction objects, enriched into transaction history knowledge and then consumed by Intelligence modules.

## Flow

Providers/Fantrax/fetch/fetch_transactions.py
↓
Providers/Fantrax/build/transaction_master.py
↓
Knowledge/transaction_history.py
↓
Intelligence/manager_behavior.py
↓
Intelligence/league_market.py

## Canonical Transaction Shape

Each canonical transaction record should expose:

- transaction_id
- timestamp
- transaction_type
- status
- summary
- managers_involved[]
- assets[]
- provider
- provider_transaction_id
- provider_metadata

## Layer Boundaries

- Fetch saves raw provider payloads only.
- Build handles Fantrax-specific payload interpretation.
- Knowledge consumes only canonical transaction records.
- Intelligence derives manager and market signals from Knowledge outputs.
- AI may later explain the generated intelligence but must not re-parse provider payloads.
