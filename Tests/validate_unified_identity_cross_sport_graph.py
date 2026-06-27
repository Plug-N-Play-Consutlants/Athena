"""Validation for Athena 0.5.3.2.0 Unified Identity & Cross-Sport Knowledge Graph."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    nums = []
    for part in parts[:5]:
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    while len(nums) < 5:
        nums.append(0)
    return tuple(nums)  # type: ignore[return-value]


def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def main() -> int:
    print("Unified Identity & Cross-Sport Knowledge Graph Validation")
    print("=" * 72)
    checks: list[bool] = []

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    checks.append(report("version metadata is 0.5.3.2.0 or later", _version_at_least(ATHENA_VERSION, "0.5.3.2.0") and ATHENA_BUILD == ATHENA_VERSION and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", ATHENA_VERSION))
    checks.append(report("release metadata is compatible", ATHENA_VERSION >= "0.5.3.2.0" and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", RELEASE_NAME))

    from Knowledge.Identity import (
        IDENTITY_MODEL_VERSION,
        build_cross_sport_identity_graph,
        build_identity_relationships,
        identity_graph_diagnostics,
        identity_key_for_provider,
        resolve_external_identity,
        resolve_identity,
        seed_identity_registry,
        studio_identity_graph_diagnostics,
    )

    registry = seed_identity_registry()
    stats = registry.stats()
    checks.append(report("identity model version matches sprint", IDENTITY_MODEL_VERSION == "0.5.3.2.0", IDENTITY_MODEL_VERSION))
    checks.append(report("sports are cross-domain", {"hockey", "football", "basketball", "baseball", "soccer"}.issubset(set(stats["sports"])), str(stats["sports"])))
    checks.append(report("leagues are cross-domain", {"NHL", "NFL", "NBA", "MLB", "UEFA"}.issubset(set(stats["leagues"])), str(stats["leagues"])))
    checks.append(report("entity types include core graph types", {"sport", "league", "team", "player"}.issubset(set(stats["by_type"])), str(stats["by_type"])))
    checks.append(report("registry preserves provider-neutral contract", stats["provider_neutral"] is True, str(stats["provider_neutral"])))

    graph = build_cross_sport_identity_graph(registry)
    relationships = build_identity_relationships(registry)
    predicates = {relationship.predicate for relationship in relationships}
    checks.append(report("graph exposes node payloads", len(graph["nodes"]) == stats["entities"] and graph["nodes"][0]["provider_neutral"] is True, str(graph["nodes"][0])))
    checks.append(report("graph exposes relationship mappings", {"belongs_to_sport", "competes_in", "plays_for", "eligible_in_league", "has_external_identifier"}.issubset(predicates), str(sorted(predicates))))

    tor_query = resolve_identity("Toronto", registry=registry)
    tor_hockey = resolve_identity("Toronto", sport="hockey", league="NHL", entity_type="team", registry=registry)
    checks.append(report("overlapping city/team names remain ambiguous without context", tor_query.ambiguous is True and len(tor_query.matches) >= 2, str([m.entity_id for m in tor_query.matches])))
    checks.append(report("sport-aware team resolution disambiguates", tor_hockey.best_match is not None and tor_hockey.best_match.entity_id == "nhl.team.tor", tor_hockey.to_dict()["reason"]))

    matthews = resolve_identity("Auston Mathtwes", sport="hockey", league="NHL", entity_type="player", registry=registry)
    aho_ambiguous = resolve_identity("Sebastian Aho", registry=registry)
    aho_context = resolve_identity("Finnish Sebastian Aho", sport="hockey", league="NHL", entity_type="player", registry=registry)
    checks.append(report("fuzzy player query resolves", matthews.best_match is not None and matthews.best_match.entity_id == "nhl.player.auston_matthews", str(matthews.to_dict())))
    checks.append(report("duplicate-name player remains ambiguous", aho_ambiguous.ambiguous and len(aho_ambiguous.matches) >= 2, str([m.entity_id for m in aho_ambiguous.matches])))
    checks.append(report("duplicate-name player resolves with context", aho_context.best_match is not None and aho_context.best_match.entity_id == "nhl.player.sebastian_aho_car", str(aho_context.to_dict())))

    external = resolve_external_identity("mlb:team", "TOR", registry=registry)
    checks.append(report("external IDs resolve to canonical entity", external.best_match is not None and external.best_match.entity_id == "mlb.team.tor", str(external.to_dict())))
    checks.append(report("provider key helper is deterministic", identity_key_for_provider("Hockey", "NHL", "Player", "Auston Matthews") == "hockey:nhl:player:auston_matthews"))

    diagnostics = identity_graph_diagnostics(registry, relationships)
    studio = studio_identity_graph_diagnostics()
    checks.append(report("diagnostics include counts and ambiguity warnings", diagnostics.entity_count >= 20 and diagnostics.relationship_count >= 20 and diagnostics.ambiguous_names, str(diagnostics.to_dict())))
    checks.append(report("Studio-facing diagnostics are serializable", studio["panel"] == "identity_graph" and isinstance(studio["sample_nodes"], list) and isinstance(studio["sample_relationships"], list), str(studio.keys())))

    # Guard against the previous Event compatibility regression while this sprint layers onto Event Intelligence.
    from Knowledge.Events import canonical_event_payload, canonical_event_types, normalize_event_payload
    checks.append(report("Knowledge.Events compatibility exports remain intact", callable(canonical_event_payload) and callable(normalize_event_payload) and callable(canonical_event_types)))

    print("-" * 72)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
