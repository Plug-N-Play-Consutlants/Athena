from enum import Enum
class TrendValue(str,Enum):
    ASCENDING="ascending"
    STABLE="stable"
    DECLINING="declining"
    UNKNOWN="unknown"
