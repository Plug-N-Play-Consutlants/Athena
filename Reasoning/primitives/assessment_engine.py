"""
Assessment Engine
"""
class AssessmentEngine:
    def build(self, findings):
        return {
            "summary": f"{len(findings)} findings evaluated.",
            "key_findings": findings,
            "overall_confidence": (
                sum(f.get("confidence",1.0) for f in findings)/len(findings)
                if findings else 0.0
            )
        }
