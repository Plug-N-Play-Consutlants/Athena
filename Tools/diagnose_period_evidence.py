"""Inspect historical scoring evidence and optionally ask the authenticated sync pipeline to refresh.

Read-only by default. --refresh explicitly invokes the existing provider acquisition
and preserves its calendar/authentication checks; never substitutes a current roster.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Athena.workspace import get_workspace_value
from Core.project_paths import OUTPUT_DIR
from Athena.Investigation.period_evidence_diagnostics import diagnose_period_evidence


def run(*, league=None, season=None, periods=None, refresh=False, output_dir=None):
    league = str(league or get_workspace_value('league_id') or '')
    season = str(season or get_workspace_value('season') or '')
    periods = list(periods or [6,7,8])
    if not league.isalnum() or not season.isdigit() or not periods or len(periods)>8 or any(type(p) is not int or p<2 for p in periods):
        raise ValueError('Specify valid league, season and 2–8 completed-period identities')
    root = Path(output_dir or OUTPUT_DIR)
    before = diagnose_period_evidence(root, league, season, periods)
    output = {'before':before,'refresh_attempted':bool(refresh)}
    if refresh:
        from Athena.Investigation.sync_period_scoring_audit import run as audit
        result=audit(league_id=league,season=season,requested_periods=periods,output_dir=root)
        output['acquisition_manifest']=result
        output['after']=diagnose_period_evidence(root, league, season, periods)
    return output


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--league',help='Fantrax league ID (defaults to configured workspace)')
    parser.add_argument('--season',help='Fantrax season (defaults to configured workspace)')
    parser.add_argument('--periods',nargs='+',type=int,default=[6,7,8])
    parser.add_argument('--refresh',action='store_true',help='Attempt authenticated acquisition for completed periods')
    args=parser.parse_args()
    print(json.dumps(run(league=args.league,season=args.season,periods=args.periods,refresh=args.refresh),indent=2,ensure_ascii=False))
