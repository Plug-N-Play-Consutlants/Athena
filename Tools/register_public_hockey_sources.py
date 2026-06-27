"""Register public hockey authority metadata and write registry outputs."""
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Sources.public_hockey_registry import (  # noqa: E402
    build_public_hockey_capability_report,
    write_public_hockey_registry_outputs,
)


def main() -> int:
    paths = write_public_hockey_registry_outputs(ROOT)
    report = build_public_hockey_capability_report(ROOT)
    print("Public Hockey Knowledge Source Registry")
    print("=======================================")
    print(f"Status: {report['status']}")
    print(f"Sources: {report['source_count']}")
    print(f"Sources present: {report['sources_present']}")
    print(f"Topics: {report['topic_count']}")
    print(f"JSON: {paths['json']}")
    print(f"Text: {paths['text']}")
    if report.get("sources_present") == report.get("source_count"):
        print("\nAll registered source documents are present. Run Tools/build_public_hockey_knowledge_packs.py to generate compact runtime packs.")
    else:
        print("\nPlace source PDFs in Knowledge/Sources/Documents/ to make the registry document-backed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
