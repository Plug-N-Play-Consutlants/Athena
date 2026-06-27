# Athena Engine Namespace

`Engine/` contains reusable deterministic algorithms and orchestration facades.

It does **not** replace the locked platform pipeline:

```text
Providers -> Fetch -> Build -> Knowledge -> Reasoning -> Intelligence -> Scout
```

Layer ownership remains:

- `Knowledge/` owns facts and registries.
- `Engine/` owns reusable deterministic algorithms and facades.
- `Reasoning/` owns conclusions.
- `Scout/` owns presentation.

The first namespace is `Engine/Events`, which composes the Event Intelligence
registries, feed discovery, acquisition, and evidence fusion introduced during
Epic 5 Sprint 1.
