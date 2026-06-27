# File Usefulness Audit — v0.5.5.5.21

## Purpose

This audit classifies the current AthenaEngine repository by **file usefulness**, **active engineering value**, and **cleanup risk**.

This is intentionally not an architecture rewrite. It is a visibility pass that reduces uncertainty before deletion, consolidation, or program-structure rework.

## Repository Snapshot

- Total files scanned: **936**
- Python files: **581**
- Python parse errors: **0**
- Generated inventory: `docs/FILE_USEFULNESS_INVENTORY_v0.5.5.5.21.csv`

## Usefulness Classification Counts

|Classification|Files|
|---|---|
|ARCHIVE_ALREADY|90|
|ARCHIVE_CANDIDATE|127|
|ENTRYPOINT_OR_UNUSED_REVIEW|56|
|KEEP_ACTIVE|291|
|KEEP_DOC|43|
|KEEP_TEST|135|
|KEEP_VALIDATION_OR_DOCTOR|77|
|LEGACY_SHIM_REVIEW|23|
|RUNTIME_DATA_REVIEW|94|

## Role Counts

|Role|Files|
|---|---|
|ATHENA_PACKAGE|10|
|AUDIT_TOOL|2|
|CLEANUP_TOOL|8|
|CONFIG|7|
|CORE|9|
|DOC|177|
|DOCTOR|77|
|ENGINE|32|
|INTELLIGENCE|27|
|KNOWLEDGE|114|
|PROVIDER|43|
|REASONING|61|
|ROOT_OR_MISC|21|
|RUNTIME_OR_ARTIFACT|184|
|SCOUT|11|
|SPORTS|2|
|TEST|135|
|TOOL|16|

## Immediate Safe Cleanup Candidates

These files are reproducible bytecode/cache artifacts and can be deleted without changing source behavior.

No bytecode/cache files are present in this patched package. The cleanup tool still supports deleting them on the installed working copy.

## High-Noise Active-Surface Candidates

### Historical root manifests / legacy top-level readmes

- Count: **127**
- Recommended action: move under a historical archive path such as `Archive/Manifests/` or `docs/archive/`, not delete blindly.
- Reason: useful for history, low value in active repository root.

### Runtime/generated data

- Count: **94**
- Recommended action: keep runtime directories but exclude them from active source review. Add clear retention rules later.
- Reason: useful for diagnostics and acceptance testing, but should not be confused with source.

## Legacy Shim Review

These files appear to be compatibility shims, root aliases, or operational wrappers. They should not be deleted until import/entrypoint usage is confirmed.

|File|Reason|
|---|---|
|Athena/capabilities.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Athena/connect.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Athena/debug_export.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Athena/exceptions.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Athena/operation_result.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Athena/orchestrator.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Athena/status.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Athena/sync.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Athena/workspace.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Intelligence/Runtime/orchestrator.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|Tools/doctor.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|build_engine.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|capabilities.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|connect.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|debug_export.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|doctor.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|exceptions.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|launch.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|operation_result.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|orchestrator.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|status.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|sync.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|
|workspace.py|Root or package-level Python shim/alias; confirm entrypoint usage before deletion.|

## Entry Point or Unused Review

These Python modules are not imported by another internal Python module in the static AST graph. That does **not** prove they are unused. Many may be dynamic entrypoints, provider build modules, or scripts invoked by Studio/Tools/tests.

Recommended action: classify each as one of:

- `KEEP_ENTRYPOINT`
- `KEEP_DYNAMIC_IMPORT`
- `MERGE_REVIEW`
- `DELETE_CANDIDATE`
- `UNKNOWN`

First 60 candidates:

