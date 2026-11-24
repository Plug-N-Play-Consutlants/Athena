"""Week 5 end-to-end publication fixture grounded in historical Scout export."""
from Athena.Investigation.editorial_newsroom import rank_stories, transaction_inventory
from Scout.conversation.journalist_composition import compose_journalist_report, audit_publication


def fixture():
    trades = [
        {'transaction_id':'t1', 'received': {'Leeeroy Jenkins':['Mika Zibanejad'], 'Protect Hronek':['Shane Wright']}},
        {'transaction_id':'t2', 'received': {'Leeeroy Jenkins':['Alexis Lafreniere'], 'Mighty Fucks':['Danila Yurov']}},
        {'transaction_id':'t3', 'received': {'Bubba’s Bruisers':['Miro Heiskanen'], 'Bobby Orr':['Luke Hughes']}},
        {'transaction_id':'t4', 'received': {'Bubba’s Bruisers':['Adam Fox'], 'Reapers':["K'Andre Miller"]}},
    ]
    return {'schema':'athena.league_period_research.v2','period':5,'league_name':'JHLPAA',
        'period_calendar':{'start':'2026-10-26','end':'2026-11-02'},
        'findings':[
            {'kind':'trade_cluster','team':'Leeeroy Jenkins','trade_count':2,
             'exchanges':[{'received': t['received']} for t in trades[:2]]},
            {'kind':'surge','team':'Bubba’s Bruisers','period_points':48,'top_score':True,'rank_change':0,'rank':3},
            {'kind':'surge','team':'The Artist Formerly Known As Kyle Dubas','period_points':46,'rank_change':3,'rank':8},
            {'kind':'scoring_leader','team':'Waterbury Wolverines','period_points':44},
            {'kind':'slide','team':'Protect Hronek','period_points':22,'rank_change':-2,'rank':9},
            {'kind':'secondary_market','transaction_count':7,'examples':['Urban Achievers added Michael Brandsegg-Nygard']},
        ],
        'editorial':{'trade_count':4,'trades':trades},
        'storyline_continuity':{'status':'verified','source':'canonical_period_standings','signals':[
          {'team_name':'The Artist Formerly Known As Kyle Dubas','direction':'climb','periods':[3,4,5],'overall_rank_change':6},
          {'team_name':'Protect Hronek','direction':'slide','periods':[3,4,5],'overall_rank_change':-4}]},
        'editorial_trade_continuity':{'status':'verified','signals':[{'team':'Bubba’s Bruisers','periods':[4,5],'total_trades':5}]},
        'editorial_player_attribution':{'status':'reconciled_snapshot','period':5,'records':[
          {'player_name':'Leo Carlsson','fantasy_team':'Bubba’s Bruisers','points':8,'credited_points_verified':False,'attribution_kind':'historical_active_snapshot_numeric_reconciliation'}]},
        'comparison':{'status':'compared','teams':[]}}


def test_week5_fully_covered_no_repeat_and_cross_month_date():
    data = fixture(); report = compose_journalist_report(research=data)
    assert 'October 26–November 2, 2026' in report
    assert 'The league recorded 4 confirmed trades' in report
    for player in ['Mika Zibanejad','Shane Wright','Alexis Lafreniere','Danila Yurov','Miro Heiskanen','Luke Hughes','Adam Fox',"K'Andre Miller"]:
        assert report.count(player) == 1, player
    assert report.count('The transaction wire') == 1
    assert '5 trades across Weeks 4–5' in report
    assert 'Leo Carlsson (8 G+A)' in report
    assert 'Reporting limits' not in report
    assert audit_publication(data, report)['status'] == 'pass'


def test_selection_not_forced_to_most_trades():
    stories = rank_stories(fixture())
    assert stories[0]['finding']['team'] != 'Leeeroy Jenkins'


def test_publication_gate_catches_missing_trade_assets_and_wrong_totals():
    data=fixture()
    report=compose_journalist_report(research=data)
    assert audit_publication(data,report)['status']=='pass'
    assert 'omitted_trade_asset:Adam Fox' in audit_publication(data,report.replace('Adam Fox','unknown'))['issues']
    data['editorial']['trade_count']=5
    assert 'trade_inventory_count_mismatch' in audit_publication(data,report)['issues']


def test_no_double_counting_when_only_overlapping_findings():
    data=fixture();data.pop('editorial')
    data['findings'].append({'kind':'trade_cluster','team':'Protect Hronek','trade_count':1,
                            'exchanges':[{'received': {'Leeeroy Jenkins':['Mika Zibanejad'], 'Protect Hronek':['Shane Wright']}}]})
    assert transaction_inventory(data)['count']==2
