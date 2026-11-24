"""Phase 3: meaningful verified correspondent prose without source invention."""
from copy import deepcopy
from Athena.Investigation.editorial_briefing import build_editorial_briefing
from Scout.conversation.journalist_composition import compose_editorial_publication, _competitive_story


def _case(rows):
    research = {'schema':'athena.league_period_research.v2','league_name':'JHLPAA',
                'period':7, 'findings':[{'kind':'scoring_leader','team':rows[0]['name'],
                                       'period_points':rows[0]['period_points']}],
                'comparison':{'status':'compared','source':'canonical_period_standings',
                              'period':7,'baseline_period':6,'teams':rows},
                'editorial':{'trades':[],'trade_count':0},
                'period_scoring_audit':{'status':'partial', 'reconciled_teams':2,'team_count':len(rows)}}
    research['editorial_briefing'] = build_editorial_briefing(research)
    return research


def test_scoring_winner_not_overall_leader_is_meaningful_story():
    rows = [dict(team_id='1',name='Southside',rank=3,points=123,rank_change=1,period_points=42),
            dict(team_id='2',name='Waterbury',rank=1,points=150,rank_change=0,period_points=29),
            dict(team_id='3',name='Alien',rank=2,points=135,rank_change=-1,period_points=30),
            dict(team_id='4',name='Bobby Orr',rank=4,points=110,rank_change=0,period_points=20)]
    item = _case(rows); before = deepcopy(item)
    report = compose_editorial_publication(research=item)
    assert report['status']=='pass'
    text = report['report']
    assert 'Beyond the scores' in text
    assert "scoring crown belongs to Southside (42 points)" in text
    assert 'overall lead still belongs to Waterbury' in text
    assert 'Nobody gets to coast' in text
    assert 'These NHL totals reconcile with the team scoring snapshots' not in text
    assert item == before


def test_high_scoring_team_can_slip_without_explaining_motives():
    rows = [dict(team_id='1',name='Leader',rank=1,points=150,rank_change=0,period_points=35),
            dict(team_id='2',name='High Scorer',rank=3,points=110,rank_change=-1,period_points=34),
            dict(team_id='3',name='Riser',rank=2,points=115,rank_change=1,period_points=30),
            dict(team_id='4',name='Last',rank=4,points=80,rank_change=0,period_points=10)]
    item = _case(rows)
    text = compose_editorial_publication(research=item)['report']
    assert 'High Scorer delivered 34 points and still slipped 1 place' in text
    assert 'Beyond the scores' in text
    assert 'lazy' not in text.lower()


def test_no_story_invented_when_briefing_unverified():
    rows = [dict(team_id='1',name='A',rank=1,points=100,rank_change=0,period_points=30)]
    case = _case(rows)
    case['comparison']['status'] = 'unverified'
    case['editorial_briefing'] = build_editorial_briefing(case)
    assert case['editorial_briefing']['status']=='unavailable'
    assert _competitive_story(case['editorial_briefing']) is None
    report=compose_editorial_publication(research=case)['report']
    assert 'Beyond the scores' not in report


def test_one_team_and_ties_are_not_forced_into_false_rivalry():
    rows = [dict(team_id='1',name='A',rank=1,points=100,rank_change=0,period_points=30)]
    item=_case(rows)
    assert item['editorial_briefing']['narrative_signals']==[]
    assert 'Beyond the scores' not in compose_editorial_publication(research=item)['report']