|File|Role|Reason|
|---|---|---|
|Knowledge/Historical/registration.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/Intelligence/Entities/disambiguation.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/asset_registry.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/comparison_engine.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/decision_engine.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/knowledge_readiness.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/league_market.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/league_profile.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/league_settings.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/league_strategy.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/player_bio.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/player_contracts.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/player_identity_resolver.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/player_production.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/player_profile.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/player_status.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/team_direction.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/team_profile.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Knowledge/transaction_history.py|KNOWLEDGE|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/ESPN/__init__.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/ESPN/build/__init__.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/ESPN/fetch/__init__.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/Fantrax/build/draft_pick_master.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/Fantrax/build/league_settings.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/Fantrax/build/player_master.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/Fantrax/build/transaction_master.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/NHL/build/__init__.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/NHL/fetch/__init__.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/NHL/fetch/fetch_player_landing.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/NHL/fetch/fetch_skater_summary.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/Yahoo/__init__.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/Yahoo/build/__init__.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Providers/Yahoo/fetch/__init__.py|PROVIDER|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/assessment_builder.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/bridges/contract_bridge.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/bridges/explainability_bridge.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/bridges/graph_bridge.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/bridges/historical_bridge.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/bridges/knowledge_pack_bridge.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/bridges/rule_bridge.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/bridges/temporal_bridge.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/composition/build002_patch.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/composition/build003_patch.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/composition/build004_patch.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/evidence/evidence_collector.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/evidence/evidence_provider.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/evidence/evidence_weighting.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/models/assessment.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/models/historical_value.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/models/organizational_value.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/models/trend_value.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/primitives/assessment_registry.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/primitives/base_primitive.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/primitives/confidence_engine.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/reasoning_object.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|
|Reasoning/reasoning_session.py|REASONING|Not imported by another internal module in static AST graph; may be entrypoint, dynamic import, or unused.|

## Duplicate Filename Hotspots

Duplicate names are not automatically bad, but they make navigation harder and may indicate repeated model/registry patterns that can be consolidated later.

