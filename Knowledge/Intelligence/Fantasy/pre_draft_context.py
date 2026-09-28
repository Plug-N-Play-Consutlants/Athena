"""Current pre-draft context assembled from reusable league evidence.

This module describes the state that exists before a draft. It does not predict
selections and does not treat configured draft slots as exercised selections.
"""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path
from typing import Any
from Core.text_utils import normalize_external_text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INTELLIGENCE_VERSION = "0.6.5.0.4"

def _json(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError): return None

def build_pre_draft_context(*, project_root: Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else PROJECT_ROOT
    profile = _json(root/'Output/league_profile.json') or {}
    draft = _json(root/'Output/draft_picks.json') or {}
    pool = _json(root/'Output/player_pool_master.json') or {}
    picks = ((draft.get('current_draft') or {}).get('picks') or [])
    owners = Counter(str(((p.get('current_owner') or {}).get('team_name')) or 'unresolved') for p in picks if isinstance(p,dict))
    rostered = [r for r in (pool.get('records') or []) if isinstance(r,dict) and r.get('availability_status') == 'rostered']
    roster_teams = Counter(normalize_external_text(r.get('fantasy_team') or 'unresolved') for r in rostered)
    positions = Counter(str(r.get('position') or 'unresolved') for r in rostered)
    # Availability evidence has two distinct semantics. Canonical live player-pool
    # records may support current availability. The imported Fantrax CSV is only
    # a broad snapshot and must never be promoted into a live best-available list.
    live_available = [r for r in (pool.get('records') or []) if isinstance(r, dict) and r.get('availability_status') in {'free_agent','waivers'}]
    live_positions = Counter(str(r.get('position') or 'unresolved') for r in live_available)
    snapshot_fa_rows = 0
    csv_path=root/'Raw/Fantrax-Players-JHLPAA.csv'
    if csv_path.exists():
        try:
            with csv_path.open(encoding='utf-8-sig', errors='replace', newline='') as fh:
                for row in csv.DictReader(fh):
                    if str(row.get('Status') or '').strip().upper() == 'FA':
                        snapshot_fa_rows += 1
        except OSError:
            snapshot_fa_rows = 0
    retained_total = sum(positions.values())
    retention_pressure = {pos: {'retained': count, 'retained_share': round(count / retained_total, 4) if retained_total else 0.0, 'live_available': live_positions.get(pos, 0), 'retained_to_live_available': round(count / live_positions[pos], 3) if live_positions.get(pos) else None} for pos, count in sorted(positions.items())}
    historical={}
    try:
        from Knowledge.Intelligence.Fantasy.historical_draft import build_historical_draft_intelligence
        historical=build_historical_draft_intelligence(project_root=root)
    except Exception: historical={}
    keeper_target=int(profile.get('keeper_count') or 0)
    team_count=int(profile.get('team_count') or 0)
    expected_keepers=keeper_target*team_count
    return {
      'schema':'athena.pre_draft_context.v1','version':INTELLIGENCE_VERSION,
      'status':'available' if picks and rostered else 'partial','season':profile.get('season'),
      'league':{'team_count':team_count,'keeper_count':keeper_target,'scoring_model':profile.get('scoring_model'),'league_subtype':profile.get('league_subtype')},
      'keeper_state':{'rostered_players':len(rostered),'expected_keeper_slots':expected_keepers,'matches_expected_keeper_state':bool(expected_keepers and len(rostered)==expected_keepers),'keeper_selection_established':False,'teams_observed':len(roster_teams),'rostered_by_team':dict(sorted(roster_teams.items())),'position_eligibility':dict(sorted(positions.items()))},
      'draft_capital':{'configured_slots':len(picks),'configured_rounds':(draft.get('current_draft') or {}).get('round_count'),'selection_count_status':(draft.get('current_draft') or {}).get('selection_count_status'),'teams_observed':len(owners),'configured_slots_by_current_owner':dict(sorted(owners.items())),'min_owned_slots':min(owners.values()) if owners else None,'max_owned_slots':max(owners.values()) if owners else None},
      'available_pool':{'authoritative_source':'Output/player_pool_master.json','live_availability_observed':bool(live_available),'live_available_records':len(live_available),'live_available_by_position':dict(sorted(live_positions.items())),'snapshot_source':'Raw/Fantrax-Players-JHLPAA.csv' if csv_path.exists() else None,'snapshot_fa_rows':snapshot_fa_rows,'snapshot_semantics':'Imported FA rows are contextual snapshot evidence only. They are not a live availability guarantee and are not ranked or promoted as current draft-pool candidates.','status_semantics':'Imported FA rows are contextual snapshot evidence only and must not be represented as a live availability guarantee.','retention_pressure':retention_pressure},
      'historical_context':{'status':historical.get('status'),'season_count':historical.get('season_count'),'coverage':historical.get('coverage'),'findings':historical.get('findings',[])},
      'files_read':['Output/league_profile.json','Output/draft_picks.json','Output/player_pool_master.json']+(['Raw/Fantrax-Players-JHLPAA.csv'] if csv_path.exists() else [])+list(historical.get('files_read') or []),
      'limitations':['Configured draft slots describe current board ownership/capacity, not selections that will be exercised.','The current roster snapshot does not identify the final keeper selections.' if len(rostered)!=expected_keepers else 'Matching the keeper allotment by count does not independently prove final keeper identities.','Imported Fantrax FA rows are contextual snapshot evidence only; current availability requires canonical live player-pool evidence.','Pre-draft context describes current evidence; it does not predict which players or positions managers will select.','Manager and cross-season franchise tendencies remain unavailable until identity continuity is established.']
    }
