"""Provider registry.

The registry keeps Athena provider-neutral. Athena asks the registry for a
provider by key; it does not import provider implementations directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Callable, Dict, Type

from Providers.base.provider import BaseProvider, ProviderConfigurationError

ProviderFactory = Callable[[], BaseProvider]


@dataclass
class ProviderRegistry:
    """Simple provider registry with lazy provider construction."""

    _factories: Dict[str, ProviderFactory] = field(default_factory=dict)

    @staticmethod
    def normalize_key(key: str) -> str:
        return str(key or "").strip().lower()

    def register(self, key: str, provider: Type[BaseProvider] | ProviderFactory) -> None:
        """Register a provider class or zero-argument factory."""
        normalized = self.normalize_key(key)
        if not normalized:
            raise ProviderConfigurationError("Provider registry key is required.")

        if isinstance(provider, type):
            if not issubclass(provider, BaseProvider):
                raise ProviderConfigurationError(
                    f"Provider '{key}' must inherit from BaseProvider."
                )
            self._factories[normalized] = provider
            return

        if not callable(provider):
            raise ProviderConfigurationError(f"Provider '{key}' must be callable.")
        self._factories[normalized] = provider

    def unregister(self, key: str) -> None:
        self._factories.pop(self.normalize_key(key), None)

    def keys(self) -> list[str]:
        return sorted(self._factories.keys())

    def has(self, key: str) -> bool:
        return self.normalize_key(key) in self._factories

    def get(self, key: str) -> BaseProvider:
        """Return a new provider instance for the requested key."""
        normalized = self.normalize_key(key)
        factory = self._factories.get(normalized)
        if factory is None:
            raise ProviderConfigurationError(f"Provider '{key}' is not registered.")
        provider = factory()
        if not isinstance(provider, BaseProvider):
            raise ProviderConfigurationError(
                f"Provider '{key}' factory did not return a BaseProvider instance."
            )
        return provider

    def describe(self) -> Dict[str, Any]:
        return {
            "providers": self.keys(),
            "count": len(self._factories),
        }


def _lazy_provider(import_path: str, class_name: str) -> ProviderFactory:
    def factory() -> BaseProvider:
        module = import_module(import_path)
        provider_cls = getattr(module, class_name)
        return provider_cls()

    return factory


registry = ProviderRegistry()


def register_provider(key: str, provider: Type[BaseProvider] | ProviderFactory) -> None:
    registry.register(key, provider)


def get_provider(key: str) -> BaseProvider:
    return registry.get(key)


def registered_providers() -> list[str]:
    return registry.keys()


# First concrete provider adapter. Lazy import avoids import-time dependency
# failures while keeping Athena provider-neutral.
register_provider("fantrax", _lazy_provider("Providers.Fantrax.fantrax_provider", "FantraxProvider"))
