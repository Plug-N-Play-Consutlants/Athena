"""
Minimal evidence fusion.
"""
from .evidence_merger import EvidenceMerger
from .evidence_normalizer import EvidenceNormalizer

class EvidenceFusion:
    def __init__(self):
        self._merge = EvidenceMerger()
        self._normalize = EvidenceNormalizer()

    def fuse(self, *collections):
        merged = self._merge.merge(*collections)
        return self._normalize.normalize(merged)
