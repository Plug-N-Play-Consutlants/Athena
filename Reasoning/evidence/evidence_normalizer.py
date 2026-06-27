"""
Evidence normalizer.
"""
from typing import Iterable

class EvidenceNormalizer:
    def normalize(self, evidence: Iterable):
        seen = set()
        result = []
        for item in evidence:
            key = getattr(item, "id", repr(item))
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result
