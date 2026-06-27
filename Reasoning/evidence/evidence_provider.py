from abc import ABC, abstractmethod

class EvidenceProvider(ABC):
    @abstractmethod
    def collect(self, subject, context):
        raise NotImplementedError
