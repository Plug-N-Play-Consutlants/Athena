"""Studio Sync League snapshot must remain distinct from Scout's editorial answers."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from Athena import sync as _unused  # intentional package import for release compatibility
import importlib
sync_module = importlib.import_module('Athena.sync')
from Tools.athena_studio import _command_summary, _sync_league_snapshot_lines


class LeagueSnapshotTests(unittest.TestCase):
    def test_canonical_summary_uses_league_profile_and_market(self):
        def read(path):
            records = {
                'league_profile.json': {'league_name': 'JHLPAA', 'season': 2026, 'league_id': 'abc', 'team_count': 14},
                'league_settings.json': {'team_count': 14, 'teams': [{'id': i} for i in range(14)]},
                'player_master.json': [{'id': i} for i in range(290)],
                'transaction_master.json': {'record_count': 59},
                'transaction_history.json': {'asset_movement_count': 116},
                'manager_behavior.json': {'manager_count': 14},
                'league_market.json': {'market_liquidity': {'classification': 'thin'}},
                'knowledge_readiness.json': {'readiness_score': 0.87},
            }
            return records.get(path.name)
        with patch.object(sync_module, '_read_json', side_effect=read):
            summary = sync_module._read_output_summary()
        self.assertEqual(summary['team_count'], 14)
        self.assertEqual(summary['canonical_transactions'], 59)
        self.assertEqual(summary['market_liquidity'], 'thin')
        self.assertEqual(summary['player_count'], 290)

    def test_success_shows_sync_snapshot_not_weekly_editorial(self):
        payload = {'ok': True, 'summary': {'league_name': 'JHLPAA', 'season': 2026,
                   'team_count': 14, 'player_count': 290, 'canonical_transactions': 59,
                   'market_liquidity': 'thin'}}
        output = json.dumps(payload, indent=2) + '\n[PASS] Canonical Fantrax sync completed.\n'
        result = '\n'.join(_command_summary('Sync League', 0, output, Path('sync.txt')))
        self.assertIn('Teams: 14', result)
        self.assertIn('Transactions: 59', result)
        self.assertIn('Market liquidity: thin', result)
        self.assertNotIn('Week 7', result)

    def test_failed_sync_does_not_present_stale_snapshot(self):
        payload = {'ok': False, 'summary': {'team_count': 14, 'canonical_transactions': 59}}
        output = json.dumps(payload) + '\n[FAIL] Canonical Fantrax sync: fetch failed\n'
        result = '\n'.join(_command_summary('Sync League', 1, output, Path('sync.txt')))
        self.assertIn('[FAIL]', result)
        self.assertNotIn('Teams: 14', result)
        self.assertEqual(_sync_league_snapshot_lines(output), [])

    def test_non_sync_commands_stay_compact(self):
        output = json.dumps({'ok': True, 'summary': {'team_count': 14}})
        result = '\n'.join(_command_summary('Verify Build', 0, output, Path('verify.txt')))
        self.assertNotIn('Teams:', result)

if __name__ == '__main__':
    unittest.main()
