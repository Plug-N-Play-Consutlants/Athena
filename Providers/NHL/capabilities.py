"""Discoverable evidence capabilities supplied by the existing NHL provider."""
NHL_PROVIDER_CAPABILITIES={
    "current_roster":"get_current_roster",
    "historical_roster":"get_roster",
    "roster_seasons":"get_roster_seasons",
    "prospects":"get_prospects",
    "club_stats_current":"get_club_stats_now",
    "club_stats_season":"get_club_stats",
    "club_stat_seasons":"get_club_stats_seasons",
    "player_landing":"get_player_landing",
    "player_game_log":"get_skater_game_log",
    "skater_summary":"get_skater_summary",
    "goalie_summary":"get_goalie_summary",
    "skater_report":"get_skater_report",
    "goalie_report":"get_goalie_report",
    "team_report":"get_team_report",
}
def supports(capability:str)->bool:return capability in NHL_PROVIDER_CAPABILITIES
def method_for(capability:str)->str:return NHL_PROVIDER_CAPABILITIES[capability]
