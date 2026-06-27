"""Compact public hockey knowledge-pack builder.

The source PDFs are acquisition artifacts. Athena runtime should consume compact,
versioned JSON knowledge packs with deterministic metadata, topic indexes, and
source pointers, not large PDFs.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import re

try:
    from Core.version import ATHENA_VERSION
except Exception:  # pragma: no cover
    ATHENA_VERSION = "unknown"

from Knowledge.Sources.public_hockey_registry import (
    KnowledgeSource,
    build_public_hockey_capability_report,
    default_public_hockey_sources,
)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "unknown"


def _pack_root_for_source(project_root: Path, source: KnowledgeSource) -> Path:
    if source.document_type == "official_rulebook":
        return project_root / "Knowledge" / "Packs" / "NHL" / "rulebook" / _slug(source.season.replace("-", "_"))
    if source.document_type == "cba_mou":
        # Keep this stable and human-readable for the June 2025 MOU.
        return project_root / "Knowledge" / "Packs" / "NHL" / "cba" / "2025_mou"
    return project_root / "Knowledge" / "Packs" / "NHL" / _slug(source.document_type) / _slug(source.season)


def _file_fingerprint(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists() or not path.is_file():
        return {"present": False, "path": None, "size_bytes": 0, "sha256": None}
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "present": True,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def _resolve_document_path(project_root: Path, source: KnowledgeSource) -> Optional[Path]:
    status = source.locate(project_root)
    if not status.get("present") or not status.get("path"):
        return None
    candidate = Path(status["path"])
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate if candidate.exists() else None


def _topic_record(source: KnowledgeSource, topic: Any) -> Dict[str, Any]:
    return {
        "topic_key": topic.key,
        "label": topic.label,
        "category": topic.category,
        "source_id": source.source_id,
        "source_title": source.title,
        "authority": source.authority,
        "authority_refs": list(topic.authority_refs),
        "keywords": list(topic.keywords),
        "notes": topic.notes,
        "citation_policy": source.citation_policy,
    }


def build_knowledge_pack_for_source(project_root: Optional[Path], source: KnowledgeSource) -> Dict[str, Any]:
    """Build compact in-memory pack data for one authoritative source."""
    root = Path(project_root or Path.cwd())
    source_path = _resolve_document_path(root, source)
    fingerprint = _file_fingerprint(source_path)
    if fingerprint["path"]:
        try:
            fingerprint["path"] = str(Path(fingerprint["path"]).resolve().relative_to(root.resolve()))
        except Exception:
            pass

    topics = [_topic_record(source, topic) for topic in source.topics]
    topic_index: Dict[str, List[str]] = {}
    for topic in topics:
        for token in [topic["topic_key"], topic["label"], topic["category"], *topic["keywords"]]:
            for part in re.split(r"[^a-z0-9]+", str(token).lower()):
                if part:
                    topic_index.setdefault(part, [])
                    if topic["topic_key"] not in topic_index[part]:
                        topic_index[part].append(topic["topic_key"])

    manifest = {
        "pack_schema": "athena.knowledge_pack.v1",
        "athena_version": ATHENA_VERSION,
        "source_id": source.source_id,
        "title": source.title,
        "authority": source.authority,
        "document_type": source.document_type,
        "season": source.season,
        "effective_date": source.effective_date,
        "scope": list(source.scope),
        "modes": list(source.modes),
        "citation_policy": source.citation_policy,
        "source_document": fingerprint,
        "topic_count": len(topics),
        "runtime_principle": "Athena reasons from compact, versioned knowledge packs generated from authoritative sources, not from source PDFs at runtime.",
    }

    if source.document_type == "official_rulebook":
        body_key = "rules"
    elif source.document_type == "cba_mou":
        body_key = "provisions"
    else:
        body_key = "entries"

    return {
        "manifest": manifest,
        body_key: topics,
        "topic_index": topic_index,
        "pack_root": str(_pack_root_for_source(root, source)),
        "body_filename": f"{body_key}.json",
    }


def write_knowledge_pack(project_root: Optional[Path], source: KnowledgeSource) -> Dict[str, Any]:
    root = Path(project_root or Path.cwd())
    pack = build_knowledge_pack_for_source(root, source)
    pack_root = Path(pack["pack_root"])
    pack_root.mkdir(parents=True, exist_ok=True)

    manifest_path = pack_root / "manifest.json"
    body_path = pack_root / pack["body_filename"]
    index_path = pack_root / "topic_index.json"

    manifest_path.write_text(json.dumps(pack["manifest"], indent=2, ensure_ascii=False), encoding="utf-8")
    body_data = pack.get("rules") or pack.get("provisions") or pack.get("entries") or []
    body_path.write_text(json.dumps(body_data, indent=2, ensure_ascii=False), encoding="utf-8")
    index_path.write_text(json.dumps(pack["topic_index"], indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "source_id": source.source_id,
        "pack_root": str(pack_root),
        "manifest": str(manifest_path),
        "body": str(body_path),
        "topic_index": str(index_path),
        "source_document_present": bool(pack["manifest"]["source_document"].get("present")),
        "topic_count": pack["manifest"]["topic_count"],
    }


def build_public_hockey_knowledge_packs(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Build all compact public hockey knowledge packs and write summary outputs."""
    root = Path(project_root or Path.cwd())
    outputs = [write_knowledge_pack(root, source) for source in default_public_hockey_sources()]
    packs_present = sum(1 for item in outputs if Path(item["manifest"]).exists() and Path(item["topic_index"]).exists())
    document_backed = sum(1 for item in outputs if item["source_document_present"])

    summary = {
        "athena_version": ATHENA_VERSION,
        "knowledge_domain": "public_hockey",
        "status": "available" if packs_present == len(outputs) else "partial",
        "pack_count": len(outputs),
        "packs_present": packs_present,
        "document_backed_packs": document_backed,
        "runtime_principle": "Source PDFs are staging artifacts. Runtime uses compact JSON packs under Knowledge/Packs.",
        "packs": outputs,
    }

    output_dir = root / "Output"
    reports_dir = root / "Reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_json = output_dir / "public_hockey_knowledge_packs.json"
    summary_txt = reports_dir / "public_hockey_knowledge_packs_report.txt"
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "Public Hockey Knowledge Packs",
        "=============================",
        f"Athena: {summary['athena_version']}",
        f"Status: {summary['status']}",
        f"Packs: {summary['pack_count']}",
        f"Document-backed packs: {summary['document_backed_packs']}",
        "Runtime: compact JSON knowledge packs",
        "Source PDFs: staging artifacts only",
        "",
    ]
    for item in outputs:
        marker = "✓" if item["source_document_present"] else "—"
        lines.append(f"{marker} {item['source_id']}")
        lines.append(f"  Pack: {Path(item['pack_root']).name}")
        lines.append(f"  Topics: {item['topic_count']}")
        lines.append(f"  Manifest: {item['manifest']}")
        lines.append(f"  Index: {item['topic_index']}")
        lines.append("")
    summary_txt.write_text("\n".join(lines), encoding="utf-8")
    summary["summary_outputs"] = {"json": str(summary_json), "text": str(summary_txt)}
    return summary


def load_public_hockey_pack_summary(project_root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(project_root or Path.cwd())
    path = root / "Output" / "public_hockey_knowledge_packs.json"
    if not path.exists():
        return {"status": "missing", "pack_count": 0, "packs_present": 0, "document_backed_packs": 0, "packs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def public_hockey_pack_status(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return registry + pack status for Doctor/debug export integrations."""
    root = Path(project_root or Path.cwd())
    registry = build_public_hockey_capability_report(root)
    packs = load_public_hockey_pack_summary(root)
    return {
        "athena_version": ATHENA_VERSION,
        "registry_status": registry.get("status"),
        "source_count": registry.get("source_count", 0),
        "sources_present": registry.get("sources_present", 0),
        "pack_status": packs.get("status"),
        "pack_count": packs.get("pack_count", 0),
        "packs_present": packs.get("packs_present", 0),
        "document_backed_packs": packs.get("document_backed_packs", 0),
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(build_public_hockey_knowledge_packs(Path.cwd()), indent=2, ensure_ascii=False))
