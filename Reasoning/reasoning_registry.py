"""
Minimal reasoning registry for 4E stabilization.
"""


class ReasoningRegistry:
    """Resolve reasoning types to engine method names."""

    def __init__(self):
        self._registry = {
            "assessment": "reason_about_asset",
            "asset": "reason_about_asset",
            "asset_assessment": "reason_about_asset",
            "player_assessment": "reason_about_player",
        }

    def register(self, key: str, handler: str) -> None:
        self._registry[key] = handler

    def resolve(self, key: str):
        return self._registry.get(key)

    def keys(self):
        return sorted(self._registry.keys())
