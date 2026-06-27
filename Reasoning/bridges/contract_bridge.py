from .base_bridge import BaseBridge
class ContractBridge(BaseBridge):
    name="contract"
    def collect(self, subject, context):
        return []
