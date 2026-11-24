"""Phase 2: the full, verified standings evidence reaches Scout publication."""
from pathlib import Path
from Athena.Investigation.editorial_briefing import build_editorial_briefing
from Athena.Investigation.editorial_storylines import investigate_storyline_continuity
from Athena.Investigation.standings_archive import save_snapshot
from Scout.conversation.journalist_composition import compose_editorial_publication


def research():
    names = ['Southside', 'Waterbury', 'Grabner', 'Alien Agenda', 'Bobby Orr',
             'No Regretzkys', 'Protect Hronek', 'Reapers']
    scores = [42, 40, 34, 29, 19, 28, 25, 17]
    movement = [0, 0, 1, 2, -2, 0, 1, -2]
    rows = [dict(team_id=str(i), name=name, rank=i + 1, points=200-i*10,
                 rank_change=movement[i], period_points=scores[i])
            for i, name in enumerate(names)]
    return {'schema':'athena.league_period_research.v2', 'league_name':'JHLPAA',
            'period':7, 'findings':[{'kind':'scoring_leader', 'team':'Southside',
                                   'period_points':42, 'rank':1, 'top_score':True}],
            'comparison':{'status':'compared','source':'canonical_period_standings',
                          'period':7,'baseline_period':6,'teams':rows},
            'editorial':{'trades':[], 'trade_count':0},
            'period_scoring_audit':{'status':'partial','reconciled_teams':2,'team_count':14}}


def test_briefing_includes_all_movers_and_weekly_scoring_contrasts():
    item = research()
    briefing = build_editorial_briefing(item)
    assert briefing['status'] == 'verified'
    assert len(briefing['climbers']) == 3
    assert len(briefing['fallers']) == 2
    item['editorial_briefing'] = briefing
    result = compose_editorial_publication(research=item)
    assert result['status'] == 'pass'
    report = result['report']
    for name in ['Grabner', 'Alien Agenda', 'Bobby Orr', 'Protect Hronek', 'Reapers']:
        assert name in report
    assert 'The competitive picture' in report
    assert '14/14 teams reconciled' not in report
    assert 'The transaction wire' not in report


def test_briefing_fails_closed_when_comparison_incomplete():
    item = research()
    item['comparison']['teams'][0]['period_points'] = None
    assert build_editorial_briefing(item)['status'] == 'unavailable'
    item = research()
    item['comparison']['source'] = 'unverified_source'
    assert build_editorial_briefing(item)['status'] == 'unavailable'


def test_reversal_is_recognized_without_claiming_a_streak(tmp_path: Path):
    # Alpha climbs from 3 to 1, then returns to 2; the direction changes.
    for week, ranks in [(5,[3,1,2]), (6,[1,2,3]), (7,[2,1,3])]:
        save_snapshot(tmp_path, dict(league_id='league1',season=2026,period=week,
                                   source='verified_test', timeframe='FROM_SEASON_START',complete=True,
                                   teams=[dict(team_id=str(i),name=name,rank=ranks[i],points=10*(4-ranks[i])+week)
                                          for i,name in enumerate(['Alpha','Beta','Gamma'])]))
    signals = investigate_storyline_continuity(tmp_path,'league1',2026,7)
    assert any(x['team_name']=='Alpha' and x['direction']=='reversal'
               and x['movements']==[2,-1] for x in signals['signals'])
    item = research()
    item['storyline_continuity'] = signals
    item['editorial_briefing'] = build_editorial_briefing(item)
    report = compose_editorial_publication(research=item)['report']
    assert 'then gave back ground by 1' in report
    assert 'two consecutive periods' not in report


def test_briefing_does_not_mutate_source_data():
    item = research()
    before = repr(item)
    build_editorial_briefing(item)
    assert repr(item) == before
