"""Doctor for Athena 0.5.3.2.0 Unified Identity & Cross-Sport Knowledge Graph."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "Knowledge/Identity/__init__.py",
    "Knowledge/Identity/models.py",
    "Knowledge/Identity/registry.py",
    "Knowledge/Identity/resolver.py",
    "Knowledge/Identity/graph.py",
    "Tests/validate_unified_identity_cross_sport_graph.py",
    "Tools/doctor_unified_identity_cross_sport_graph.py",
]
REQUIRED_EXPORTS = {
    "IDENTITY_MODEL_VERSION",
    "IdentityEntity",
    "CrossSportIdentityRegistry",
    "seed_identity_registry",
    "resolve_identity",
    "resolve_external_identity",
    "build_cross_sport_identity_graph",
    "identity_graph_diagnostics",
    "studio_identity_graph_diagnostics",
}


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


def exports_from_init() -> set[str]:
    init_file = PROJECT_ROOT / "Knowledge" / "Identity" / "__init__.py"
    tree = ast.parse(init_file.read_text(encoding="utf-8"))
    exports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__" and isinstance(node.value, ast.List):
                    for item in node.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            exports.add(item.value)
    return exports


def main() -> int:
    print("Unified Identity & Cross-Sport Knowledge Graph Doctor")
    print("=" * 72)
    checks: list[bool] = []
    for rel in REQUIRED_FILES:
        checks.append(report(f"required file exists: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    checks.append(report("version metadata is 0.5.3.2.0 or later", _version_at_least(ATHENA_VERSION, "0.5.3.2.0") and ATHENA_BUILD == ATHENA_VERSION and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", ATHENA_VERSION))
    checks.append(report("release metadata is compatible", ATHENA_VERSION >= "0.5.3.2.0" and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", RELEASE_NAME))

    exports = exports_from_init()
    checks.append(report("Knowledge.Identity exports canonical symbols", REQUIRED_EXPORTS.issubset(exports), ", ".join(sorted(exports))))

    from Knowledge.Identity import build_cross_sport_identity_graph, resolve_external_identity, resolve_identity, seed_identity_registry, studio_identity_graph_diagnostics
    registry = seed_identity_registry()
    stats = registry.stats()
    checks.append(report("registry includes five sports", {"hockey", "football", "basketball", "baseball", "soccer"}.issubset(set(stats["sports"])), str(stats["sports"])))
    checks.append(report("registry includes target leagues", {"NHL", "NFL", "NBA", "MLB", "UEFA"}.issubset(set(stats["leagues"])), str(stats["leagues"])))
    checks.append(report("registry is provider-neutral", stats["provider_neutral"] is True, str(stats)))

    graph = build_cross_sport_identity_graph(registry)
    checks.append(report("identity graph has nodes and relationships", len(graph["nodes"]) >= 20 and len(graph["relationships"]) >= 20, f"nodes={len(graph['nodes'])}; relationships={len(graph['relationships'])}"))

    matthews = resolve_identity("Auston Mathtwes", sport="hockey", league="NHL", entity_type="player", registry=registry)
    aho = resolve_identity("Sebastian Aho", registry=registry)
    nba_team = resolve_external_identity("nba:team", "TOR", registry=registry)
    checks.append(report("fuzzy player identity resolves", matthews.best_match is not None and matthews.best_match.entity_id == "nhl.player.auston_matthews", matthews.to_dict()["reason"]))
    checks.append(report("ambiguous duplicate name is preserved", aho.ambiguous is True and len(aho.matches) >= 2, str([m.entity_id for m in aho.matches])))
    checks.append(report("external provider hint resolves without coupling", nba_team.best_match is not None and nba_team.best_match.entity_id == "nba.team.tor", nba_team.to_dict()["reason"]))

    studio = studio_identity_graph_diagnostics()
    checks.append(report("Studio diagnostics payload is available", studio["panel"] == "identity_graph" and studio["status"] in {"pass", "warn"}, str(studio.keys())))

    print("-" * 72)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
