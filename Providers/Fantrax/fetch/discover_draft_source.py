"""Authenticated Fantrax draft-pick source discovery.

Runs locally with Athena's existing Fantrax session. It never prints cookies,
Secret IDs, request headers, or other credential values. The raw provider
payload is retained in Raw/draft_picks.json for later schema-driven Build work;
a safe structural report is written to Reports.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Core.project_paths import RAW_DIR
from Providers.Fantrax.fantrax_client import FantraxClient

REPORT_DIR = PROJECT_ROOT / "Reports" / "fantrax_draft_discovery"
RAW_OUTPUT = RAW_DIR / "draft_picks.json"
SENSITIVE_TERMS = ("cookie", "secret", "token", "authorization", "password", "credential", "session")


def _safe_key(key: Any) -> bool:
    lowered = str(key).lower()
    return not any(term in lowered for term in SENSITIVE_TERMS)


def _shape(value: Any, depth: int = 0) -> Any:
    if depth >= 4:
        if isinstance(value, list):
            return {"type": "list", "count": len(value)}
        if isinstance(value, dict):
            return {"type": "object", "keys": [str(k) for k in value.keys() if _safe_key(k)][:30]}
        return type(value).__name__
    if isinstance(value, dict):
        return {str(k): _shape(v, depth + 1) for k, v in list(value.items())[:40] if _safe_key(k)}
    if isinstance(value, list):
        return {"type": "list", "count": len(value), "sample": [_shape(v, depth + 1) for v in value[:2]]}
    return type(value).__name__


def _find_lists(value: Any, path: str = "root", depth: int = 0) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if depth > 6:
        return found
    if isinstance(value, list):
        sample_keys: list[str] = []
        if value and isinstance(value[0], dict):
            sample_keys = [str(k) for k in value[0].keys() if _safe_key(k)][:30]
        found.append({"path": path, "count": len(value), "sample_keys": sample_keys})
        for i, item in enumerate(value[:2]):
            found.extend(_find_lists(item, f"{path}[{i}]", depth + 1))
    elif isinstance(value, dict):
        for key, item in value.items():
            if _safe_key(key):
                found.extend(_find_lists(item, f"{path}.{key}", depth + 1))
    return found


def main() -> None:
    print("Authenticated Fantrax Draft Source Discovery")
    print("=" * 72)
    client = FantraxClient()
    status = client.cookie_status()
    print(f"League ID: {client.league_id}")
    print(f"Season: {client.season}")
    print(f"Authenticated browser session available: {bool(status.get('present'))}")
    print(f"Cookie count: {status.get('cookie_count', 0)}")
    print("Credential values: REDACTED / NOT EXPORTED")
    print(f"Endpoint: {client.get_endpoint('draft_picks')}")

    payload = client.get_draft_picks()
    client.validate_payload(payload, "Fantrax draft picks")
    write_json(RAW_OUTPUT, payload)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "league_id": client.league_id,
        "season": client.season,
        "endpoint": client.get_endpoint("draft_picks"),
        "raw_output": str(RAW_OUTPUT),
        "top_level_type": type(payload).__name__,
        "top_level_keys": [str(k) for k in payload.keys() if _safe_key(k)] if isinstance(payload, dict) else [],
        "list_candidates": _find_lists(payload),
        "shape": _shape(payload),
        "credentials_exported": False,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"draft_source_discovery_{stamp}.json"
    write_json(report_path, report)

    print(f"Raw payload saved: {RAW_OUTPUT}")
    print(f"Safe discovery report: {report_path}")
    print(f"Top-level type: {report['top_level_type']}")
    print(f"Top-level keys: {report['top_level_keys']}")
    print("List candidates:")
    for item in report["list_candidates"]:
        print(f"  - {item['path']}: {item['count']} rows; keys={item['sample_keys']}")
    print("\nSafe structural shape:")
    print(json.dumps(report["shape"], indent=2, ensure_ascii=False))
    print("\nDiscovery complete. Copy this console output back into the development chat.")


if __name__ == "__main__":
    main()
