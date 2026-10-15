import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.period_evidence_acquisition import inspect_player_stats_schema
secret="DO_NOT_EXPORT_PRIVATE_VALUE"
p={"statsTable":[{"playerId":secret,"cells":[{"value":secret,"statId":"G"}]}],"tableHeader":{"cells":[{"label":"GP","cells":[{"name":secret}]}]},"seasonOrProjections":[{"label":secret,"selected":True}],"posOrGroupList":[{"id":secret}],"statusOrTeamList":[{"name":secret}],"paginatedResultSet":{"totalCount":1234,"secret":secret}}
x=inspect_player_stats_schema(p)
assert x["statsTable_count"]==1
assert "cells" in x["first_stats_row_shape"]["keys"]
assert x["seasonOrProjections_selection_flags"]["selected"]==1
assert "totalCount" in x["pagination_shape"]["keys"]
assert secret not in str(x),x
print("[PASS] nested metadata inspection is bounded and value-free")
