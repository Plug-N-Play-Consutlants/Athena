"""Cross-layer, user-visible presentation regression contract."""
from Scout.conversation.composition import compose_answer_payload
from Scout.app import _session_continuation, SESSION_TRANSCRIPT, SESSION_LOCK
from Core.version import ATHENA_VERSION, SCOUT_VERSION, RELEASE_PATCH


def payload(intent, mode, title, text, suggestions=None):
    return compose_answer_payload({
        'intent': intent, 'title': title, 'natural_language_response': text,
        'known_limitations': ['Schedule not yet verified'],
        'suggested_prompts': suggestions or [],
        'developer': {'athena_request': {'mode': mode, 'selected_route': intent}},
    })


p = payload('public_nhl_player_contract', 'public', 'Toronto contract options',
            'Toronto has cap constraints. JHLPAA is mentioned as quoted background.',
            ['Which JHLPAA findings can we verify further?', 'Show Toronto cap implications'])
assert p['presentation_domain'] == 'public'
assert all('JHLPAA' not in x and 'Fantrax' not in x for x in p['suggested_prompts'])
assert all('JHLPAA' not in x['prompt'] for x in p['continuation_options'])
assert 'Toronto has cap constraints' in p['public_comment']

f = payload('league_period_timing', 'fantasy', 'JHLPAA lock', 'Toronto is mentioned in the roster evidence.',
            ['Which JHLPAA game sets the lock?'])
assert f['presentation_domain'] == 'fantasy'
assert any('JHLPAA' in x for x in f['suggested_prompts'])
assert all('Toronto' not in x['prompt'] for x in f['continuation_options'])

with SESSION_LOCK:
    original = list(SESSION_TRANSCRIPT)
    SESSION_TRANSCRIPT[:] = [{
        'mode': 'public', 'answer': {'continuation': {
            'origin_intent': 'public_nhl_decision_inquiry', 'subject': 'Toronto Maple Leafs'}}}]
try:
    hint = _session_continuation('What if I include our next first-round pick?', 'public')
    assert hint and hint['subject'] == 'Toronto Maple Leafs'
    assert _session_continuation('What about the JHLPAA trading block?', 'public') is None
    assert _session_continuation('What about the Edmonton Oilers?', 'public') is None
    assert _session_continuation('What if I include a first-round pick?', 'fantasy') is None
finally:
    with SESSION_LOCK:
        SESSION_TRANSCRIPT[:] = original

assert ATHENA_VERSION == SCOUT_VERSION.removeprefix('v')
assert ATHENA_VERSION.split('.')[3] == RELEASE_PATCH
print('PASS conversation domain, suggestions, continuity isolation, version metadata')
