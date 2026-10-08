"""Normalized current NHL organizational player evidence.

Raw communication remains in Providers.NHL. This layer turns roster/prospect and
club-stat payloads into investigation-ready facts without assigning a hidden
trade-value score or claiming front-office intent.
"""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, Iterable, List

def _name(v:Any)->str:
    if isinstance(v,dict): return str(v.get("default") or v.get("en") or next(iter(v.values()),"") or "")
    return str(v or "")
def _age(born:str)->int|None:
    try:
        b=date.fromisoformat(str(born));t=date.today();return t.year-b.year-((t.month,t.day)<(b.month,b.day))
    except (TypeError,ValueError):return None
def _rows(payload:Any)->List[Dict[str,Any]]:
    if not isinstance(payload,dict):return []
    out=[]
    for key in ("forwards","defensemen","goalies","skaters","players","prospects"):
        vals=payload.get(key)
        if isinstance(vals,list):out.extend(x for x in vals if isinstance(x,dict))
    return out

def normalize_team_player_evidence(team_abbrev:str, roster:Any, prospects:Any, club_stats:Any)->Dict[str,Any]:
    stats_rows=_rows(club_stats)
    stats_by_id={str(x.get("playerId") or x.get("id") or ""):x for x in stats_rows if x.get("playerId") or x.get("id")}
    def norm(row:Dict[str,Any],relationship:str)->Dict[str,Any]:
        pid=str(row.get("id") or row.get("playerId") or row.get("personId") or "")
        first=_name(row.get("firstName"));last=_name(row.get("lastName"));full=(first+" "+last).strip() or _name(row.get("name"))
        st=stats_by_id.get(pid,{})
        points=st.get("points")
        if points is None and isinstance(st.get("goals"),(int,float)) and isinstance(st.get("assists"),(int,float)):points=st["goals"]+st["assists"]
        return {"nhl_player_id":pid,"name":full,"team":team_abbrev.upper(),"relationship":relationship,
                "position":row.get("positionCode") or row.get("position") or "","shoots_catches":row.get("shootsCatches") or "",
                "birth_date":row.get("birthDate") or "","age":_age(row.get("birthDate") or ""),"height_inches":row.get("heightInInches"),"weight_pounds":row.get("weightInPounds"),
                "games_played":st.get("gamesPlayed"),"goals":st.get("goals"),"assists":st.get("assists"),"points":points,
                "plus_minus":st.get("plusMinus"),"avg_toi":st.get("avgTimeOnIcePerGame") or st.get("timeOnIcePerGame"),
                "power_play_goals":st.get("powerPlayGoals"),"power_play_points":st.get("powerPlayPoints"),"shots":st.get("shots")}
    roster_rows=_rows(roster);prospect_rows=_rows(prospects)
    players=[norm(x,"current_roster") for x in roster_rows]
    seen={p["nhl_player_id"] for p in players if p["nhl_player_id"]}
    prospect_players=[]
    for x in prospect_rows:
        p=norm(x,"prospect")
        if not p["nhl_player_id"] or p["nhl_player_id"] not in seen:prospect_players.append(p)
    return {"team":team_abbrev.upper(),"as_of":date.today().isoformat(),"roster":players,"prospects":prospect_players,
            "counts":{"roster":len(players),"prospects":len(prospect_players),"club_stats":len(stats_rows)},
            "provenance":["NHL public roster endpoint","NHL public prospects endpoint","NHL public club-stats endpoint"]}

def acquire_team_player_evidence(team_abbrev:str, client:Any=None)->Dict[str,Any]:
    from Providers.NHL.nhl_client import NHLClient
    c=client or NHLClient();errors=[];payloads={}
    for key,fn in (("roster",c.get_current_roster),("prospects",c.get_prospects),("club_stats",c.get_club_stats_now)):
        try:payloads[key]=fn(team_abbrev)
        except Exception as exc: errors.append(f"{key}: {type(exc).__name__}: {exc}");payloads[key]={}
    result=normalize_team_player_evidence(team_abbrev,payloads["roster"],payloads["prospects"],payloads["club_stats"]);result["acquisition_errors"]=errors
    return result
