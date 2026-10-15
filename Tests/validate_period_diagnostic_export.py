"""Regression: provider diagnostics survive Athena -> Studio observed-facts export."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.period_evidence_acquisition import _safe_error

assert _safe_error({"error": {"code": "BAD_PERIOD", "message": "Unsupported period"}}) == {"code": "BAD_PERIOD", "message": "Unsupported period"}
assert _safe_error({"errorCode": 403, "errorMessage": "Access denied"}) == {"code": "403", "message": "Access denied"}
assert "redacted" in _safe_error({"error": {"message": "token=abc123"}})["message"]
assert "abc123" not in str(_safe_error({"error": {"message": "token=abc123"}}))
source = (Path(__file__).resolve().parents[1] / "Athena" / "Investigation" / "period_execution.py").read_text(encoding="utf-8")
assert 'facts.append("Player-period provider diagnostic: "' in source
assert 'diagnostic = player_production.get("diagnostic") or {}' in source
router = (Path(__file__).resolve().parents[1] / "Scout" / "conversation" / "router.py").read_text(encoding="utf-8")
assert 'observed_facts=facts' in router
print("[PASS] Sanitized provider diagnostic preserved through observed-facts export contract")
