"""Doctor for Athena 0.5.3.1.0 Official Multi-Sport Provider Connectors."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "Engine/MultiSport/__init__.py",
    "Engine/MultiSport/models.py",
    "Engine/MultiSport/registry.py",
    "Engine/MultiSport/connectors.py",
    "Knowledge/Events/multi_sport.py",
    "Tests/validate_multi_sport_provider_connectors.py",
    "Tools/doctor_multi_sport_provider_connectors.py",
]
REQUIRED_EXPORTS = {
    "MultiSportRegistry",
    "OfficialMultiSportConnector",
    "connector_capability_report",
    "run_official_connector",
    "seed_multi_sport_registry",
}


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def exports_from_init() -> set[str]:
    init_file = PROJECT_ROOT / "Engine" / "MultiSport" / "__init__.py"
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


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    numeric = []
    for part in parts[:5]:
        try:
            numeric.append(int(part))
        except ValueError:
            numeric.append(0)
    while len(numeric) < 5:
        numeric.append(0)
    return tuple(numeric)  # type: ignore[return-value]

def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def main() -> int:
    print("Official Multi-Sport Provider Connectors Doctor")
    print("=" * 64)
    checks: list[bool] = []
    for rel in REQUIRED_FILES:
        checks.append(report(f"required file exists: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME
    checks.append(report("version metadata is 0.5.3.1.0 or later", _version_at_least(ATHENA_VERSION, "0.5.3.1.0") and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("release name is available", bool(RELEASE_NAME), RELEASE_NAME))

    exports = exports_from_init()
    checks.append(report("MultiSport exports canonical symbols", REQUIRED_EXPORTS.issubset(exports), ", ".join(sorted(exports))))

    from Engine.MultiSport import connector_capability_report, run_official_connector, seed_multi_sport_registry
    registry = seed_multi_sport_registry()
    checks.append(report("registry has at least five sports", len(registry.sports) >= 5, ", ".join(sorted(registry.sports))))
    checks.append(report("registry has official connectors", len(registry.connectors) >= 6, ", ".join(sorted(registry.connectors))))
    checks.append(report("capability report is available", _version_at_least(connector_capability_report(registry).version, "0.5.3.1.0")))
    result = run_official_connector("nba")
    checks.append(report("sample NBA connector run succeeds", result.status == "success" and result.events and result.events[0].league == "nba", str(result.to_dict())))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
