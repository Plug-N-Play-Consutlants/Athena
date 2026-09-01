"""Multi-sport intelligence foundation exports."""
from .modules import (
    INTELLIGENCE_FOUNDATION_VERSION,
    IntelligenceModule,
    IntelligenceRegistry,
    seed_intelligence_registry,
    select_intelligence_modules,
    capability_matrix,
    studio_intelligence_diagnostics,
)
from .module_contracts import (
    MODULE_CONTRACT_VERSION,
    ModuleInsertionContract,
    ModuleContractRegistry,
    seed_module_contract_registry,
    module_contract_diagnostics,
)

__all__ = [
    "INTELLIGENCE_FOUNDATION_VERSION",
    "IntelligenceModule",
    "IntelligenceRegistry",
    "seed_intelligence_registry",
    "select_intelligence_modules",
    "capability_matrix",
    "studio_intelligence_diagnostics",
    "MODULE_CONTRACT_VERSION",
    "ModuleInsertionContract",
    "ModuleContractRegistry",
    "seed_module_contract_registry",
    "module_contract_diagnostics",
]
