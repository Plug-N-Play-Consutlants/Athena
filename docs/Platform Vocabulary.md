# Platform Vocabulary

The Sports Intelligence Platform uses consistent terminology to keep the shared engine separate from the products that consume it.

## Terms

- **Sports Intelligence Platform**: the overall project and product ecosystem.
- **Sports Intelligence Engine**: the shared deterministic core that runs Fetch → Build → Knowledge → Intelligence → AI.
- **Products**: product experiences built on top of the engine.
- **Providers**: external data sources such as Fantrax, NHL, Yahoo, ESPN, CBS, Sleeper and future integrations.
- **Consumers**: APIs, websites, desktop apps, mobile apps, dashboards, AI assistants and other applications that consume engine output.
- **Canonical objects**: normalized data contracts produced by Build and consumed by Knowledge and Intelligence.

## Product Set

The shared engine currently frames three primary products:

1. **Fantasy Sports Intelligence**
2. **Public Sports Intelligence**
3. **AI Content Platform**

A future API layer is treated as a platform consumer, not as a separate calculation engine.

## Language Rules

- Engine documentation should use provider-neutral and sport-neutral language.
- Product-specific language belongs in product documentation.
- Provider names should appear in provider documentation and implementation notes, not in shared engine concepts.
- AI explains deterministic intelligence. It does not invent facts or bypass the pipeline.
