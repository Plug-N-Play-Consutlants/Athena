"""Provider foundation package."""

from Providers.base.connection_state import ConnectionState
from Providers.base.events import ProviderEvent, provider_event
from Providers.base.provider import (
    BaseProvider,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
)
from Providers.base.registry import (
    ProviderRegistry,
    get_provider,
    register_provider,
    registered_providers,
    registry,
)
from Providers.base.session import ProviderSessionStatus

__all__ = [
    "BaseProvider",
    "ConnectionState",
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderError",
    "ProviderEvent",
    "ProviderRegistry",
    "ProviderSessionStatus",
    "get_provider",
    "provider_event",
    "register_provider",
    "registered_providers",
    "registry",
]
