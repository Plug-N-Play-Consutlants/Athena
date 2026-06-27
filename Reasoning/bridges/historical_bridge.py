from .base_bridge import BaseBridge
class HistoricalBridge(BaseBridge):
    name="historical"
    def collect(self, subject, context):
        return []
