"""v63: live-request metadata, qualified profiles, and fantasy/pro evidence boundaries."""
from Athena.intent_resolution import select_executable_route
from Scout.conversation.router import route_question


def test_qualified_player_identity_uses_same_profile_surface(monkeypatch):
    monkeypatch.setenv('ATHENA_NHL_PLAYER_NETWORK', '0')
    for prompt, position in [('Sebastian Aho Carolina Hurricanes center', 'C'),
                             ('Sebastian Aho Swedish defenseman', 'D')]:
        assert select_executable_route(prompt, 'public')[0] == 'public_player_identity'
        answer = route_question(prompt, mode='public')
        assert answer['intent'] == 'public_player_profile'
        assert answer['player']['position'] == position
        assert answer['developer']['public_player_profile']['entity_id']
    assert route_question('Sebastian Aho', mode='public')['intent'] == 'public_entity_disambiguation'


def test_deep_scouting_has_more_than_bare_profile(monkeypatch):
    monkeypatch.setenv('ATHENA_NHL_PLAYER_NETWORK', '0')
    short = route_question('Alex Ovechkin', mode='public')
    full = route_question('Give me a complete scouting profile of Alex Ovechkin.', mode='public')
    assert full['intent'] == short['intent'] == 'public_player_profile'
    assert len(full['public_comment']) > len(short['public_comment'])
    assert 'Scouting read (curated' in full['public_comment']
    assert 'Remaining scouting uncertainty' in full['public_comment']
    assert full['player']['full_name'] == short['player']['full_name']


def test_current_season_stays_investigation_and_league_comparison_is_not_public():
    assert select_executable_route('How is Mitch Marner playing this season?', 'public')[0] == 'public_player_investigation'
    assert select_executable_route('Compare Auston Matthews vs Connor McDavid for JHLPAA keeper scoring', 'public')[0] == 'league_player_comparison'


def test_runtime_provenance_is_live_and_tied_to_each_turn(tmp_path, monkeypatch):
    from Scout import app
    provenance = app._runtime_provenance()
    from Core.version import SCOUT_VERSION
    assert provenance['scout_version'] == SCOUT_VERSION
    assert provenance['process_id'] > 0
    assert provenance['project_root']
    monkeypatch.setattr(app, 'SESSION_JOURNAL', tmp_path / 'turns.jsonl')
    monkeypatch.setattr(app, 'SESSION_TRANSCRIPT', [])
    answer = {'intent': 'test', 'title': 'Test', 'engine_conclusion': 'Test only'}
    app._record_session_turn('version?', 'public', answer)
    turns = app._journal_turns()
    assert turns[0]['runtime_provenance']['scout_version'] == SCOUT_VERSION
    assert turns[0]['runtime_provenance']['session_instance'] == provenance['session_instance']


def test_league_bridge_never_promotes_nhl_stats_to_fantasy_credit(monkeypatch):
    monkeypatch.setenv('ATHENA_NHL_PLAYER_NETWORK', '0')
    from Athena.capability_handlers import _answer_league_player_comparison
    from Scout.conversation.context import load_context
    result = _answer_league_player_comparison(load_context(), 'Compare Auston Matthews and Connor McDavid for JHLPAA keeper scoring')
    bridge = result['developer']['cross_domain_evidence_bridge']
    assert bridge['fantasy_credit'].startswith('unverified')
    assert {x['name'] for x in bridge['subjects']} == {'Auston Matthews', 'Connor McDavid'}
