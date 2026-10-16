"""Repository-grounded Athena diagnostics with explicit trace limitations."""
from __future__ import annotations

from typing import Any


def execute_diagnostic(ctx: Any, question: str) -> dict[str, Any]:
    from Athena.execution_registry import SPECIALISTS
    from Scout.conversation.responses import developer_info, response

    registered = sorted(SPECIALISTS)
    facts = [
        "Athena selected the registered diagnostic capability for this request.",
        f"The repository currently registers {len(registered)} specialist capabilities.",
        "This diagnostic route does not retrieve prior-turn execution traces.",
    ]
    natural = (
        "I can report the capabilities registered in this repository, but this request "
        "does not retrieve a prior-turn execution trace. I cannot verify which capabilities "
        "or evidence sources were used for an earlier answer."
    )
    return response(
        intent="athena_runtime_diagnostics",
        title="Athena execution diagnostics",
        engine_conclusion=natural + "\n\nRegistered capabilities: " + ", ".join(registered) + ".",
        natural_language_response=natural + "\n\nRegistered capabilities: " + ", ".join(registered) + ".",
        observed_facts=facts,
        known_limitations=["prior_turn_execution_trace_unavailable"],
        confidence=1.0,
        developer=developer_info(
            "athena_runtime_diagnostics",
            getattr(ctx, "files_loaded", []),
            knowledge_used=["Athena.execution_registry"],
            intelligence_used=["athena_diagnostic_intent"],
            missing=["prior_turn_execution_trace"],
        ) | {"registered_capabilities": registered},
    )
