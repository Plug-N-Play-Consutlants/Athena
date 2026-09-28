from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Events.live_sources import discover_current_news
from Providers.Fantrax.fantrax_provider import FantraxProvider


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return bool(ok)


def main() -> int:
    passed = []
    passed.append(check("version", ATHENA_VERSION == "0.6.4.1.3", ATHENA_VERSION))
    passed.append(check("release", RELEASE_NAME == "Current Information and Fantrax Connection Patch", RELEASE_NAME))

    xml = b'''<?xml version="1.0"?><rss><channel><item><title>Toronto Maple Leafs announce training camp roster</title><link>https://example.test/leafs-camp</link><pubDate>Wed, 16 Sep 2026 12:00:00 GMT</pubDate><description>Toronto Maple Leafs open camp with roster updates.</description></item></channel></rss>'''
    items = discover_current_news('"Toronto Maple Leafs" nhl', raw_payload=xml)
    passed.append(check("current_news_discovery", len(items) == 1, str(items[0].get("title") if items else "")))
    passed.append(check("discovery_provenance", bool(items and items[0].get("url") and items[0].get("published_at") and items[0].get("discovery_role") == "discovery"), str(items[0] if items else {})))

    class FakeClient:
        created = []
        next_league = "league-a"
        def __init__(self):
            self.league_id = type(self).next_league
            type(self).created.append(self.league_id)
        def validate_config(self): return None
        def cookie_status(self): return {"present": True, "source": "fixture", "cookie_count": 1}
        def has_cookie_auth(self): return True

    with patch("Providers.Fantrax.fantrax_provider.FantraxClient", FakeClient):
        provider = FantraxProvider()
        first = provider._get_client("league-a")
        FakeClient.next_league = "league-b"
        second = provider._get_client("league-b")
        passed.append(check("fantrax_client_rebound", first is not second and second.league_id == "league-b", str(FakeClient.created)))

    print(f"Overall status: {'PASS' if all(passed) else 'FAIL'}")
    return 0 if all(passed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
