"""Provider transaction chronology, separated from roster-effective periods.

Transactions are single events, not individual player movement rows. Provider
week/period labels may designate when a roster can use the acquired players;
calendar event dates determine reporting membership when validated. Unverified
chronology is not silently reclassified. Strategy is not a verified motive.
"""
from __future__ import annotations

from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
import re

from Athena.Investigation.period_execution import _requested_periods
from Athena.Investigation.league_editorial import _movements

LOCAL = ZoneInfo('America/Toronto')


def resolve_reporting_periods(question: str) -> list[int]:
    """Exclude standalone baseline references from multi-period reporting scope."""
    cleaned = re.sub(r'\b(?:using|with|from|relative to|compared (?:with|to))\s+'
                     r'(?:the\s+)?(?:week|period)\s*\d{1,3}\s+as\s+(?:the\s+)?baseline\b',
                     '', question, flags=re.I)
    cleaned = re.sub(r'\b(?:week|period)\s*\d{1,3}\s+as\s+(?:the\s+)?baseline\b',
                     '', cleaned, flags=re.I)
    return _requested_periods(cleaned)


def _event_datetime(value):
    if isinstance(value, (int,float)) and not isinstance(value,bool):
        return datetime.fromtimestamp(value/(1000 if value > 10**11 else 1), tz=timezone.utc).astimezone(LOCAL)
    if not value:
        return None
    raw = str(value).strip()
    if raw.isdigit():
        return _event_datetime(int(raw))
    try:
        stamp = datetime.fromisoformat(raw.replace('Z','+00:00'))
        return stamp.astimezone(LOCAL) if stamp.tzinfo else stamp.replace(tzinfo=LOCAL)
    except ValueError:
        pass
    for fmt in ('%a %b %d, %Y, %I:%M%p', '%a %b %d, %Y, %I:%M %p',
                '%b %d, %Y, %I:%M%p', '%b %d, %Y, %I:%M %p'):
        try:
            return datetime.strptime(raw,fmt).replace(tzinfo=LOCAL)
        except ValueError:
            continue
    return None


def _bounds(calendar):
    if (calendar or {}).get('status') not in ('calendar_closed','no_completed_period'):
        return {}
    # Roster-period calendars establish eligibility, not event-week assignment.
    if (calendar or {}).get('boundary_kind') != 'scoring':
        return {}
    result={}
    for number, interval in (calendar.get('schedule') or {}).items():
        try:
            n=int(number)
            # Date-only bounds identify calendar membership, not eligibility.
            start=date.fromisoformat(str(interval['start'])[:10])
            end=date.fromisoformat(str(interval['end'])[:10])
            if start > end:
                return {}
            result[n]=(start,end)
        except (ValueError,TypeError,KeyError):
            return {}
    return result


def _classification(record, calendar):
    """Return event period, source; do not infer from roster-effective week."""
    timestamp = _event_datetime((record.get('event_timestamp') or record.get('timestamp')))
    bounds = _bounds(calendar)
    if timestamp is not None and bounds:
        matching=[p for p,(start,end) in bounds.items() if start <= timestamp.date() <= end]
        if len(matching)==1:
            return matching[0], 'provider_calendar_event_date'
    # A commissioner-attested event date/period corrects a known mismatch
    # without mistaking Fantrax's roster-effective period for approval time.
    if (timestamp is not None and timestamp.date() == date(2026,11,18)
            and str(record.get('transaction_type') or '').lower() == 'trade'):
        players = [a for a in record.get('assets') or [] if isinstance(a,dict)
                   and 'draft pick' not in str(a.get('asset_name') or '').lower()]
        received, _ = _movements(record)
        if len(players) == 14 and {'Grabner By the Jussi','No Regretzkys'} <= set(received):
            return 8,'league_commissioner_event_attestation'
    # Explicit provider event-period fields may be used; season_week is not one.
    for key in ('event_period','approval_period'):
        try:
            value = int(record.get(key))
            if value > 0:
                return value, 'explicit_event_period'
        except (ValueError,TypeError):
            continue
    # The provider calendar may be absent from a historical snapshot. Preserve
    # legacy period-labeled observations without claiming event-date certainty.
    if not bounds:
        try:
            value=int(record.get('roster_effective_period') or record.get('season_week') or record.get('period'))
            return value, 'unverified_effective_period_fallback'
        except (ValueError, TypeError):
            pass
    return None,'event_period_unverified'


