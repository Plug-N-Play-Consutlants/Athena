"""Offline, deterministic source-format tests. NOT a live-provider acceptance test."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from types import SimpleNamespace
from Knowledge.Contracts.public_cap_benchmark import (
    parse_sportsnet_cap_page, acquire_sportsnet_cap_benchmark, TEAM_SLUGS,
)

HTML = '''<html><body><script>fake 999</script><div>TEAM SALARY</div>
<div>PROJECTED TOTAL CAP HIT</div><span>$107,936,241</span>
<div>103.78% OF CAP (SALARY CAP: $104M)</div>
<div>PROJECTED CAP SPACE</div><span>-$3,936,241</span>
<div>CAP SPACE TODAY</div><span>-$3,936,241</span></body></html>'''

class Tests(unittest.TestCase):
    def test_parse_source_observation(self):
        value = parse_sportsnet_cap_page('TOR', HTML, retrieved_at='2026-10-16T20:00:00Z')
        self.assertEqual((value.projected_total, value.projected_space, value.cap_ceiling),
                         (107936241, -3936241, 104000000))
        self.assertIn('sportsnet.ca', value.source_url)
    def test_no_automatic_authorization(self):
        with self.assertRaises(PermissionError):
            acquire_sportsnet_cap_benchmark('TOR')
    def test_opt_in_bounded_transport(self):
        calls = []
        def transport(url, **kwargs):
            calls.append((url, kwargs))
            return SimpleNamespace(status_code=200, content=HTML.encode())
        result = acquire_sportsnet_cap_benchmark('TOR', authorized=True, transport=transport,
                                                 retrieved_at='2026-10-16T20:00:00Z')
        self.assertEqual(result.projected_total, 107936241)
        self.assertEqual(calls[0][1]['allow_redirects'], False)
    def test_no_promoted_completeness(self):
        result = parse_sportsnet_cap_page('TOR', HTML, retrieved_at='2026-10-16T20:00:00Z')
        self.assertFalse(hasattr(result, 'charges'))
        self.assertFalse(hasattr(result, 'verified_domains'))
    def test_reject_page_drift(self):
        for html in ('<p>no cap</p>', HTML.replace('$107,936,241', '$97,936,241'),
                     HTML.replace('PROJECTED CAP SPACE', 'NOT A CAP VALUE')):
            with self.assertRaises(ValueError):
                parse_sportsnet_cap_page('TOR', html, retrieved_at='2026-10-16T20:00:00Z')
    def test_known_teams(self):
        self.assertEqual(len(TEAM_SLUGS), 32)

if __name__ == '__main__':
    unittest.main()
