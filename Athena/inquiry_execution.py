"""Athena's bounded specialist execution and observable inquiry lifecycle.

The registry is a capability census, not permission to execute every specialist.
No presentation-layer inference is treated as acquired evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from Athena.execution_registry import SPECIALISTS, execute_specialist
from Athena.intent_resolution import select_executable_route


@dataclass(frozen=True)
class CapabilityRecord:
    route: str
    owner: str
    eligibility: str
    reason: str
    state: str


def capability_catalog() -> list[dict[str, str]]:
    return [dict(route=s.route, owner=s.module + "." + s.function,
                 domain=s.mode, registered="true")
            for s in sorted(SPECIALISTS.values(), key=lambda x: x.route)]


def _record(route: str, eligibility: str, reason: str, state: str) -> dict[str, str]:
    spec = SPECIALISTS[route]
    return asdict(CapabilityRecord(route, spec.module + "." + spec.function,
                                   eligibility, reason, state))


def _remaining_capabilities(route: str, mode: str) -> list[dict[str, str]]:
    """Account for registered capabilities without executing unrelated modules."""
    return [
        _record(name, "gated" if spec.mode == "fantasy" and mode != "fantasy" else "not_selected",
                "fantasy_mode_required" if spec.mode == "fantasy" and mode != "fantasy" else "not_selected_by_inquiry_planner",
                "skipped")
        for name, spec in sorted(SPECIALISTS.items()) if name != route
    ]


def _completion(result: Any, status: str) -> dict[str, Any]:
    """Report *observed* execution, not an unsupported claim of answer completeness."""
    if status != "executed":
        return {"state": "not_assessed", "reason": status, "requirements": []}
    if not isinstance(result, dict):
        return {"state": "unverified", "reason": "unstructured_specialist_result", "requirements": []}
    declared = result.get("inquiry_completion")
    if isinstance(declared, dict) and declared.get("state") in {"complete", "partial", "blocked"}:
        return {"state": declared["state"], "reason": "specialist_declared",
                "requirements": declared.get("requirements", []),
                "unresolved": declared.get("unresolved", [])}
    return {"state": "unverified", "reason": "specialist_did_not_supply_clause_coverage",
            "requirements": []}


def investigate(question: str, context: Any, *, mode: str = "public") -> dict[str, Any]:
    """Execute one selected specialist; expose eligibility, failures and completion.

    Legacy fallback remains explicit until its handlers are migrated. Exceptions
    are not silently converted to an empty answer, and the compatibility caller
    may still propagate them while diagnostic consumers can inspect the outcome.
    """
    selected = (mode or "public").strip().lower()
    route, selection_reason = select_executable_route(question, selected)
    if not route or route not in SPECIALISTS:
        status = "legacy_fallback" if not route else "unregistered"
        return {"status": status, "result": None, "selection_reason": selection_reason,
                "capability_ledger": _remaining_capabilities("", selected),
                "completion": _completion(None, status)}
    spec = SPECIALISTS[route]
    if spec.mode == "fantasy" and selected != "fantasy":
        status, result = "gated", None
        first = _record(route, "gated", "fantasy_mode_required", "skipped")
    else:
        try:
            result = execute_specialist(route, context, question, mode=selected)
        except Exception as exc:
            status = "failed"
            first = _record(route, "eligible", "handler_raised_" + type(exc).__name__, "failed")
            return {"status": status, "result": None, "selection_reason": selection_reason,
                    "capability_ledger": [first] + _remaining_capabilities(route, selected),
                    "completion": _completion(None, status), "error_type": type(exc).__name__}
        status = "executed" if result is not None else "no_result"
        first = _record(route, "eligible", selection_reason, status)
    return {"status": status, "result": result, "selection_reason": selection_reason,
            "capability_ledger": [first] + _remaining_capabilities(route, selected),
            "completion": _completion(result, status)}


def answer(question: str, context: Any, *, mode: str = "public") -> dict[str, Any] | None:
    """Legacy Scout response shape; never mistake unverified for complete."""
    outcome = investigate(question, context, mode=mode)
    return outcome["result"]
