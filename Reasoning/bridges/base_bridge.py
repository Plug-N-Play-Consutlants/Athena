from abc import ABC, abstractmethod

class BaseBridge(ABC):
    name="base"
    @abstractmethod
    def collect(self, subject, context):
        return []
