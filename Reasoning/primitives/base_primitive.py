from abc import ABC, abstractmethod
from typing import Any

class BasePrimitive:
    """Base class for all Athena reasoning primitives."""

    name: str = "base"

    @abstractmethod
    def execute(self, request: Any, evidence_bundle: Any):
        raise NotImplementedError
