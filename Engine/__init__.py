"""Reusable Athena engines.

The Engine namespace houses deterministic computational components consumed by
Knowledge, Reasoning and Intelligence. It does not replace the locked pipeline.
"""

ENGINE_NAMESPACE_VERSION = "0.5.3.1.0"

__all__ = ["ENGINE_NAMESPACE_VERSION", "Events", "Evidence", "CrossDomain", "EventTimeline", "EventConfidence", "EventSummarization", "MultiSport"]
