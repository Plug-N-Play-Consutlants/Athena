"""Cross-player profile integrity: simple names, expanded requests, same-name selection."""
from __future__ import annotations

from unittest.mock import patch

from Knowledge.Intelligence.Public import player_evidence as evidence
from Scout.conversation.router import route_question
from Knowledge.Intelligence.Entities.entity_registry import find_by_id


LONG_OV = ("Give me a complete scouting profile of Alex Ovechkin. Evaluate his current NHL "
           "performance, career achievements, historical scoring trends, playing style, "
           "strengths, weaknesses, age-related considerations, and current value. "
           "Distinguish his career legacy from his present-day performance, and explain any evidence limitations.")


def _offline(monkeypatch):
    monkeypatch.setenv("ATHENA_NHL_PLAYER_NETWORK", "0")


def test_bare_ovechkin_provides_dated_official_historical_stats(monkeypatch):
    _offline(monkeypatch)
    a = route_question("Alex Ovechkin", mode="public")
    assert a["intent"] == "public_player_profile"
    assert a["player"]["full_name"] == "Alex Ovechkin"
    assert "64 points in 82 games" in a["public_comment"]
    assert "2025-26" in a["title"]
    assert "complete career record" in a["public_comment"]
    assert a["stats"] == {}  # Never present 2025-26 as current 2026-27.
    assert a["season_statistics"][0]["season"] == "2025-26"


def test_full_ovechkin_scouting_request_does_not_become_stature_or_system_limitations(monkeypatch):
    _offline(monkeypatch)
    a = route_question(LONG_OV, mode="public")
    assert a["intent"] == "public_player_profile"
    assert "Alex Ovechkin" in a["title"]
    assert "64 points in 82 games" in a["public_comment"]
    assert "one-timer" in a["public_comment"].lower()
    assert "unrated" not in a["public_comment"]


def test_aho_choice_prompts_keep_distinct_subjects(monkeypatch):
    _offline(monkeypatch)
    a = route_question("Sebastian Aho", mode="public")
    assert a["intent"] == "public_entity_disambiguation"
    assert len(a["cards"]) == 2
    car = route_question("Sebastian Aho Carolina Hurricanes center", mode="public")
    swe = route_question("Sebastian Aho Swedish defenseman", mode="public")
    assert car["intent"] == swe["intent"] == "public_player_profile"
    assert car["player"]["position"] == "C"
    assert swe["player"]["position"] == "D"
    assert car["player"]["nationality"] == "Finland"
    assert swe["player"]["nationality"] == "Sweden"
    assert "80 points in 79 games" in car["public_comment"]
    assert "80 points in 79 games" not in swe["public_comment"]
    assert "historical ties to NYI/AHL" in swe["public_comment"]


def _landing(name, dob, pos, club, nhl_id):
    first, last = name.split(" ", 1)
    return {
        "firstName": {"default": first}, "lastName": {"default": last},
        "birthDate": dob, "position": pos, "currentTeamAbbrev": club,
        "sweaterNumber": 8, "headshot": f"https://example.invalid/{nhl_id}.png",
        "featuredStats": {"season": 20262027, "regularSeason": {
            "subSeason": {"gamesPlayed": 4, "points": 4, "goals": 2, "assists": 2, "plusMinus": 1},
            "career": {"gamesPlayed": 900, "points": 500, "goals": 300}}},
        "seasonTotals": [{"leagueAbbrev":"NHL", "gameTypeId":2, "season":20262027,
                         "gamesPlayed":4,"points":4,"goals":2,"assists":2,"plusMinus":1},
                         {"leagueAbbrev":"NHL", "gameTypeId":2, "season":20252026,
                         "gamesPlayed":70,"points":60,"goals":30,"assists":30,"plusMinus":2}]
    }


def test_exact_id_landing_recovery_normalizes_lw_and_checks_birth(monkeypatch):
    monkeypatch.setenv("ATHENA_NHL_PLAYER_NETWORK", "1")
    payload = _landing("Alex Ovechkin", "1985-09-17", "L", "WSH", "8471214")
    evidence._verified_landing_by_id.cache_clear()
    with patch.object(evidence, "_verified_landing_by_id", return_value=payload) as get_landing, \
         patch.object(evidence, "_live_record", return_value=None):
        a = evidence.player_evidence("Alex Ovechkin", team="WSH", position="LW", birth_date="1985-09-17")
        assert a.get("nhl_id") == "8471214"
        assert a["stats"]["points"] == 4
        get_landing.assert_called_once_with("8471214", "Alex Ovechkin", "LW", "1985-09-17")
    with patch.object(evidence, "_verified_landing_by_id", return_value=None), \
         patch.object(evidence, "_live_record", return_value=None):
        a = evidence.player_evidence("Alex Ovechkin", team="WSH", position="LW", birth_date="1985-09-17")
        assert a.get("source") == "nhl_skater_summary"
        assert not a.get("stats")


def test_same_name_defender_historical_landing_requires_birth_date(monkeypatch):
    monkeypatch.setenv("ATHENA_NHL_PLAYER_NETWORK", "1")
    swe = _landing("Sebastian Aho", "1996-02-17", "D", "", "historic_aho_id")
    def season_index(s):
        return ([{"skaterFullName": "Sebastian Aho", "positionCode": "D",
                  "teamAbbrevs": "NYI", "playerId": "historic_aho_id"}]
                if str(s) == "20232024" else [])
    class Client:
        def get_player_landing(self, player_id):
            return swe
    with patch.object(evidence, "_records", return_value=([], {})), \
         patch.object(evidence, "_cached_summary_candidates", return_value=[]), \
         patch.object(evidence, "_season_index", side_effect=season_index), \
         patch("Providers.NHL.nhl_client.NHLClient", Client):
        evidence._live_record.cache_clear()
        record = evidence.player_evidence("Sebastian Aho", team="NYI/AHL", position="D", birth_date="1996-02-17")
        assert record["nhl_id"] == "historic_aho_id"
        assert record["birth_date"] == "1996-02-17"
        assert record["position"] == "D"
        bad = evidence.player_evidence("Sebastian Aho", team="NYI/AHL", position="D", birth_date="1997-07-26")
        assert bad == {}
    evidence._live_record.cache_clear()
