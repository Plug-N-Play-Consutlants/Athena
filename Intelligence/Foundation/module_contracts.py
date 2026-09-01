"""Module insertion contracts for Athena intelligence expansion.

This layer makes Athena module-adaptive. Future intelligence capabilities should
be registered through explicit contracts so orchestration, context selection,
response composition, diagnostics, and validators can discover them without
hard-coded feature rewrites.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, Tuple

MODULE_CONTRACT_VERSION = "0.6.4.1.0"


@dataclass(frozen=True)
class ModuleInsertionContract:
    """Declarative contract for an Athena intelligence module."""

    module_id: str
    capability_family: str
    supported_domains: Tuple[str, ...]
    required_inputs: Tuple[str, ...]
    produced_outputs: Tuple[str, ...]
    evidence_contract: Tuple[str, ...]
    context_contract: Tuple[str, ...]
    reasoning_hooks: Tuple[str, ...]
    composition_hooks: Tuple[str, ...]
    validation_gates: Tuple[str, ...]
    limitations: Tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    def supports_domain(self, domain: str = "") -> bool:
        key = str(domain or "").strip().lower()
        return not key or "all" in self.supported_domains or key in self.supported_domains

    def is_discoverable(self) -> bool:
        return bool(
            self.module_id
            and self.capability_family
            and self.produced_outputs
            and self.evidence_contract
            and self.context_contract
            and self.reasoning_hooks
            and self.composition_hooks
            and self.validation_gates
        )


    def capability_tokens(self) -> Tuple[str, ...]:
        """Return normalized tokens orchestration may use for adaptive discovery."""
        tokens = {
            self.module_id,
            self.capability_family,
            *self.produced_outputs,
            *self.evidence_contract,
            *self.context_contract,
            *self.reasoning_hooks,
            *self.composition_hooks,
        }
        return tuple(sorted(str(token).strip().lower() for token in tokens if str(token).strip()))

    def provides_capability(self, capability: str = "") -> bool:
        key = str(capability or "").strip().lower()
        return bool(key and key in self.capability_tokens())

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["contract_version"] = MODULE_CONTRACT_VERSION
        payload["discoverable"] = self.is_discoverable()
        return payload


CORE_INSERTION_CONTRACTS: Tuple[ModuleInsertionContract, ...] = (
    ModuleInsertionContract(
        module_id="player_assessment",
        capability_family="assessment",
        supported_domains=("all",),
        required_inputs=("identity", "knowledge", "history", "events"),
        produced_outputs=("assessment", "confidence", "explanation"),
        evidence_contract=("identity_registry", "knowledge_graph", "historical_intelligence", "event_intelligence"),
        context_contract=("player_profile", "organizational_context", "historical_context"),
        reasoning_hooks=("profile_reasoning", "comparative_reasoning", "confidence_reasoning"),
        composition_hooks=("player_experience", "evidence_panel", "public_summary"),
        validation_gates=("validate_player_intelligence_foundation", "validate_player_experience"),
        limitations=("Live feed completeness depends on provider availability.",),
    ),
    ModuleInsertionContract(
        module_id="team_assessment",
        capability_family="assessment",
        supported_domains=("all",),
        required_inputs=("identity", "knowledge", "events"),
        produced_outputs=("assessment", "summary", "confidence"),
        evidence_contract=("identity_registry", "knowledge_graph", "event_intelligence"),
        context_contract=("team_profile", "organizational_context", "competitive_window"),
        reasoning_hooks=("team_reasoning", "window_reasoning", "confidence_reasoning"),
        composition_hooks=("team_experience", "evidence_panel", "public_summary"),
        validation_gates=("validate_team_reasoning_engine",),
        limitations=("Offline mode may not include current roster or injury data.",),
    ),
    ModuleInsertionContract(
        module_id="event_assessment",
        capability_family="event_intelligence",
        supported_domains=("all",),
        required_inputs=("events", "sources", "identity"),
        produced_outputs=("event_context", "impact", "confidence"),
        evidence_contract=("source_profiles", "event_registry", "identity_registry"),
        context_contract=("timeline_context", "source_context", "impact_context"),
        reasoning_hooks=("event_reasoning", "cross_domain_impact", "confidence_reasoning"),
        composition_hooks=("news_experience", "timeline_summary", "evidence_panel"),
        validation_gates=("validate_event_intelligence_foundation", "validate_event_confidence_source_corroboration"),
        limitations=("Source corroboration quality varies by feed coverage.",),
    ),
    ModuleInsertionContract(
        module_id="decision_intelligence",
        capability_family="future_decision_intelligence",
        supported_domains=("organization", "fantasy", "public"),
        required_inputs=("objective", "constraints", "alternatives", "evidence", "context"),
        produced_outputs=("solution_comparison", "tradeoffs", "confidence", "limitations"),
        evidence_contract=("knowledge_graph", "historical_intelligence", "relationship_intelligence", "scenario_intelligence"),
        context_contract=("organizational_objective", "rule_environment", "competitive_window", "available_alternatives"),
        reasoning_hooks=("solution_reasoning", "counterfactual_reasoning", "scenario_reasoning"),
        composition_hooks=("decision_brief", "comparison_experience", "evidence_panel"),
        validation_gates=("future_validate_decision_intelligence_contract",),
        limitations=("Future module contract only; not an active recommendation engine."),
        metadata={"status": "future_contract"},
    ),
)


class ModuleContractRegistry:
    """Registry for insertion-adaptive Athena modules."""

    def __init__(self, contracts: Iterable[ModuleInsertionContract] | None = None) -> None:
        self._contracts: Tuple[ModuleInsertionContract, ...] = tuple(contracts or CORE_INSERTION_CONTRACTS)
        self._by_id = {contract.module_id.lower(): contract for contract in self._contracts}

    def all_contracts(self) -> Tuple[ModuleInsertionContract, ...]:
        return self._contracts

    def get(self, module_id: str) -> ModuleInsertionContract | None:
        return self._by_id.get(str(module_id or "").strip().lower())

    def for_domain(self, domain: str) -> Tuple[ModuleInsertionContract, ...]:
        return tuple(contract for contract in self._contracts if contract.supports_domain(domain))

    def resolve_capability(self, capability: str, domain: str = "") -> Tuple[ModuleInsertionContract, ...]:
        """Discover contracts that advertise a requested capability token."""
        return tuple(
            contract
            for contract in self.for_domain(domain)
            if contract.provides_capability(capability)
        )

    def resolve_capabilities(self, capabilities: Iterable[str], domain: str = "") -> Dict[str, Tuple[str, ...]]:
        return {
            str(capability): tuple(contract.module_id for contract in self.resolve_capability(capability, domain))
            for capability in capabilities
        }

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "version": MODULE_CONTRACT_VERSION,
            "status": "pass" if all(contract.is_discoverable() for contract in self._contracts) else "warn",
            "contract_count": len(self._contracts),
            "module_ids": sorted(contract.module_id for contract in self._contracts),
            "families": sorted({contract.capability_family for contract in self._contracts}),
            "module_adaptive": True,
            "all_discoverable": all(contract.is_discoverable() for contract in self._contracts),
        }


def seed_module_contract_registry() -> ModuleContractRegistry:
    return ModuleContractRegistry()


def module_contract_diagnostics() -> Dict[str, Any]:
    return seed_module_contract_registry().diagnostics()


__all__ = [
    "MODULE_CONTRACT_VERSION",
    "ModuleInsertionContract",
    "ModuleContractRegistry",
    "seed_module_contract_registry",
    "module_contract_diagnostics",
]
