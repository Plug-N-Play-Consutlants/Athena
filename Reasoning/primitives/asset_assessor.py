"""
Asset Assessor integration.
"""
from Reasoning.evidence.evidence_fusion import EvidenceFusion
from .finding_builder import FindingBuilder
from .assessment_engine import AssessmentEngine

class AssetAssessor:
    def __init__(self):
        self.fusion=EvidenceFusion()
        self.findings=FindingBuilder()
        self.assessment=AssessmentEngine()

    def assess(self,*collections):
        fused=self.fusion.fuse(*collections)
        findings=self.findings.build(fused)
        return self.assessment.build(findings)
