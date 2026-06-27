"""Query compact public hockey knowledge packs from Spyder or CLI."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Sources.public_hockey_retrieval import (  # noqa: E402
    retrieve_public_hockey_knowledge,
    write_public_hockey_retrieval_report,
)


def main(query: str = "LTIR waivers icing", mode: str = "public_sports") -> int:
    result = retrieve_public_hockey_knowledge(query, ROOT, mode=mode, limit=5, auto_build=False)
    paths = write_public_hockey_retrieval_report(query, ROOT, mode=mode)
    print("Public Hockey Knowledge Retrieval")
    print("=================================")
    print(f"Status: {result['status']}")
    print(f"Query: {result['query']}")
    print(f"Mode: {result['mode']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Packs checked: {result['packs_checked']}")
    print(f"Evidence: {result['evidence_count']}")
    for item in result.get("evidence", []):
        refs = "; ".join(item.get("authority_refs", []) or [])
        print(f"✓ {item['label']} — {item['source_id']} ({refs})")
    print(f"JSON: {paths['json']}")
    print(f"Text: {paths['text']}")
    return 0


if __name__ == "__main__":
    query_arg = " ".join(sys.argv[1:]).strip() or "LTIR waivers icing"
    raise SystemExit(main(query_arg))
