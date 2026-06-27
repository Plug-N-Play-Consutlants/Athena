"""
Evidence merger.
"""
class EvidenceMerger:
    def merge(self, *collections):
        merged = []
        for c in collections:
            if c:
                merged.extend(c)
        return merged
