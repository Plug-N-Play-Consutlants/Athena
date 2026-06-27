from .base_bridge import BaseBridge
class GraphBridge(BaseBridge):
    name="graph"
    def collect(self, subject, context):
        return []
