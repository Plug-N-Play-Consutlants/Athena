"""Doctor for Athena 0.5.1.4.0 Official NHL Feed Connectors."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))
    return name, condition, detail


def main() -> int:
    print("Official NHL Feed Connectors Doctor")
    print("=" * 64)
    checks: list[tuple[str, bool, str]] = []

    version_file = PROJECT_ROOT / "Core" / "version.py"
    version_text = version_file.read_text(encoding="utf-8") if version_file.exists() else ""
    checks.append(check("version is 0.5.1.4.0 or later", 'VERSION_SCHEMA = "major.epic.sprint.patch.hotfix"' in version_text and ('ATHENA_VERSION = "0.5.1.4.0"' in version_text or 'ATHENA_VERSION = "0.5.1.5.' in version_text or 'ATHENA_VERSION = "0.5.2.' in version_text), str(version_file)))
    checks.append(check("repository standard remains AthenaEngine", 'REPOSITORY_NAME = "AthenaEngine"' in version_text and 'PYTHON_PACKAGE_NAME = "Athena"' in version_text, "root renamed; package preserved"))

    required = [
        "Knowledge/Events/feeds.py",
        "Knowledge/Events/acquisition.py",
        "Knowledge/Events/nhl_official.py",
        "Knowledge/Events/__init__.py",
        "Tests/validate_official_nhl_feed_connectors.py",
        "Tools/doctor_official_nhl_feed_connectors.py",
    ]
    for rel in required:
        checks.append(check(f"required file present: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    try:
        events = importlib.import_module("Knowledge.Events")
        checks.append(check("NHL exports are available", all(hasattr(events, name) for name in ["NhlOfficialApiConnector", "seed_nhl_feed_registry", "seed_nhl_connector_registry", "acquire_nhl_official_sample"]), "Knowledge.Events exports"))
        feeds = events.seed_nhl_feed_registry()
        checks.append(check("NHL feed registry has official feeds", {"nhl_official_schedule", "nhl_official_standings", "nhl_official_club_stats"}.issubset(set(feeds.feeds)), str(list(feeds.feeds))))
        checks.append(check("official NHL connector can acquire sample", events.acquire_nhl_official_sample().status == "success", events.acquire_nhl_official_sample().to_dict().__repr__()[:240]))
        checks.append(check("connector summary is network-safe", events.nhl_connector_summary().get("network_safe_by_default") is True, str(events.nhl_connector_summary())))
    except Exception as exc:
        checks.append(check("NHL connector imports and smoke test", False, str(exc)))

    failed = [item for item in checks if not item[1]]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    if failed:
        for name, _, detail in failed:
            print(f"[FAIL] {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
