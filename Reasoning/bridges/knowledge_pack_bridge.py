from .base_bridge import BaseBridge
class KnowledgePackBridge(BaseBridge):
    name="knowledge_pack"
    def collect(self, subject, context):
        return []
