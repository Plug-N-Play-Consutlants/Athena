"""Validate Athena foundational governance and module-adaptive contracts."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
from Intelligence.Foundation import (
    MODULE_CONTRACT_VERSION,
    ModuleInsertionContract,
    seed_module_contract_registry,
)

FOUNDATION_FILES = [
    "Athena_Constitution.md",
    "Athena_Manifesto.md",
    "Athena_Intelligence_Model.md",
    "Scout_Principles.md",
    "Engineering_Principles.md",
    "Product_Vision.md",
    "Roadmap.md",
    "Decision_Record_Template.md",
]


def check(label: str, condition: bool, detail: object, failures: list[str]) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}: {detail}")
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    print("Foundational Governance Validation")
    print("=" * 64)

    check("version_advanced_to_6c", ATHENA_VERSION >= "0.6.3.0.0", ATHENA_VERSION, failures)
    check("release_name", RELEASE_NAME in {"Foundational Governance and Module Adaptivity", "Foundational Governance Cleanup Tolerance Hotfix", "Adaptive Investigation Strategy Foundation", "Adaptive Investigation Runtime Integration"}, RELEASE_NAME, failures)
    check("version_schema_locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA, failures)
    check("module_contract_version", MODULE_CONTRACT_VERSION >= "0.6.3.0.0", MODULE_CONTRACT_VERSION, failures)

    foundations_dir = PROJECT_ROOT / "Foundations"
    check("foundations_directory", foundations_dir.exists(), foundations_dir, failures)

    for filename in FOUNDATION_FILES:
        path = foundations_dir / filename
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        check(f"foundation_document:{filename}", path.exists() and len(text.strip()) > 100, filename, failures)

    constitution = (foundations_dir / "Athena_Constitution.md").read_text(encoding="utf-8")
    check("north_star_locked", "Athena transforms curiosity into understanding" in constitution, "North Star", failures)
    check("evidence_before_conclusions", "Evidence before agreement" in constitution and "Reasoning before conclusions" in constitution, "principles", failures)

    engineering = (foundations_dir / "Engineering_Principles.md").read_text(encoding="utf-8")
    check("module_adaptive_engineering_rule", "Athena should be module-adaptive" in engineering, "module adaptive", failures)
    check("registry_over_imports", "Registries over imports" in engineering, "registries", failures)
    check("contract_over_hardcoding", "Contracts over hardcoding" in engineering, "contracts", failures)

    registry = seed_module_contract_registry()
    diagnostics = registry.diagnostics()
    check("contract_registry_pass", diagnostics.get("status") == "pass", diagnostics, failures)
    check("contract_registry_count", diagnostics.get("contract_count", 0) >= 4, diagnostics, failures)
    check("decision_intelligence_contract_present", registry.get("decision_intelligence") is not None, diagnostics.get("module_ids"), failures)

    sample = ModuleInsertionContract(
        module_id="sample_future_module",
        capability_family="future",
        supported_domains=("all",),
        required_inputs=("evidence",),
        produced_outputs=("context",),
        evidence_contract=("knowledge_graph",),
        context_contract=("investigation_context",),
        reasoning_hooks=("sample_reasoning",),
        composition_hooks=("sample_composition",),
        validation_gates=("sample_validation",),
    )
    check("new_module_contract_discoverable", sample.is_discoverable(), sample.to_dict(), failures)
    check("new_module_domain_support", sample.supports_domain("hockey") and sample.supports_domain(""), sample.supported_domains, failures)

    print("-" * 64)
    if failures:
        print("Overall status: FAIL")
        print(f"Failed: {len(failures)}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