|Filename|Count|Examples|
|---|---|---|
|__init__.py|62|__init__.py<br>Athena/__init__.py<br>Core/__init__.py<br>Diagnostics/__init__.py<br>Engine/__init__.py<br>Intelligence/__init__.py<br>Knowledge/__init__.py<br>Providers/__init__.py<br>...|
|models.py|9|Knowledge/Events/models.py<br>Knowledge/Historical/models.py<br>Knowledge/Identity/models.py<br>Knowledge/Trends/models.py<br>Intelligence/Explainability/models.py<br>Intelligence/Reasoning/models.py<br>Intelligence/Runtime/models.py<br>Engine/EventReasoning/models.py<br>...|
|README.md|7|README.md<br>Configuration/README.md<br>Engine/README.md<br>Scout/README.md<br>Archive/patch_notes_and_root_duplicates_20260618/README.md<br>Archive/retired_configuration_examples_20260618/README.md<br>Archive/retired_fantrax_legacy_endpoints_20260618/README.md|
|registry.py|7|Sports/registry.py<br>Providers/base/registry.py<br>Knowledge/Events/registry.py<br>Knowledge/Historical/registry.py<br>Knowledge/Identity/registry.py<br>Knowledge/Trends/registry.py<br>Engine/MultiSport/registry.py|
|orchestrator.py|5|orchestrator.py<br>Athena/orchestrator.py<br>Intelligence/Runtime/orchestrator.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/orchestrator.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/orchestrator.py|
|CHANGE_MANIFEST_v0.5.0_drop4e14_scout_fantasy_routing_ux.md|4|CHANGE_MANIFEST_v0.5.0_drop4e14_scout_fantasy_routing_ux.md<br>Athena/CHANGE_MANIFEST_v0.5.0_drop4e14_scout_fantasy_routing_ux.md<br>Archive/runtime_quarantine/nested_athena_20260622_002814/CHANGE_MANIFEST_v0.5.0_drop4e14_scout_fantasy_routing_ux.md<br>Archive/runtime_quarantine/nested_athena_20260622_172902/CHANGE_MANIFEST_v0.5.0_drop4e14_scout_fantasy_routing_ux.md|
|CHANGE_MANIFEST_v0.5.0_drop4e6_scout_js_binding_hotfix.md|4|CHANGE_MANIFEST_v0.5.0_drop4e6_scout_js_binding_hotfix.md<br>Athena/CHANGE_MANIFEST_v0.5.0_drop4e6_scout_js_binding_hotfix.md<br>Archive/runtime_quarantine/nested_athena_20260622_002814/CHANGE_MANIFEST_v0.5.0_drop4e6_scout_js_binding_hotfix.md<br>Archive/runtime_quarantine/nested_athena_20260622_172902/CHANGE_MANIFEST_v0.5.0_drop4e6_scout_js_binding_hotfix.md|
|capabilities.py|4|capabilities.py<br>Athena/capabilities.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/capabilities.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/capabilities.py|
|confidence_engine.py|4|Reasoning/primitives/confidence_engine.py<br>Knowledge/Historical/confidence_engine.py<br>Knowledge/Trends/confidence_engine.py<br>Engine/EventConfidence/confidence_engine.py|
|connect.py|4|connect.py<br>Athena/connect.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/connect.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/connect.py|
|debug_export.py|4|debug_export.py<br>Athena/debug_export.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/debug_export.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/debug_export.py|
|exceptions.py|4|exceptions.py<br>Athena/exceptions.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/exceptions.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/exceptions.py|
|operation_result.py|4|operation_result.py<br>Athena/operation_result.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/operation_result.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/operation_result.py|
|status.py|4|status.py<br>Athena/status.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/status.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/status.py|
|sync.py|4|sync.py<br>Athena/sync.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/sync.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/sync.py|
|workspace.py|4|workspace.py<br>Athena/workspace.py<br>Archive/runtime_quarantine/nested_athena_20260622_002814/workspace.py<br>Archive/runtime_quarantine/nested_athena_20260622_172902/workspace.py|
|comparison_engine.py|3|Knowledge/comparison_engine.py<br>Knowledge/Historical/comparison_engine.py<br>Knowledge/Trends/comparison_engine.py|
|confidence.py|3|Reasoning/models/confidence.py<br>Knowledge/Historical/confidence.py<br>Knowledge/Trends/confidence.py|
|engine.py|3|Knowledge/Historical/engine.py<br>Knowledge/Trends/engine.py<br>Intelligence/Reasoning/engine.py|
|reasoning_engine.py|3|Reasoning/reasoning_engine.py<br>Knowledge/Graph/reasoning_engine.py<br>Engine/EventReasoning/reasoning_engine.py|

## Safe Cleanup Tool

This patch adds `Tools/cleanup_safe_repository_noise.py`.

Default dry run:

```text
python Tools\cleanup_safe_repository_noise.py
```

Delete only Python cache/bytecode artifacts:

```text
python Tools\cleanup_safe_repository_noise.py --apply
```

Optional historical-root cleanup:

```text
python Tools\cleanup_safe_repository_noise.py --archive-root-history --apply
```

The historical-root cleanup moves root-level `CHANGE_MANIFEST_*` and legacy `README_*` files into `Archive/Manifests/`. It is opt-in because those files are useful historical records even though they are noisy in the active repository root.

## Recommended Cleanup Order

1. Delete bytecode/cache artifacts.
2. Move historical root manifests/readmes into a history archive folder.
3. Mark runtime/output folders as generated/non-source in the audit docs.
4. Review root-level Python aliases and Athena package duplicate aliases.
5. Audit unimported provider/build/knowledge files before deletion because many may be dynamically invoked.
6. Only then consolidate architecture-level overlaps across `Engine/`, `Intelligence/`, `Reasoning/`, and `Knowledge/Intelligence`.

## Guardrails

Do not delete a file only because the static import graph does not see it. Athena uses scripts, Studio subprocesses, dynamic imports, validators, and operational entrypoints. Static analysis is a screening tool, not a deletion authority.
