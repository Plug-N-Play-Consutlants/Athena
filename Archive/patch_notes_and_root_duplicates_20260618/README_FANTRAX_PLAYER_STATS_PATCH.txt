Replace/add these files:

Providers/Fantrax/fantrax_client.py
Providers/Fantrax/fetch/fetch_player_stats.py
Providers/Fantrax/fetch/fetch_all.py
Knowledge/player_production.py
docs/Fantrax Player Stats Fetch.md

Optional reference only:
Configuration/config.example.player_stats.json

Run:

runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Providers/Fantrax/fetch/fetch_player_stats.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)

Then:

runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Knowledge/player_production.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)
