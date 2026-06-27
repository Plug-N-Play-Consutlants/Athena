class ConfidenceEngine:
    def score(self, findings, evidence_bundle):
        if not findings:
            return {"score":0.0,"level":"none"}
        avg=sum(f.get("confidence",1.0) for f in findings)/len(findings)
        level="high" if avg>=0.8 else "medium" if avg>=0.5 else "low"
        return {"score":round(avg,3),"level":level}
