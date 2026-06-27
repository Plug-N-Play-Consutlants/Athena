from dataclasses import dataclass, field
@dataclass
class EvidenceBundle:
    graph:list=field(default_factory=list)
    historical:list=field(default_factory=list)
    temporal:list=field(default_factory=list)
    rules:list=field(default_factory=list)
