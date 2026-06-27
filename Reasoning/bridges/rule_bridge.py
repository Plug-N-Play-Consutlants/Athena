from .base_bridge import BaseBridge
class RuleBridge(BaseBridge):
    name="rule"
    def collect(self, subject, context):
        return []
