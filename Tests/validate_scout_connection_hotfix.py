"""Validate Scout/Fantrax connection hotfix 3F.1a.

This test verifies that Athena connection workspace updates do not pass
provider/provider_key/league_id twice when provider context inference returns
provider metadata. It uses a local fake provider and does not call Fantrax.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.project_paths import CONFIGURATION_DIR, RAW_DIR
connect_module = importlib.import_module("Athena.connect")
from Athena.workspace import load_workspace
from Scout import app

WORKSPACE_FILE = CONFIGURATION_DIR / "workspace.json"
SECRETS_FILE = CONFIGURATION_DIR / "secrets.local.json"
RAW_LEAGUE_FILE = RAW_DIR / "league_info.json"


class FakeStatus:
    def to_dict(self) -> Dict[str, Any]:
        return {"ok": True, "provider": "Fantrax", "authenticated": True}


class FakeFantraxProvider:
    provider_name = "Fantrax"

    def connect(self, **kwargs: Any) -> Dict[str, Any]:
        return {"ok": True, "state": "connected", "authenticated": True, "kwargs": kwargs}

    def test(self, **kwargs: Any) -> Dict[str, Any]:
        return {"ok": True, "message": "Fake Fantrax validation succeeded.", "kwargs": kwargs}

    def fetch(self, resource: str) -> Dict[str, Any]:
        if resource != "league":
            return {}
        return {
            "leagueName": "Hotfix Test League",
            "seasonYear": 2025,
            "teamInfo": {"1": {"name": "A"}, "2": {"name": "B"}},
            "rosterInfo": {"positionConstraints": {"C": {}, "LW": {}, "RW": {}, "D": {}}},
            "scoringSystem": {"Goal": 1, "Assist": 1},
        }

    def status(self) -> FakeStatus:
        return FakeStatus()


def check(name: str, condition: bool, message: str, results: list[dict]) -> None:
    results.append({"name": name, "status": "PASS" if condition else "FAIL", "message": message})


def read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def restore(path: Path, content: str | None) -> None:
    if content is None:
        if path.exists():
            path.unlink()
    else:
        path.write_text(content, encoding="utf-8")


def main() -> int:
    results: list[dict] = []
    original_get_provider = connect_module.get_provider
    original_registered = connect_module.registered_providers
    workspace_backup = read_text(WORKSPACE_FILE)
    secrets_backup = read_text(SECRETS_FILE)
    raw_backup = read_text(RAW_LEAGUE_FILE)

    try:
        connect_module.get_provider = lambda provider: FakeFantraxProvider()  # type: ignore[assignment]
        connect_module.registered_providers = lambda: ["fantrax"]  # type: ignore[assignment]

        result = connect_module.connect_provider(
            provider="fantrax",
            league_id="hotfix_league_id",
            auth_cookie="session=hotfix; fantraxToken=abc123",
            validate=True,
            mode="fantasy_league",
        )
        workspace = load_workspace().get("workspace", {})

        check(
            "connect_provider_no_duplicate_provider_kwarg",
            result.get("ok") is True,
            f"connect_provider completed without duplicate provider keyword error: {result.get('message')}",
            results,
        )
        check(
            "workspace_provider_preserved",
            workspace.get("provider") == "Fantrax" and workspace.get("provider_key") == "fantrax",
            f"Workspace provider={workspace.get('provider')!r}; provider_key={workspace.get('provider_key')!r}.",
            results,
        )
        check(
            "workspace_league_id_saved",
            workspace.get("league_id") == "hotfix_league_id",
            f"Workspace league_id={workspace.get('league_id')!r}.",
            results,
        )
        check(
            "workspace_inferred_context_saved",
            workspace.get("league_name") == "Hotfix Test League" and workspace.get("sport") == "NHL" and str(workspace.get("season")) == "2025",
            f"Workspace league_name={workspace.get('league_name')!r}; sport={workspace.get('sport')!r}; season={workspace.get('season')!r}.",
            results,
        )
        check(
            "scout_version_hotfix_visible",
            "Scout Alpha v0.5.0 Drop 3F.1a" in app.INDEX_HTML,
            "Scout UI displays the 3F.1a hotfix version.",
            results,
        )
    except Exception as exc:
        check("hotfix_unhandled_exception", False, f"Unexpected exception: {exc}", results)
    finally:
        connect_module.get_provider = original_get_provider  # type: ignore[assignment]
        connect_module.registered_providers = original_registered  # type: ignore[assignment]
        restore(WORKSPACE_FILE, workspace_backup)
        restore(SECRETS_FILE, secrets_backup)
        restore(RAW_LEAGUE_FILE, raw_backup)

    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = sum(1 for item in results if item["status"] == "FAIL")
    overall = "PASS" if failed == 0 else "FAIL"

    report_lines = [
        "Scout Connection Hotfix Validation Report",
        "==========================================",
        f"Overall status: {overall}",
        f"Passed: {passed}",
        "Warnings: 0",
        f"Failed: {failed}",
        "",
    ]
    for item in results:
        report_lines.append(f"[{item['status']}] {item['name']}: {item['message']}")

    reports_dir = PROJECT_ROOT / "Reports"
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "scout_connection_hotfix_validation_report.json").write_text(
        json.dumps({"overall_status": overall, "results": results}, indent=2), encoding="utf-8"
    )
    (reports_dir / "scout_connection_hotfix_validation_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    print("\n".join(report_lines))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
