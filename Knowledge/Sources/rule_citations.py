"""Rule-citation presentation bridge for Scout and reasoning outputs.

This module turns compact public-hockey knowledge-pack evidence into stable,
UI-friendly citation records. It does not interpret rules and does not read
source PDFs at runtime. It only exposes bounded evidence that has already been
registered in Athena's knowledge packs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import re

try:
    from Core.version import ATHENA_VERSION
except Exception:  # pragma: no cover
    ATHENA_VERSION = "unknown"

try:
    from Knowledge.Sources.public_hockey_retrieval import load_public_hockey_packs
except Exception:  # pragma: no cover
    load_public_hockey_packs = None  # type: ignore


def _safe_slug(value: Any) -> str:
    cleaned = re.sub(r"[^a-z0-9_\-]+", "_", str(value or "").lower()).strip("_")
    return cleaned or "unknown"


def citation_id_for_evidence(evidence: Dict[str, Any]) -> str:
    """Return a stable citation id for one knowledge-pack evidence record."""
    source_id = _safe_slug(evidence.get("source_id"))
    topic_key = _safe_slug(evidence.get("topic_key"))
    return f"rule:{source_id}:{topic_key}"


def citation_from_evidence(evidence: Dict[str, Any], base_url: str = "") -> Dict[str, Any]:
    """Convert one retrieval evidence record into a Scout-renderable citation."""
    source_id = str(evidence.get("source_id") or "").strip()
    topic_key = str(evidence.get("topic_key") or "").strip()
    params = f"source_id={_safe_slug(source_id)}&topic_key={_safe_slug(topic_key)}"
    view_url = f"/api/rules/public-hockey?{params}"
    if base_url:
        view_url = base_url.rstrip("/") + view_url
    authority_refs = [str(item) for item in evidence.get("authority_refs", []) or [] if str(item).strip()]
    return {
        "id": citation_id_for_evidence(evidence),
        "citation_type": "rule_evidence",
        "label": evidence.get("label") or topic_key or "Rule evidence",
        "topic_key": topic_key,
        "category": evidence.get("category") or "rules",
        "source_id": source_id,
        "source_title": evidence.get("source_title") or evidence.get("source_id") or "Knowledge pack",
        "authority": evidence.get("authority") or "Unknown authority",
        "authority_refs": authority_refs,
        "document_type": evidence.get("document_type"),
        "season": evidence.get("season"),
        "effective_date": evidence.get("effective_date"),
        "summary": evidence.get("summary") or "Registered rule evidence topic.",
        "citation_text": f"{evidence.get('source_title') or source_id} — {'; '.join(authority_refs or ['registered topic'])}",
        "view_url": view_url,
        "confidence_signal": evidence.get("score"),
        "source_document_present": bool(evidence.get("source_document_present")),
    }


def citations_from_evidence(evidence: Iterable[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    """Build unique rule-citation records from retrieval evidence."""
    citations: List[Dict[str, Any]] = []
    seen = set()
    for item in evidence or []:
        if not isinstance(item, dict):
            continue
        citation = citation_from_evidence(item)
        if citation["id"] in seen:
            continue
        seen.add(citation["id"])
        citations.append(citation)
        if len(citations) >= max(1, int(limit or 5)):
            break
    return citations


def _project_root(project_root: Optional[Path] = None) -> Path:
    return Path(project_root or Path.cwd())


def lookup_rule_citation(source_id: str, topic_key: str, project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return a viewable rule/provision citation record by source and topic.

    This powers Scout's rule-card drill-down endpoint. It returns only compact
    knowledge-pack metadata and a bounded topic summary.
    """
    root = _project_root(project_root)
    clean_source = _safe_slug(source_id)
    clean_topic = _safe_slug(topic_key)
    if load_public_hockey_packs is None:
        return {
            "status": "unavailable",
            "athena_version": ATHENA_VERSION,
            "message": "Public hockey knowledge-pack loader is unavailable.",
        }

    packs = load_public_hockey_packs(root, auto_build=False)
    for pack in packs:
        manifest = pack.get("manifest", {}) if isinstance(pack, dict) else {}
        pack_source = _safe_slug(manifest.get("source_id"))
        if clean_source and pack_source != clean_source:
            continue
        for entry in pack.get("entries", []) or []:
            if not isinstance(entry, dict):
                continue
            if _safe_slug(entry.get("topic_key")) != clean_topic:
                continue
            evidence = {
                "source_id": manifest.get("source_id") or entry.get("source_id"),
                "source_title": manifest.get("title") or entry.get("source_title"),
                "authority": manifest.get("authority") or entry.get("authority"),
                "document_type": manifest.get("document_type"),
                "season": manifest.get("season"),
                "effective_date": manifest.get("effective_date"),
                "topic_key": entry.get("topic_key"),
                "label": entry.get("label"),
                "category": entry.get("category"),
                "authority_refs": list(entry.get("authority_refs", []) or []),
                "keywords": list(entry.get("keywords", []) or []),
                "summary": entry.get("notes") or "Registered rule evidence topic.",
                "citation_policy": manifest.get("citation_policy") or entry.get("citation_policy"),
                "source_document_present": bool((manifest.get("source_document") or {}).get("present")),
            }
            citation = citation_from_evidence(evidence)
            return {
                "status": "available",
                "athena_version": ATHENA_VERSION,
                "citation": citation,
                "entry": entry,
                "manifest": manifest,
                "runtime_principle": "Scout displays compact rule evidence from versioned knowledge packs; it does not read source PDFs at runtime.",
                "limitations": [
                    "This is a bounded rule/provision topic citation, not a legal opinion or full cap/eligibility calculator.",
                    "Dedicated intelligence modules should perform calculations when a response requires applying the rule to live facts.",
                ],
            }

    return {
        "status": "not_found",
        "athena_version": ATHENA_VERSION,
        "source_id": source_id,
        "topic_key": topic_key,
        "message": "No matching rule/provision topic was found in compact public hockey knowledge packs.",
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(lookup_rule_citation("nhl_nhlpa_mou_2025", "ltir_lti", Path.cwd()), indent=2, ensure_ascii=False))