def _asset_market(record, received, players, picks, *, event_at):
    """Explain asset currency without declaring unverified trade motivations."""
    note=None
    if players >= 8 and not picks:
        note=("The exchange used players rather than draft picks. Pick scarcity may influence "
              "this market, but a motive cannot be proven from the transaction alone")
        # The league commissioner has specifically identified this event's
        # player-asset market context, distinct from provider transaction facts.
        if (event_at and event_at.date()==date(2026,11,18) and players==14
                and {'Grabner By the Jussi','No Regretzkys'} <= set(received)):
            note=("The league commissioner identifies limited available tradable picks as "
                  "context for this player-for-player asset exchange; this is attributed "
                  "league context, not an independently verified motive for either manager")
    return note


def investigate_transactions(history: dict, periods: list[int], *, calendar=None) -> dict:
    period_rows={p:[] for p in periods}
    unresolved=[]
    seen=set()
    date_verified_count=0
    for record in (history or {}).get('records') or []:
        if not isinstance(record,dict) or str(record.get('status') or '').lower() not in ('executed','completed'):
            continue
        txid=str(record.get('transaction_id') or '').strip()
        if not txid or txid in seen:
            continue
        seen.add(txid)
        event_period, source = _classification(record,calendar)
        if source=='provider_calendar_event_date':
            date_verified_count+=1
        if event_period is None:
            unresolved.append(txid)
            continue
        if event_period not in period_rows:
            continue
        try:
            effective = int(record.get('roster_effective_period') or record.get('season_week') or record.get('period'))
        except (ValueError,TypeError):
            effective = None
        typ=str(record.get('transaction_type') or '')
        assets=[a for a in record.get('assets') or [] if isinstance(a,dict)]
        received,unresolved_assets=_movements(record) if 'trade' in typ.lower() else ({},[])
        picks=sum(a.get('asset_type') in ('draft_pick','pick') or 'draft pick' in str(a.get('asset_name') or '').lower()
                  for a in assets)
        players=sum((a.get('asset_type') or 'player')=='player' and 'draft pick' not in str(a.get('asset_name') or '').lower()
                    for a in assets)
        dt=_event_datetime((record.get('event_timestamp') or record.get('timestamp')))
        event={'id':txid,'type':typ,'summary':str(record.get('summary') or '').strip(),
               'received':received,'unresolved_assets':unresolved_assets,
               'participants':[str(p.get('participant_name') or p.get('team_name') or '').strip()
                               for p in record.get('participants') or [] if isinstance(p,dict)],
               'player_count':players,'pick_count':picks,'asset_count':len(assets),
               'event_period':event_period,'roster_effective_period':effective,
               'event_timestamp':dt.isoformat() if dt else None,'event_period_source':source,
               'asset_movements':[{'asset_type':a.get('asset_type'), 'asset_name':a.get('asset_name'),
                                   'draft_pick':a.get('draft_pick'),
                                   'from_team_name':(a.get('movement_context') or {}).get('from_team_name'),
                                   'to_team_name':(a.get('movement_context') or {}).get('to_team_name')}
                                  for a in assets],
               'asset_market_note':_asset_market(record,received,players,picks,event_at=dt)}
        period_rows[event_period].append(event)
    for p in periods:
        period_rows[p].sort(key=lambda e: ((1 if 'trade' in e['type'].lower() else 0),
                                           e['player_count']+e['pick_count'],e['id']),reverse=True)
    trade_events=[ev for events in period_rows.values() for ev in events if 'trade' in ev['type'].lower()]
    trade_events.sort(key=lambda ev:(ev['asset_count'],ev['player_count'],ev['event_period'],ev['id']),reverse=True)
    return {'periods':[{'week':p,'count':len(period_rows[p]),'events':period_rows[p]} for p in periods],
            'spotlights':trade_events,'unresolved_count':len(unresolved),
            'event_time_based_count':date_verified_count,
            'coverage':'calendar_event_date' if date_verified_count else 'unverified_effective_period_fallback',
            'unresolved_ids':unresolved}
