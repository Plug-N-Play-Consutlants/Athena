"""Deterministic integration coverage for the JHLPAA weekly report path."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from Athena.Investigation.fantrax_period_calendar import resolve_unified_period
from Athena.Investigation.period_execution import _explicit_period_request, _match_date_period
from Athena.Investigation.standings_archive import save_snapshot
from Athena.Investigation.trading_block_history import compare_snapshots
from Athena.Inquiry.execution import summarize_recent_league_activity
from Scout.conversation.league_recap_narrative import compose_period_report
from Scout.conversation.context import ScoutContext
from Scout.conversation.router import route_question


PERIODS = [
    {"period": 1, "startDate": "2026-09-29", "endDate": "2026-10-04"},
    {"period": 2, "startDate": "2026-10-05", "endDate": "2026-10-11"},
    {"period": 3, "startDate": "2026-10-12", "endDate": "2026-10-18"},
    {"period": 4, "startDate": "2026-10-19", "endDate": "2026-10-25"},
]
SCHEDULE = {
    row["period"]: {"start": row["startDate"], "end": row["endDate"]}
    for row in PERIODS
}
QUESTION = (
    "Produce the JHLPAA weekly league report for the most recently completed period. "
    "Include standings, individual player performances, roster changes, trades, "
    "acquisitions, drops, and other relevant league activity. Compare results with "
    "the preceding period, identify the biggest movers and noteworthy developments, "
    "and distinguish verified evidence from unavailable information."
)


def _snapshot(period: int, alpha_rank: int, alpha_points: int, beta_rank: int, beta_points: int) -> dict:
    return {
        "league_id": "jhlpaa1",
        "season": 2026,
        "period": period,
        "source": "deterministic_acceptance_fixture",
        "timeframe": "FROM_SEASON_START",
        "complete": True,
        "teams": [
            {"team_id": "alpha", "name": "Alpha", "rank": alpha_rank, "points": alpha_points},
            {"team_id": "beta", "name": "Beta", "rank": beta_rank, "points": beta_points},
        ],
    }


class _UnauthenticatedFantrax:
    def __init__(self, **kwargs):
        pass

    def has_cookie_auth(self):
        return False


class WeeklyReportAcceptanceTests(unittest.TestCase):
    def test_explicit_week_and_date_range_resolve_without_guessing(self):
        self.assertEqual(_explicit_period_request("Show the JHLPAA report for Week 3")[0], 3)
        period, dates, label, year_unspecified = _explicit_period_request("Report for October 12–18, 2026")
        self.assertIsNone(period)
        self.assertFalse(year_unspecified)
        self.assertEqual((dates[0].isoformat(), dates[1].isoformat()), ("2026-10-12", "2026-10-18"))
        self.assertEqual(_match_date_period(SCHEDULE, dates), 3)
        self.assertIsNone(_match_date_period(SCHEDULE, (dates[0], dates[1].replace(day=17))))
        self.assertIn("2026", label)
        _, dates, _, year_unspecified = _explicit_period_request("Report for October 12–18")
        self.assertTrue(year_unspecified)
        self.assertEqual(_match_date_period(SCHEDULE, dates, year_unspecified=year_unspecified), 3)

    def test_missing_period_never_uses_rolling_activity(self):
        activity = summarize_recent_league_activity(
            {"records": [{"transaction_id": "recent", "timestamp": "2026-10-20T12:00:00Z"}]},
            period=None, allow_rolling=False,
        )
        self.assertEqual(activity["transaction_count"], 0)
        self.assertEqual(activity["scope_method"], "unresolved_period")

    def test_trade_story_composes_without_standings(self):
        report = compose_period_report(research={
            "schema": "athena.league_period_research.v2",
            "league_name": "JHLPAA",
            "period": 3,
            "findings": [{
                "kind": "trade", "trade_count": 1,
                "exchanges": [{"received": {"Alpha": ["Player A"]}}],
            }],
            "comparison": None,
            "coverage": {"period_standings": "incomplete",
                         "player_period_production": "unverified_period"},
        })
        self.assertIn("Alpha acquired Player A", report)
        self.assertIn("Individual player production", report)
        self.assertIn("Period standings and movement", report)

    def test_trading_block_change_is_only_between_verified_observations(self):
        before = {
            "status": "complete", "authenticated": True, "league_id": "jhlpaa1",
            "season": 2026, "observed_at": "2026-10-11T18:00:00Z",
            "teams": [{"team_id": "alpha", "block": {"offered": ["Player A"]}}],
        }
        after = {
            "status": "complete", "authenticated": True, "league_id": "jhlpaa1",
            "season": 2026, "observed_at": "2026-10-18T18:00:00Z",
            "teams": [{"team_id": "alpha", "block": {"offered": ["Player B"]}}],
        }
        changes = compare_snapshots(before, after)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["kind"], "block_changed")
        self.assertEqual(changes[0]["time_precision"], "between_observations")

    def test_full_public_route_composes_partial_evidence_for_latest_completed_period(self):
        calendar = {"data": {"scoringPeriods": PERIODS, "rosterPeriods": PERIODS}}
        unified = resolve_unified_period(calendar, today=date(2026, 10, 21))
        self.assertEqual((unified["period"], unified["start"], unified["end"]),
                         (3, "2026-10-12", "2026-10-18"))
        ctx = ScoutContext(
            league_profile={
                "league_id": "jhlpaa1", "season": 2026, "league_name": "JHLPAA",
                "team_count": 2, "sport": "NHL", "keeper_count": 11,
            },
            standings_archive={"league_id": "jhlpaa1", "season": 2026},
            team_profiles=[],
            manager_behavior={},
            league_market={},
            knowledge_readiness={},
            transaction_history={"records": [
                {
                    "transaction_id": "trade-3", "period": 3,
                    "timestamp": "2026-10-14T12:00:00Z",
                    "transaction_type": "trade", "summary": "Alpha acquired Player A",
                    "participants": [{"team_name": "Alpha"}, {"team_name": "Beta"}],
                    "assets": [{"asset_type": "player", "asset_name": "Player A",
                                "movement_context": {"from_team_name": "Beta", "to_team_name": "Alpha"}}],
                },
                {
                    "transaction_id": "trade-4", "period": 4,
                    "timestamp": "2026-10-20T12:00:00Z",
                    "transaction_type": "trade", "summary": "Beta acquired Player B",
                    "participants": [{"team_name": "Beta"}, {"team_name": "Alpha"}],
                    "assets": [],
                },
            ]},
            player_master=[],
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            save_snapshot(output, _snapshot(2, 2, 90, 1, 100))
            save_snapshot(output, _snapshot(3, 1, 150, 2, 110))
            with (
                patch("Core.project_paths.OUTPUT_DIR", output),
                patch("Athena.fantasy_refresh.ensure_fantasy_freshness",
                      return_value={"status": "fresh", "attempted": False}),
                patch("Athena.Investigation.fantrax_period_calendar.acquire_unified_period",
                      return_value=unified),
                patch("Providers.Fantrax.fantrax_client.FantraxClient", _UnauthenticatedFantrax),
                patch("Athena.Investigation.period_evidence_acquisition.acquire_player_period_production",
                      return_value={"status": "unverified_period", "verified": False,
                                    "records": [], "reason": "period not independently confirmed",
                                    "diagnostic": {}}),
            ):
                answer = route_question(QUESTION, ctx=ctx, mode="public")
                dated_answer = route_question(
                    "Produce the JHLPAA weekly league report for October 12–18, 2026.",
                    ctx=ctx, mode="public",
                )

        self.assertEqual(answer["developer"]["athena_request"]["selected_route"], "league_recap")
        self.assertEqual(answer["developer"]["athena_request"]["mode"], "public")
        self.assertEqual(answer["developer"]["period_selection"]["period"], 3)
        self.assertTrue(answer["developer"]["period_selection"]["completion_verified"])
        self.assertEqual(answer["developer"]["player_production_acquisition"]["status"], "unverified_period")
        report = answer["natural_language_response"]
        self.assertIn("Week 3 (October 12-18, 2026)", report)
        self.assertIn("Alpha", report)
        self.assertIn("Player A", report)
        self.assertNotIn("Player B", report)
        self.assertIn("Individual player production: the provider did not confirm the requested season and period", report)
        self.assertEqual(answer["developer"]["period_standings_comparison"]["status"], "compared")
        self.assertEqual(dated_answer["developer"]["period_selection"]["period"], 3)
        self.assertTrue(dated_answer["developer"]["period_selection"]["explicit"])


if __name__ == "__main__":
    unittest.main()
