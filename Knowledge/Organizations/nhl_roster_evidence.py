"""Normalized current NHL organizational player evidence.

Raw communication remains in Providers.NHL. This layer turns roster/prospect and
club-stat payloads into investigation-ready facts without assigning a hidden
trade-value score or claiming front-office intent.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json
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
    _write_identity_snapshot(team_abbrev, result["roster"] + result["prospects"])
    return result


# Identity evidence is durable; organizational control is not. Never restore
# current-roster status or transferable rights from an older observation.
def _identity_snapshot_path(team_abbrev: str) -> Path:
    return Path(__file__).resolve().parents[2] / "Output" / "Knowledge" / "OrganizationalIdentity" / (team_abbrev.upper() + ".json")


def _read_identity_snapshot(team_abbrev: str) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(_identity_snapshot_path(team_abbrev).read_text(encoding="utf-8"))
        return [dict(p) for p in payload.get("players", []) if isinstance(p, dict) and p.get("nhl_player_id") and p.get("name")]
    except (OSError, ValueError, TypeError):
        return []


def _write_identity_snapshot(team_abbrev: str, players: List[Dict[str, Any]]) -> None:
    path = _identity_snapshot_path(team_abbrev)
    prior = {str(p["nhl_player_id"]): p for p in _read_identity_snapshot(team_abbrev)}
    for p in players:
        pid = str(p.get("nhl_player_id") or "")
        if pid and p.get("name"):
            prior[pid] = {"nhl_player_id": pid, "name": p["name"],
                          "identity_source": "previous_nhl_organizational_observation",
                          "last_seen": date.today().isoformat()}
    if not prior:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"team": team_abbrev.upper(), "players": list(prior.values())}, indent=2), encoding="utf-8")
        temporary.replace(path)
    except OSError:
        pass  # Persistence failure must not change the live rights assessment.


def acquire_historical_player_identities(team_abbrev: str, client: Any = None, max_seasons: int = 3) -> List[Dict[str, Any]]:
    """Identity-only fallback from observed historical rosters, never rights evidence."""
    from Providers.NHL.nhl_client import NHLClient
    c = client or NHLClient()
    found = {str(p["nhl_player_id"]): p for p in _read_identity_snapshot(team_abbrev)}
    if max_seasons <= 0:
        for value in found.values():
            value["relationship"] = "historical_identity_only"
            value["team"] = team_abbrev.upper()
            value["current_control_verified"] = False
        return list(found.values())
    try:
        raw_seasons = c.get_roster_seasons(team_abbrev)
        if isinstance(raw_seasons, dict):
            raw_seasons = raw_seasons.get("seasons") or raw_seasons.get("rosterSeasons") or []
        season_ids = []
        for entry in raw_seasons if isinstance(raw_seasons, list) else []:
            value = entry.get("seasonId") or entry.get("season") if isinstance(entry, dict) else entry
            if str(value or "").isdigit():
                season_ids.append(str(value))
        for season in sorted(set(season_ids), reverse=True)[:max_seasons]:
            roster = c.get_roster(team_abbrev, season)
            for row in _rows(roster):
                pid = str(row.get("id") or row.get("playerId") or "")
                name = ( _name(row.get("firstName")) + " " + _name(row.get("lastName")) ).strip() or _name(row.get("name"))
                if pid and name and pid not in found:
                    found[pid] = {"nhl_player_id": pid, "name": name,
                                  "relationship": "historical_roster_identity_only",
                                  "identity_source": "nhl_historical_roster", "observed_season": season}
    except Exception:
        # Cached verified identities remain usable if historical acquisition fails.
        pass
    for value in found.values():
        value["relationship"] = "historical_identity_only"
        value["team"] = team_abbrev.upper()
        value["current_control_verified"] = False
    return list(found.values())
