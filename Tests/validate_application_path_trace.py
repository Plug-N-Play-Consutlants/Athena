"""Validate that the system-wide pathway trace is complete and honest."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tools.application_path_trace import build_trace

trace = build_trace()
checks = {
    "trace_contract": trace.get("contract") == "athena_application_path_trace",
    "major_domains_traced": set(trace.get("trace_scope") or []) == {"player_identity_and_stats", "current_news_events", "rules_and_cap_boundary", "historical_fantasy"},
    "representative_routes_resolve": not trace.get("route_failures"),
    "player_canonical_authority_visible": next(c for c in trace["cases"] if c["domain"] == "player_identity_and_stats")["authority"] == "canonical_player_statistical_evidence",
    "cap_gap_explicit": any(i.get("id") == "current_public_cap_ledger" and i.get("status") == "known_unregistered" for i in trace["unresolved"]),
    "scout_ownership_debt_explicit": any(i.get("id") == "scout_specialist_implementation_ownership" and i.get("status") == "correction_required" for i in trace["unresolved"]),
}
for label, good in checks.items():
    print(f"[{'PASS' if good else 'FAIL'}] {label}")
print(f"[TRACE] structural_corrections_required={trace['structural_corrections_required']}")
raise SystemExit(0 if all(checks.values()) else 1)
