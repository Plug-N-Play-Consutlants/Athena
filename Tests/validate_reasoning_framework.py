from Reasoning.reasoning_registry import ReasoningRegistry
from Reasoning.evidence.evidence_bundle import EvidenceBundle
r=ReasoningRegistry()
r.register("asset_assessment",object())
b=EvidenceBundle()
assert "asset_assessment" in r.names()
assert len(b.evidence)==0
print("Reasoning Framework Validation PASS")
