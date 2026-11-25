from types import SimpleNamespace
from Athena.entry_policy import select_entry_route
from Athena.Investigation.standings_archive import save_snapshot
from Athena.Investigation.league_team_performance import investigate_team_performance, _resolve_named_team

QUESTION = "Analyze Bubba's Bruisers' performance in JHLPAA scoring period 8. Which rostered players drove the team's results, which players underperformed, and how much did each contribute? Use verified scoring evidence and clearly identify anything that cannot yet be established."

def test_real_world_public_route():
    assert select_entry_route(QUESTION,'public').route == 'league_team_period_performance'

def test_calendar_remains_calendar():
    assert select_entry_route('What was the most recently completed JHLPAA scoring period? Give me its exact dates.','public').route == 'league_scoring_period_boundary'
    assert select_entry_route('When did JHLPAA scoring period 8 end?','public').route == 'league_scoring_period_boundary'

def test_editorial_remains_editorial():
    q = 'Write a JHLPAA scoring period 8 editorial. Cover standings, trades, performances, quiet teams, and top players.'
    assert select_entry_route(q, 'public').route == 'league_recap'

def test_player_leader_remains_leader():
    q='Which players contributed the most fantasy points to the JHLPAA in scoring period 8?'
    assert select_entry_route(q,'public').route=='league_player_period_leaders'

def _snap(p, scores):
    return {'league_id':'abc123','season':2026,'period':p,'source':'fixture', 'timeframe':'FROM_SEASON_START','complete':True,
            'teams':[{'team_id':'a','name':"Bubba’s Bruisers",'rank':2,'points':scores[0]},
                     {'team_id':'b','name':'Leeeroy Jenkins','rank':1,'points':scores[1]}]}

def _ctx():
    return SimpleNamespace(league_profile={'league_id':'abc123','season':2026,'team_count':2}, standings_archive={}, files_loaded=[])

def test_verified_standings_partial_answer(tmp_path):
    save_snapshot(tmp_path,_snap(7,[100,115]));save_snapshot(tmp_path,_snap(8,[154,166]))
    result=investigate_team_performance(_ctx(),QUESTION,output=tmp_path)
    assert result['intent']=='league_team_period_performance'
    answer=result['engine_conclusion']
    assert '54' in answer and 'rank 2' in answer and '12 points' in answer
    assert 'Individual contributors' in answer
    assert result['team_period_investigation']['ledger_written'] is False

def test_no_inferred_period_points_without_baseline(tmp_path):
    save_snapshot(tmp_path,_snap(8,[154,166]))
    result=investigate_team_performance(_ctx(),QUESTION,output=tmp_path)
    assert 'Points earned during the period' not in result['engine_conclusion']
    assert 'Prior-period standings missing' in str(result['known_limitations'])

def test_no_unrelated_team_substitution():
    assert _resolve_named_team('Analyze JHLPAA scoring period 8', [{'name':'Bubba’s Bruisers'}]) is None
