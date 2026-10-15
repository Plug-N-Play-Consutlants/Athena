from pathlib import Path
from tempfile import TemporaryDirectory
from Athena.Investigation.standings_archive import save_snapshot, compare_archived, validate_snapshot

def sample(p,pts,ranks):
    return {'league_id':'jhlpaa123','season':2026,'period':p,'source':'fantrax',
            'timeframe':'FROM_SEASON_START','complete':True,
            'teams':[{'team_id':str(i),'name':f'Team {i}','rank':ranks[i], 'points':pts[i]} for i in range(2)]}

with TemporaryDirectory() as temp:
    root=Path(temp)
    first=sample(1,[43,38],[1,2]);second=sample(2,[50,55],[2,1])
    save_snapshot(root,first);save_snapshot(root,second)
    result=compare_archived(root,'jhlpaa123',2026,2)
    assert result['status']=='compared',result
    assert result['teams'][0]['rank_change']==-1
    assert result['teams'][1]['period_points']==17
    result=compare_archived(root,'jhlpaa123',2026,3)
    assert result['status']=='missing_requested_period'
    second['teams'][0]['points']=51
    save_snapshot(root,second)
    assert list((root/'Standings/jhlpaa123/2026/revisions').glob('*.json'))
    bad=sample(3,[1,2],[1,1])
    try: validate_snapshot(bad)
    except ValueError: pass
    else: raise AssertionError('duplicate rank accepted')
print('Standings archive regression PASS')
