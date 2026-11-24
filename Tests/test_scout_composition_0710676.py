"""Scout editorial acceptance: single lead, contrast and causality guardrails."""
import json
import zipfile
from pathlib import Path

from Athena.Investigation.competitive_race import analyze_race
from Athena.Investigation.storyline_synthesis import synthesize_storylines
from Scout.conversation.multi_period_publication import publish_multi_period


def fixture():
    # Sufficient sample to reproduce the real three-week situation, including
    # competing challengers and two struggling teams. Source-independent test.
    records = [
        ('Leeeroy Jenkins', [80,121,174,207], [1,1,1]),
        ('Bubba’s Bruisers', [52,100,168,196], [3,2,2]),
        ('Grabner By the Jussi', [50,83,139,173], [2,3,2]),
        ('Reapers', [72,95,116,139], [8,10,13]),
        ('Mighty Fucks', [76,95,119,142], [9,11,14]),
    ]
    # This fixture intentionally uses consistent per-team cumulative score
    # differences for prose tests, not synthetic rank validity claims.
    teams=[]
    for i,(name,points,ranks) in enumerate(records):
        weekly={5:points[1]-points[0],6:points[2]-points[1],7:points[3]-points[2]}
        teams.append(dict(team_id=str(i),name=name,ranks=ranks,cumulative_points=points[1:],
                          rank_change=ranks[0]-ranks[-1],weekly_points=weekly,
                          window_points=sum(weekly.values())))
    baseline={'teams':[{'team_id':str(i),'points':record[1][0]} for i,record in enumerate(records)]}
    race=analyze_race(teams,[5,6,7],baseline=baseline)
    return teams,race


def article():
    teams,race=fixture()
    trades=[{'week':5,'count':2,'events':[
        {'id':'a','type':'trade','received':{'Bubba’s Bruisers':['Adam Fox'],'Reapers':["K’Andre Miller"]},
         'participants':['Bubba’s Bruisers','Reapers']},
        {'id':'b','type':'trade','received':{'Bubba’s Bruisers':['Miro Heiskanen'],'Bobby Orr':['Luke Hughes']},
         'participants':['Bubba’s Bruisers','Bobby Orr']}]},
        {'week':6,'count':0,'events':[]}, {'week':7,'count':0,'events':[]}]
    synthesis=synthesize_storylines({'status':'verified','teams':teams,'race':race,'transactions':trades})
    return publish_multi_period({'status':'verified','teams_analyzed':5,'periods':[5,6,7],
        'stories':[{'kind':'scoring_pace','team':'Bubba’s Bruisers','points':144,
                    'scope':'full_window','weekly_points':{5:48,6:68,7:28}}],
        'race':race,'transactions':trades,'synthesis':synthesis})


def test_main_finding_not_repeated_in_three_sections():
    text=article()
    assert text.count('144 points') <= 1
    assert text.count('has closed') <= 1
    assert text.count('The race for first') == 1
    assert 'The developing picture' not in text
    assert 'trade(s)' not in text


def test_reader_gets_scoring_detail_contrast_and_actionable_watch():
    text=article()
    assert 'Week 5: 48, Week 6: 68, Week 7: 28' in text
    assert 'By contrast' in text
    assert 'What to watch' in text
    assert 'the next scoring period' in text


def test_verified_asset_directions_and_no_attributed_effect():
    text=article()
    assert 'Bubba’s Bruisers received Adam Fox' in text
    assert 'Reapers received K’Andre Miller' in text
    assert 'not what caused the change' in text
    assert 'trade(s)' not in text


def test_partial_window_qualifies_scope_and_unverified_is_safe():
    teams,race=fixture()
    partial=publish_multi_period({'status':'verified','periods':[5,6,7],
        'race':analyze_race(teams,[5,6,7]),
        'stories':[{'kind':'scoring_pace','team':'Bubba’s Bruisers','points':96,
                    'scope':'after_initial_snapshot','weekly_points':{6:68,7:28}}]})
    assert 'Week 5 production remains unverified' in partial
    assert 'not a full-window total' in partial
    assert 'not from the start of Week 5' in partial
    assert 'No comparative performance conclusion' in publish_multi_period({'status':'unavailable','periods':[5,6,7]})
