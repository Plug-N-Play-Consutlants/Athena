from .base_bridge import BaseBridge
class TemporalBridge(BaseBridge):
    name="temporal"
    def collect(self, subject, context):
        return []
