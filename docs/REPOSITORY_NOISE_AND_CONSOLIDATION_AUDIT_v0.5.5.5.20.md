# Repository Noise and Consolidation Audit — v0.5.5.5.20

## Purpose

This document identifies noise and consolidation candidates in the current AthenaEngine repository. It does not authorize broad deletion. The goal is to reduce confusion without damaging validated behavior.

## Immediate noise findings

### Root-level release manifests

The repository root currently contains more than one hundred `CHANGE_MANIFEST_*.md` files.

Assessment:

- They are useful history.
- They are not runtime code.
- They make the root look much noisier than it is.
- They should eventually move under `docs/history/` or `Archive/release_history_root/`.

Risk:

```text
Low, if no launcher/doctor expects root-level manifests.
```

Recommended action:

```text
Do not manually delete.
Use a cleanup script or approved move once doctors confirm no root-manifest dependency.
```

### Root README variants

Several old `README_*` files remain at root.

Assessment:

- Most are release-era instructions.
- They should be archived by theme or version.
- The root should retain only current project README, launch instructions, and active operational guidance.

Risk:

```text
Low to medium, depending on whether any user-facing launch note is still current.
```

### Runtime artifacts

The snapshot includes runtime/output paths such as:

```text
Raw/
Output/
Logs/
Reports/
```

Assessment:

- These are useful during acceptance testing.
- They should remain gitignored/local.
- Some sample data may need to move into a future `samples/` or `fixtures/` directory if it is required for validation.

Risk:

```text
Medium. Do not delete blindly.
```

### Python caches

The snapshot includes Python cache artifacts:

```text
Scout/__pycache__/
Tools/__pycache__/
*.pyc
```

Assessment:

- These are safe to delete.
- They should not be distributed in patches.
- `.gitignore` already excludes them.

Risk:

```text
Very low.
```

### Archive/runtime_quarantine

There are quarantined nested-runtime files that duplicate canonical package names.

Assessment:

- They are outside the active import path.
- They are useful as historical evidence of prior root/nesting issues.
- They increase duplicate-name noise when searching the repo.

Risk:

```text
Low if retained in Archive. Medium if removed before the acceptance period closes.
```

## Architectural consolidation candidates

### `Scout/conversation/router.py`

Symptom:

- Very large deterministic multiplexer.
- Owns public routing, league/fantasy handlers, live events, diagnostics, and fallback behavior.

Do not split yet.

Future split candidate:

```text
Scout/conversation/routes/
  league_routes.py
  public_routes.py
  event_routes.py
  diagnostic_routes.py
  fallback_routes.py
```

Prerequisite:

- Route map and typed route contracts for every branch.

### `Knowledge/Intelligence/Public/public_answers.py`

Symptom:

- Owns answer construction for players, teams, comparisons, gaps, and copy cleanup.
- It is drifting toward composition and reasoning responsibilities.

Do not split yet.

Future split candidate:

```text
Composition/public/
  player_profile.py
  team_profile.py
  comparison.py
  gap_language.py
```

Prerequisite:

- Public answer payload contract.

### `Engine/`, `Intelligence/`, and `Reasoning/`

Symptom:

- Multiple namespaces contain engines, models, confidence, reasoning, events, and runtime concepts.
- The naming overlap is real but not automatically wrong.

Do not merge by folder name alone.

Future direction:

```text
Evidence
Reasoning
Composition
Runtime
```

Prerequisite:

- One vertical slice proves which layer owns evidence, reasoning, confidence, and narrative.

## Safe cleanup tool

This build adds:

```text
Tools/cleanup_repository_noise.py
```

Default behavior is dry-run only.

Safe command:

```text
python Tools/cleanup_repository_noise.py
```

Cache cleanup:

```text
python Tools/cleanup_repository_noise.py --apply
```

Historical manifest move, only after explicit approval:

```text
python Tools/cleanup_repository_noise.py --apply --apply-manifests
```

## Do not delete

Do not delete these until the traceability audit marks them unused:

```text
Output/
Raw/
Reports/
Logs/
Archive/
Engine/
Intelligence/
Reasoning/
Knowledge/Intelligence/
Scout/conversation/
```

They may be noisy, but they are not yet proven dead.

## Recommended next cleanup sequence

1. Keep v0.5.5.5.20 as an audit checkpoint.
2. Run `Tools/audit_evidence_paths.py --write-report`.
3. Run `Tools/cleanup_repository_noise.py` dry-run.
4. Trace the `Leafs weakness` vertical slice.
5. Add a typed evidence packet for that slice.
6. Only then split or move code.
