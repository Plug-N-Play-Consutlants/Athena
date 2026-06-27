"""Provider interface contract.

Every provider implementation should expose the same small public interface.
Authentication details, request mechanics, and provider-specific payloads stay
inside the provider. Athena and Scout consume this contract rather than reaching
into provider-specific implementation details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from Providers.base.session import ProviderSessionStatus


class ProviderError(Exception):
    """Base exception for provider framework failures."""


class ProviderAuthenticationError(ProviderError):
    """Raised when provider authentication is missing, expired, or invalid."""


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is missing or invalid."""


class BaseProvider(ABC):
    """Abstract provider contract."""

    provider_key: str = "base"
    provider_name: str = "Base Provider"

    @abstractmethod
    def connect(self, **kwargs: Any) -> Dict[str, Any]:
        """Connect or configure the provider session."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> Dict[str, Any]:
        """Disconnect or clear the active provider session."""
        raise NotImplementedError

    @abstractmethod
    def test(self, **kwargs: Any) -> Dict[str, Any]:
        """Test whether the provider connection is usable."""
        raise NotImplementedError

    @abstractmethod
    def status(self) -> ProviderSessionStatus:
        """Return safe provider session status."""
        raise NotImplementedError

    @abstractmethod
    def fetch(self, endpoint: str, **kwargs: Any) -> Any:
        """Fetch provider data by provider-specific endpoint key or route."""
        raise NotImplementedError

    def refresh_auth(self, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """Optional authentication refresh hook."""
        return None
