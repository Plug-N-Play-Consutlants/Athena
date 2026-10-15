import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.period_evidence_acquisition import inspect_player_stats_schema
p={"tableHeader":{"cells":[{"key":"GP","name":"Games Played","shortName":"GP"},{"key":"G","name":"Goals","shortName":"G"},{"key":"auth-token","name":"bearer secret","shortName":"G"}]},"seasonOrProjections":[{"code":"SEASON_31l_YEAR_TO_DATE","name":"2026-27","shortName":"2026"},{"code":"http://unsafe/?secret=1","name":"@private","shortName":"A"}],"statsTable":[{"cells":[{"value":"DO_NOT_EXPORT_PRIVATE_PLAYER"}]}],"paginatedResultSet":{"pageNumber":1,"maxResultsPerPage":500,"totalCount":1250}}
x=inspect_player_stats_schema(p)
assert x["header_columns"][1]["key"]=="G"
assert x["season_option_metadata"][0]["code"]=="SEASON_31l_YEAR_TO_DATE"
assert x["pagination_values"]["totalCount"]==1250
assert x["page_full"] is False
assert "DO_NOT_EXPORT_PRIVATE_PLAYER" not in str(x)
assert "http://unsafe" not in str(x)
assert "bearer secret" not in str(x)
assert "auth-token" not in str(x)
print("[PASS] safe selector metadata and pagination; private values excluded")
