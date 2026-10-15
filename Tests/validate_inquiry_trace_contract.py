"""Hermetic diagnostic-contract test: no network, credentials or Studio dependency."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.request_execution import AthenaRequest, execute_request
from Athena.execution_registry import Specialist


def run():
    context = SimpleNamespace()
    fake_registry = {"probe": Specialist("probe", "test.module", "probe_handler", "public")}
    evidence = {"status": "partial", "sources": ["canonical_probe"], "missing": ["current_roster"]}
    result = {"intent": "probe", "confidence": 0.9, "natural_language_response": "Bounded result"}
    with patch("Athena.intent_resolution.select_executable_route", return_value=("probe", "test_selection")), \
         patch("Athena.execution_registry.SPECIALISTS", fake_registry), \
         patch("Athena.execution_registry.execute_specialist", return_value=result), \
         patch("Athena.evidence_bundle.build_request_evidence", return_value=evidence):
        answer = execute_request(AthenaRequest("Probe request", mode="public", context=context))
    trace = answer["developer"]["inquiry_execution_trace"]
    assert trace["selection"]["registered"] is True
    assert trace["invocation"]["completed"] is True
    assert trace["invocation"]["route"] == "probe"
    assert trace["evidence"]["missing"] == ["current_roster"]
    assert trace["evidence"]["attached_to_context"] is True
    assert context.request_evidence is evidence
    assert trace["result"]["inquiry_completeness_verified"] is False
    assert trace["result"]["evidence_consumption_verified"] is False
    assert "Probe request" not in str(trace)
    assert answer["natural_language_response"] == "Bounded result"
    # A route-less inquiry must be labeled as a legacy Scout adapter, never
    # misreported as an Athena specialist invocation.
    with patch("Athena.intent_resolution.select_executable_route", return_value=(None, "unmatched")), \
         patch("Athena.evidence_bundle.build_request_evidence", return_value={"status": "not_required", "sources": [], "missing": []}), \
         patch("Athena.specialist_compatibility.execute_existing_specialist", return_value={"intent": "legacy", "public_comment": "Legacy answer"}):
        fallback = execute_request(AthenaRequest("Unmatched request", mode="fantasy", context=SimpleNamespace()))
    legacy = fallback["developer"]["inquiry_execution_trace"]
    assert legacy["selection"]["registered"] is False
    assert legacy["invocation"]["owner"] == "legacy_scout_specialist_adapter"
    assert legacy["invocation"]["route"] == "legacy_fallback"
    assert legacy["result"]["public_fields_present"] == ["public_comment"]
    print("PASS: request trace records execution and evidence without asserting completeness")


if __name__ == "__main__":
    run()
