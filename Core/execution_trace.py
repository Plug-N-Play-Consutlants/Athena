"""Execution trace foundation for AthenaEngine observability.

This module is intentionally lightweight and side-effect safe. It does not
change Scout routing, capability selection, or response composition. It gives
Studio and future Scout hooks a canonical model for recording what happened in
an execution path so later drops can compare expected versus actual behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple
import json
import time
import uuid

EXECUTION_TRACE_VERSION = "0.5.6.1.0"

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TRACE_DIR = _REPO_ROOT / "Reports" / "execution_traces"


def utc_now() -> str:
    """Return a stable UTC timestamp string for trace records."""
    return datetime.now(timezone.utc).isoformat()


def _duration_ms(start_monotonic: float | None, end_monotonic: float | None = None) -> float:
    if start_monotonic is None:
        return 0.0
    end = time.monotonic() if end_monotonic is None else end_monotonic
    return round(max(0.0, end - start_monotonic) * 1000.0, 3)


def _safe_dict(value: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not value:
        return {}
    out: Dict[str, Any] = {}
    for key, item in value.items():
        try:
            json.dumps(item)
            out[str(key)] = item
        except Exception:
            out[str(key)] = repr(item)
    return out


@dataclass
class ExecutionStage:
    """A single stage in a prompt execution trace."""

    stage_id: str
    label: str
    status: str = "pending"
    detail: str = ""
    confidence: float | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float = 0.0
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    skipped: bool = False
    fallback: bool = False
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    _start_monotonic: float | None = field(default=None, repr=False, compare=False)

    def start(self, **metadata: Any) -> "ExecutionStage":
        self.status = "running"
        self.started_at = utc_now()
        self._start_monotonic = time.monotonic()
        self.metadata.update(_safe_dict(metadata))
        return self

    def complete(
        self,
        status: str = "pass",
        detail: str = "",
        outputs: Mapping[str, Any] | None = None,
        confidence: float | None = None,
        **metadata: Any,
    ) -> "ExecutionStage":
        self.status = status
        self.detail = detail or self.detail
        self.outputs.update(_safe_dict(outputs))
        if confidence is not None:
            self.confidence = float(confidence)
        self.completed_at = utc_now()
        self.duration_ms = _duration_ms(self._start_monotonic)
        self.metadata.update(_safe_dict(metadata))
        return self

    def skip(self, reason: str = "", **metadata: Any) -> "ExecutionStage":
        self.status = "skipped"
        self.skipped = True
        self.detail = reason
        self.started_at = self.started_at or utc_now()
        self.completed_at = utc_now()
        self.duration_ms = _duration_ms(self._start_monotonic)
        self.metadata.update(_safe_dict(metadata))
        return self

    def fail(self, error: str, **metadata: Any) -> "ExecutionStage":
        self.status = "fail"
        self.error = str(error)
        self.detail = self.detail or str(error)
        self.completed_at = utc_now()
        self.duration_ms = _duration_ms(self._start_monotonic)
        self.metadata.update(_safe_dict(metadata))
        return self

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("_start_monotonic", None)
        return data


@dataclass
class CapabilityTrace:
    """How a capability participated in a trace."""

    capability_id: str
    expected: bool = False
    selected: bool = False
    executed: bool = False
    skipped: bool = False
    skip_reason: str = ""
    evidence_expected: Tuple[str, ...] = field(default_factory=tuple)
    evidence_found: Tuple[str, ...] = field(default_factory=tuple)
    evidence_missing: Tuple[str, ...] = field(default_factory=tuple)
    output_keys: Tuple[str, ...] = field(default_factory=tuple)
    included_output_keys: Tuple[str, ...] = field(default_factory=tuple)
    discarded_output_keys: Tuple[str, ...] = field(default_factory=tuple)
    confidence: float | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionTrace:
    """Canonical trace for a single Scout or Studio execution."""

    trace_id: str
    prompt: str
    mode: str = "public"
    version: str = EXECUTION_TRACE_VERSION
    created_at: str = field(default_factory=utc_now)
    completed_at: str | None = None
    status: str = "running"
    intent: str = "unknown"
    entities: Tuple[str, ...] = field(default_factory=tuple)
    expected_capabilities: Tuple[str, ...] = field(default_factory=tuple)
    selected_capabilities: Tuple[str, ...] = field(default_factory=tuple)
    skipped_capabilities: Tuple[str, ...] = field(default_factory=tuple)
    evidence_requested: Tuple[str, ...] = field(default_factory=tuple)
    evidence_found: Tuple[str, ...] = field(default_factory=tuple)
    evidence_missing: Tuple[str, ...] = field(default_factory=tuple)
    composition_inputs: Tuple[str, ...] = field(default_factory=tuple)
    composition_outputs: Tuple[str, ...] = field(default_factory=tuple)
    final_response_summary: str = ""
    confidence: float | None = None
    stages: List[ExecutionStage] = field(default_factory=list)
    capabilities: List[CapabilityTrace] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, prompt: str, mode: str = "public", **metadata: Any) -> "ExecutionTrace":
        return cls(
            trace_id=f"trace_{uuid.uuid4().hex[:16]}",
            prompt=str(prompt or ""),
            mode=str(mode or "public"),
            metadata=_safe_dict(metadata),
        )

    def add_stage(self, stage_id: str, label: str, inputs: Mapping[str, Any] | None = None, **metadata: Any) -> ExecutionStage:
        stage = ExecutionStage(
            stage_id=str(stage_id),
            label=str(label),
            inputs=_safe_dict(inputs),
            metadata=_safe_dict(metadata),
        )
        stage.start()
        self.stages.append(stage)
        return stage

    def add_capability(self, capability: CapabilityTrace) -> CapabilityTrace:
        self.capabilities.append(capability)
        return capability

    def complete(self, status: str = "pass", confidence: float | None = None, final_response_summary: str = "") -> "ExecutionTrace":
        self.status = status
        self.completed_at = utc_now()
        if confidence is not None:
            self.confidence = float(confidence)
        if final_response_summary:
            self.final_response_summary = str(final_response_summary)
        return self

    def duration_ms(self) -> float:
        return round(sum(float(stage.duration_ms or 0.0) for stage in self.stages), 3)

    def audit_summary(self) -> Dict[str, Any]:
        stage_statuses: Dict[str, int] = {}
        for stage in self.stages:
            stage_statuses[stage.status] = stage_statuses.get(stage.status, 0) + 1
        expected = set(self.expected_capabilities)
        selected = set(self.selected_capabilities)
        skipped = set(self.skipped_capabilities)
        missing = sorted(expected - selected - skipped)
        return {
            "trace_id": self.trace_id,
            "status": self.status,
            "intent": self.intent,
            "stage_count": len(self.stages),
            "stage_statuses": stage_statuses,
            "expected_capabilities": len(expected),
            "selected_capabilities": len(selected),
            "skipped_capabilities": len(skipped),
            "missing_expected_capabilities": missing,
            "evidence_requested": len(self.evidence_requested),
            "evidence_found": len(self.evidence_found),
            "evidence_missing": len(self.evidence_missing),
            "composition_inputs": len(self.composition_inputs),
            "composition_outputs": len(self.composition_outputs),
            "confidence": self.confidence,
            "duration_ms": self.duration_ms(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "prompt": self.prompt,
            "mode": self.mode,
            "version": self.version,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "intent": self.intent,
            "entities": list(self.entities),
            "expected_capabilities": list(self.expected_capabilities),
            "selected_capabilities": list(self.selected_capabilities),
            "skipped_capabilities": list(self.skipped_capabilities),
            "evidence_requested": list(self.evidence_requested),
            "evidence_found": list(self.evidence_found),
            "evidence_missing": list(self.evidence_missing),
            "composition_inputs": list(self.composition_inputs),
            "composition_outputs": list(self.composition_outputs),
            "final_response_summary": self.final_response_summary,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms(),
            "audit_summary": self.audit_summary(),
            "stages": [stage.to_dict() for stage in self.stages],
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "metadata": dict(self.metadata),
        }


def create_execution_trace(prompt: str, mode: str = "public", **metadata: Any) -> ExecutionTrace:
    return ExecutionTrace.create(prompt=prompt, mode=mode, **metadata)


def sample_execution_trace() -> ExecutionTrace:
    """Build an offline-safe sample trace used by doctors and Studio."""
    trace = create_execution_trace("How does Gavin McKenna help the Leafs?", mode="public", sample=True)
    trace.intent = "organizational_impact"
    trace.entities = ("Gavin McKenna", "Toronto Maple Leafs")
    trace.expected_capabilities = (
        "player_assessment",
        "team_assessment",
        "roster_assessment",
        "historical_assessment",
        "event_assessment",
        "reasoning",
        "response_composition",
    )
    trace.selected_capabilities = ("player_assessment", "team_assessment", "reasoning")
    trace.skipped_capabilities = ("roster_assessment", "event_assessment", "response_composition")
    trace.evidence_requested = ("player_profile", "team_profile", "roster", "prospects", "cap", "recent_events")
    trace.evidence_found = ("player_profile", "team_profile")
    trace.evidence_missing = ("roster", "prospects", "cap", "recent_events")
    trace.composition_inputs = ("player_assessment", "team_assessment", "reasoning")
    trace.composition_outputs = ("executive_summary", "limitations")

    trace.add_stage("intent_classification", "Intent Classification", {"prompt": trace.prompt}).complete(
        detail="organizational_impact", outputs={"intent": trace.intent}, confidence=0.82
    )
    trace.add_stage("entity_resolution", "Entity Resolution", {"prompt": trace.prompt}).complete(
        detail="Gavin McKenna, Toronto Maple Leafs", outputs={"entities": list(trace.entities)}, confidence=0.8
    )
    trace.add_stage("capability_selection", "Capability Selection", {"intent": trace.intent}).complete(
        detail="selected player/team/reasoning; skipped roster/event/composition", outputs={"selected": list(trace.selected_capabilities)}, confidence=0.64
    )
    trace.add_stage("evidence_collection", "Evidence Collection", {"requested": list(trace.evidence_requested)}).complete(
        detail="partial evidence available", outputs={"found": list(trace.evidence_found), "missing": list(trace.evidence_missing)}, confidence=0.55
    )
    trace.add_stage("reasoning", "Reasoning", {"capabilities": list(trace.selected_capabilities)}).complete(
        detail="bounded impact reasoning", outputs={"sections": ["executive_summary", "limitations"]}, confidence=0.68
    )
    trace.add_capability(CapabilityTrace(
        capability_id="player_assessment",
        expected=True,
        selected=True,
        executed=True,
        evidence_expected=("player_profile",),
        evidence_found=("player_profile",),
        output_keys=("profile", "strengths"),
        included_output_keys=("profile", "strengths"),
        confidence=0.82,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="roster_assessment",
        expected=True,
        selected=False,
        executed=False,
        skipped=True,
        skip_reason="not selected by current planner/routing path",
        evidence_expected=("roster", "cap", "prospects"),
        evidence_missing=("roster", "cap", "prospects"),
    ))
    return trace.complete(status="pass", confidence=0.68, final_response_summary="Sample trace shows partial execution and missing roster/cap evidence.")


def persist_execution_trace(trace: ExecutionTrace, folder: Path | None = None) -> Path:
    target = Path(folder) if folder else _TRACE_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{trace.trace_id}.json"
    path.write_text(json.dumps(trace.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_execution_trace(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def execution_trace_diagnostics(persist_sample: bool = False) -> Dict[str, Any]:
    trace = sample_execution_trace()
    path = ""
    if persist_sample:
        path = str(persist_execution_trace(trace).relative_to(_REPO_ROOT))
    return {
        "panel": "execution_trace",
        "version": EXECUTION_TRACE_VERSION,
        "status": trace.status,
        "trace_id": trace.trace_id,
        "summary": trace.audit_summary(),
        "sample_trace": trace.to_dict(),
        "persisted_sample": path,
        "supports": [
            "stage_timing",
            "expected_vs_selected_capabilities",
            "evidence_found_missing",
            "composition_input_output_counts",
            "persistent_trace_json",
        ],
    }


__all__ = [
    "EXECUTION_TRACE_VERSION",
    "CapabilityTrace",
    "ExecutionStage",
    "ExecutionTrace",
    "create_execution_trace",
    "execution_trace_diagnostics",
    "load_execution_trace",
    "persist_execution_trace",
    "sample_execution_trace",
]
