"""
Finding Builder
"""
class FindingBuilder:
    def build(self, evidence):
        findings=[]
        for item in evidence:
            findings.append({
                "category": getattr(item,"source_type","general"),
                "statement": getattr(item,"summary",str(item)),
                "confidence": getattr(item,"confidence",1.0)
            })
        return findings
