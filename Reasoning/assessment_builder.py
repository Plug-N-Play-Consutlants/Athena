class AssessmentBuilder:
    def build(self,bundle):
        return {
            "summary":"Assessment generated.",
            "findings":getattr(bundle,"findings",[]),
            "confidence":getattr(bundle,"confidence",None),
            "rule_citations":getattr(bundle,"rule_citations",[])
        }
