"""Guard recap handling of relative-week prompts without an explicit week regex match."""
import ast
from pathlib import Path

router = Path(__file__).resolve().parents[1] / "Scout" / "conversation" / "router.py"
source = router.read_text(encoding="utf-8")
tree = ast.parse(source)
assert "compose_league_editorial(editorial, explicit_week.group(1))" not in source
assert "compose_league_editorial(editorial, selected_period if selected_period is not None else inquiry.temporal_scope.label)" in source
assert "int(explicit_week.group(1)) if explicit_week else resolve_archived_period" in source
assert "investigation_execution_trace" in source
print("PASS: relative-week recap no longer dereferences absent explicit_week; explicit-week selection preserved")
