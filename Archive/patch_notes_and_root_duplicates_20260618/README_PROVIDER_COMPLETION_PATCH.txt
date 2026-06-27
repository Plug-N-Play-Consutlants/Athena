Replace/add these files:

Providers/Fantrax/fetch/discover_provider_capabilities.py
Providers/NHL/__init__.py
Providers/NHL/nhl_client.py
Providers/NHL/fetch/__init__.py
Providers/NHL/fetch/fetch_skater_summary.py
docs/Provider Completion Plan.md

Reference only:
Configuration/config.example.provider_completion.json

Run Fantrax capability discovery:

runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Providers/Fantrax/fetch/discover_provider_capabilities.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)

Run NHL skater summary fetch:

runfile(
    'F:/Development/Sports_Intelligence_Engine_2.0/Providers/NHL/fetch/fetch_skater_summary.py',
    wdir='F:/Development/Sports_Intelligence_Engine_2.0'
)
