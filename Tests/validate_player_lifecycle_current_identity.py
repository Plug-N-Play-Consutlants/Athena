from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Intelligence.Public.player_lifecycle import resolve_player_lifecycle
from Scout.conversation.context import load_context
from Scout.conversation.router import route_question


def check(name, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return bool(condition)


def current_news(*args, **kwargs):
    return [
        {"title":"Maple Leafs season preview: Bobrovsky, McKenna among new faces", "summary":"Gavin McKenna joins the Toronto Maple Leafs roster after being selected 1st overall.", "published_at":"2026-09-26T12:00:00Z", "url":"https://example.test/nhl", "source_display_name":"NHL.com"},
        {"title":"Gavin McKenna impresses at camp and prepares for opening night with Maple Leafs", "summary":"Toronto Maple Leafs rookie Gavin McKenna impressed at camp and prepares for opening night after earning a roster spot.", "published_at":"2026-09-25T12:00:00Z", "url":"https://example.test/news", "source_display_name":"Sportsnet"},
    ]


def main():
    ok=[]
    ok.append(check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1), ATHENA_VERSION))
    ok.append(check('release', bool(RELEASE_NAME), RELEASE_NAME))
    with patch('Knowledge.Intelligence.Public.player_lifecycle.discover_current_news', side_effect=current_news):
        life=resolve_player_lifecycle('Gavin McKenna', allow_network=True)
        ok.append(check('current_team_supersedes_old_na', life.get('team')=='TOR', str(life.get('team'))))
        ok.append(check('current_lifecycle', life.get('lifecycle_state')=='nhl_roster_player', str(life.get('lifecycle_state'))))
        ok.append(check('draft_context', life.get('draft')=='1st overall', str(life.get('draft'))))
        ok.append(check('historical_evidence_retained', any(e.get('source')=='fantrax_player_export' for e in life.get('evidence',[]))))
        with patch('Knowledge.Intelligence.Public.player_lifecycle.os.getenv', return_value='1'):
            ans=route_question('Gavin McKenna', load_context(), mode='public')
        ok.append(check('bare_player_profile_route', ans.get('intent')=='public_player_profile', str(ans.get('intent'))))
        ok.append(check('bare_player_not_draft_gap', ans.get('title')!='Draft outlook needs verified evidence', str(ans.get('title'))))
        ok.append(check('adaptive_team_context', 'TOR' in str(ans.get('title')) or 'TOR' in str(ans.get('natural_language_response'))))
        ok.append(check('lifecycle_diagnostics', 'player_lifecycle' in (ans.get('developer') or {})))
        experience = next((s for s in ((ans.get('athena_response') or {}).get('ui_sections') or []) if s.get('section_type')=='player_experience'), {})
        analysis = next((t for t in (experience.get('children') or []) if t.get('title')=='Analysis'), {})
        sections = {s.get('title'): s.get('summary') for s in (analysis.get('children') or [])}
        ok.append(check('early_career_current_assessment', 'camp' in str(sections.get('Current Season','')).lower() and 'nhl roster' in str(sections.get('Current Season','')).lower(), str(sections.get('Current Season'))))
        ok.append(check('developmental_trajectory', 'developmental' in str(sections.get('Career Trend','')).lower(), str(sections.get('Career Trend'))))
        ok.append(check('player_investigate_further', len(ans.get('suggested_prompts') or []) >= 2 and any('camp' in p.lower() or 'transition' in p.lower() for p in (ans.get('suggested_prompts') or [])), str(ans.get('suggested_prompts'))))
        ok.append(check('lifecycle_badge_not_pending', 'NHL Roster Player' in str((experience.get('data') or {}).get('identity',{}).get('assessment_badges')), str((experience.get('data') or {}).get('identity',{}).get('assessment_badges'))))
        ok.append(check('playing_style_not_transition_duplicate', sections.get('Playing Style','') != sections.get('Current Season',''), str(sections.get('Playing Style'))))
    matthews=route_question('Auston Matthews', load_context(), mode='public')
    ok.append(check('professional_player_evidence_or_bounded_gap', matthews.get('intent')=='public_player_profile' and 'Auston Matthews' in str(matthews.get('title')) and (bool(matthews.get('professional_assessment')) or 'Assessment Pending' in str(matthews.get('assessment_badges'))), str(matthews.get('title'))))
    ok.append(check('seeded_player_followups', len(matthews.get('suggested_prompts') or []) >= 2, str(matthews.get('suggested_prompts'))))
    ok.append(check('established_player_no_initial_role_prompt', not any('initial NHL role' in p for p in (matthews.get('suggested_prompts') or [])), str(matthews.get('suggested_prompts'))))
    raise SystemExit(0 if all(ok) else 1)

if __name__=='__main__': main()
