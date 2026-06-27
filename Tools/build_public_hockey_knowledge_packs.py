"""Build compact public hockey knowledge packs from staged source documents."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Sources.public_hockey_packs import build_public_hockey_knowledge_packs  # noqa: E402


def main() -> int:
    summary = build_public_hockey_knowledge_packs(ROOT)
    print("Public Hockey Knowledge Pack Builder")
    print("====================================")
    print(f"Status: {summary['status']}")
    print(f"Packs: {summary['pack_count']}")
    print(f"Packs present: {summary['packs_present']}")
    print(f"Document-backed packs: {summary['document_backed_packs']}")
    for pack in summary["packs"]:
        marker = "✓" if pack["source_document_present"] else "—"
        print(f"{marker} {pack['source_id']}: topics={pack['topic_count']}")
    outputs = summary.get("summary_outputs", {})
    if outputs:
        print(f"JSON: {outputs.get('json')}")
        print(f"Text: {outputs.get('text')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
