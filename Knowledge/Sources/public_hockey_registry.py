"""Deterministic registry for public hockey knowledge sources.

This module does not try to answer hockey questions directly. It records which
public hockey authorities Athena knows about, what topics each source can
support, and whether the local source document is present in the workspace.

Design principle:
    Public NHL/NHLPA knowledge is shared evidence. Fantasy intelligence may
    consume it, but fantasy league settings remain a separate evidence layer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import re

try:
    from Core.version import ATHENA_VERSION
except Exception:  # pragma: no cover - safe fallback for isolated validation
    ATHENA_VERSION = "unknown"


@dataclass(frozen=True)
class KnowledgeTopic:
    """A deterministic topic pointer into an authoritative source."""

    key: str
    label: str
    category: str
    authority_refs: List[str]
    keywords: List[str] = field(default_factory=list)
    notes: str = ""

    def matches(self, query: str) -> bool:
        q = query.lower()
        haystack = " ".join([self.key, self.label, self.category, self.notes, *self.keywords]).lower()
        tokens = [t for t in re.split(r"[^a-z0-9]+", q) if t]
        return any(token in haystack for token in tokens)


@dataclass(frozen=True)
class KnowledgeSource:
    """Metadata for a public hockey authority."""

    source_id: str
    title: str
    authority: str
    document_type: str
    season: str
    effective_date: str
    expected_filenames: List[str]
    scope: List[str]
    modes: List[str]
    topics: List[KnowledgeTopic]
    citation_policy: str = "cite_source_and_section"

    def locate(self, project_root: Path) -> Dict[str, Any]:
        """Find the source PDF if the user has placed it in a supported location."""
        candidates: List[Path] = []
        search_roots = [
            project_root,
            project_root / "Knowledge" / "Sources" / "Documents",
            project_root / "Knowledge" / "Documents",
            project_root / "Raw",
            project_root / "Configuration",
        ]
        for root in search_roots:
            for filename in self.expected_filenames:
                candidates.append(root / filename)

        for path in candidates:
            if path.exists() and path.is_file():
                return {
                    "present": True,
                    "path": str(path.relative_to(project_root)) if _is_relative_to(path, project_root) else str(path),
                    "size_bytes": path.stat().st_size,
                }
        return {
            "present": False,
            "path": None,
            "size_bytes": 0,
            "expected_locations": [
                "Knowledge/Sources/Documents/<filename>",
                "Knowledge/Documents/<filename>",
                "Raw/<filename>",
                "project root/<filename>",
            ],
        }

    def to_record(self, project_root: Optional[Path] = None) -> Dict[str, Any]:
        record = asdict(self)
        record["topics"] = [asdict(topic) for topic in self.topics]
        if project_root is not None:
            record["document_status"] = self.locate(project_root)
        return record


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def default_public_hockey_sources() -> List[KnowledgeSource]:
    """Return Athena's built-in public hockey authority registry."""
    rulebook_topics = [
        KnowledgeTopic("playing_area", "Playing Area", "game_rules", ["NHL Official Rules 2025-2026 Section 1"], ["rink", "goal crease", "boards", "ice", "dimensions"]),
        KnowledgeTopic("eligible_players", "Eligible Players", "roster_rules", ["NHL Official Rules 2025-2026 Rule 5"], ["lineup", "roster", "eligible", "ineligible", "players"]),
        KnowledgeTopic("injured_players", "Injured Players", "availability_rules", ["NHL Official Rules 2025-2026 Rule 8"], ["injury", "injured", "goalkeeper", "blood", "substitution", "IR"]),
        KnowledgeTopic("penalty_types", "Types of Penalties", "game_rules", ["NHL Official Rules 2025-2026 Section 4"], ["minor", "major", "match", "misconduct", "delayed penalty", "short-handed"]),
        KnowledgeTopic("video_review", "Video Review and Coach's Challenge", "officiating_rules", ["NHL Official Rules 2025-2026 Rules 37-38"], ["review", "challenge", "goal review", "situation room"]),
        KnowledgeTopic("game_flow", "Game Flow", "game_rules", ["NHL Official Rules 2025-2026 Section 10"], ["icing", "offside", "faceoff", "overtime", "goals", "line changes"]),
    ]

    mou_topics = [
        KnowledgeTopic("salary_cap", "Salary Cap Setting", "cba_economic_rules", ["NHL/NHLPA MOU June 27 2025 Items 3-4"], ["cap", "salary cap", "upper limit", "cap ceiling", "escrow", "HRR"]),
        KnowledgeTopic("ltir_lti", "LTI / Playoff Cap Counting", "cba_roster_cap_rules", ["NHL/NHLPA MOU June 27 2025 Item 25"], ["LTIR", "LTI", "long term injured reserve", "injured reserve", "playoff cap"]),
        KnowledgeTopic("minimum_salary", "NHL Minimum Salary", "cba_contract_rules", ["NHL/NHLPA MOU June 27 2025 Item 26"], ["minimum salary", "league minimum", "contract"]),
        KnowledgeTopic("performance_bonus_injured_veterans", "Performance Bonus Eligibility for Injured Veterans", "cba_contract_rules", ["NHL/NHLPA MOU June 27 2025 Item 27"], ["bonus", "performance bonus", "injured veteran", "35+"]),
        KnowledgeTopic("no_trade_lists", "Filing of No-Trade Lists", "cba_contract_rules", ["NHL/NHLPA MOU June 27 2025 Item 34"], ["no trade", "no-trade", "trade list", "NTC", "NMC", "clause"]),
        KnowledgeTopic("salary_retention", "Second Retained Salary Transaction", "cba_transaction_rules", ["NHL/NHLPA MOU June 27 2025 Item 35"], ["salary retention", "retained salary", "retention", "trade"]),
        KnowledgeTopic("contract_variability", "Contract Variability", "cba_contract_rules", ["NHL/NHLPA MOU June 27 2025 Item 37"], ["contract variability", "salary variance", "front-loaded", "back-loaded"]),
        KnowledgeTopic("contract_term_limits", "Limitation on Contract Term", "cba_contract_rules", ["NHL/NHLPA MOU June 27 2025 Item 38"], ["contract term", "extension", "sign and trade", "seven years", "eight years"]),
        KnowledgeTopic("four_recall_rule", "Four Recall Rule", "cba_roster_rules", ["NHL/NHLPA MOU June 27 2025 Item 16"], ["recall", "emergency recall", "four recall", "active roster"]),
        KnowledgeTopic("waiver_system_access", "NHLPA User Access to Waiver System", "cba_transaction_rules", ["NHL/NHLPA MOU June 27 2025 Item 82"], ["waiver", "waivers", "claim", "notification"]),
        KnowledgeTopic("supplementary_discipline", "Supplementary Discipline", "cba_discipline_rules", ["NHL/NHLPA MOU June 27 2025 Item 85"], ["discipline", "fine", "suspension", "maximum fine"]),
    ]

    return [
        KnowledgeSource(
            source_id="nhl_official_rules_2025_2026",
            title="National Hockey League Official Rules 2025-2026",
            authority="National Hockey League",
            document_type="official_rulebook",
            season="2025-2026",
            effective_date="2025-2026 season",
            expected_filenames=["nhl.pdf", "25_26_OfficialRules.pdf", "NHL_Official_Rules_2025_2026.pdf"],
            scope=["game_rules", "officiating", "equipment", "penalties", "game_flow", "roster_lineup_rules"],
            modes=["public_sports", "fantasy_league"],
            topics=rulebook_topics,
        ),
        KnowledgeSource(
            source_id="nhl_nhlpa_mou_2025_06_27",
            title="NHL/NHLPA Memorandum of Understanding - June 27, 2025",
            authority="National Hockey League / National Hockey League Players' Association",
            document_type="cba_mou",
            season="2026-2030 framework",
            effective_date="2026-09-16 with specified earlier/later provisions",
            expected_filenames=["NHLPA-NHL-MOU-June-27-2025.pdf", "NHL_NHLPA_MOU_June_27_2025.pdf"],
            scope=["salary_cap", "cba", "contracts", "waivers", "recalls", "ltir", "discipline", "player_benefits"],
            modes=["public_sports", "fantasy_league"],
            topics=mou_topics,
        ),
    ]


def find_public_hockey_topics(query: str, sources: Optional[Iterable[KnowledgeSource]] = None) -> List[Dict[str, Any]]:
    """Find deterministic source/topic candidates for a question or phrase."""
    results: List[Dict[str, Any]] = []
    for source in sources or default_public_hockey_sources():
        for topic in source.topics:
            if topic.matches(query):
                results.append({
                    "source_id": source.source_id,
                    "title": source.title,
                    "authority": source.authority,
                    "document_type": source.document_type,
                    "topic": asdict(topic),
                })
    return results


def build_public_hockey_capability_report(project_root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(project_root or Path.cwd())
    sources = default_public_hockey_sources()
    records = [source.to_record(root) for source in sources]
    topic_count = sum(len(source.topics) for source in sources)
    present_count = sum(1 for record in records if record.get("document_status", {}).get("present"))
    return {
        "athena_version": ATHENA_VERSION,
        "knowledge_domain": "public_hockey",
        "status": "available" if present_count else "registered_metadata_only",
        "source_count": len(records),
        "sources_present": present_count,
        "topic_count": topic_count,
        "shared_modes": ["public_sports", "fantasy_league"],
        "principle": "Public NHL/NHLPA knowledge is shared evidence available to public and fantasy intelligence layers.",
        "sources": records,
    }


def write_public_hockey_registry_outputs(project_root: Optional[Path] = None) -> Dict[str, str]:
    root = Path(project_root or Path.cwd())
    report = build_public_hockey_capability_report(root)
    output_dir = root / "Output"
    reports_dir = root / "Reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "public_hockey_knowledge_registry.json"
    txt_path = reports_dir / "public_hockey_knowledge_registry_report.txt"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "Public Hockey Knowledge Registry",
        "================================",
        f"Athena: {report['athena_version']}",
        f"Status: {report['status']}",
        f"Sources: {report['source_count']}",
        f"Sources present: {report['sources_present']}",
        f"Topics: {report['topic_count']}",
        "Shared modes: public_sports, fantasy_league",
        "",
    ]
    for source in report["sources"]:
        status = source.get("document_status", {})
        marker = "✓" if status.get("present") else "—"
        lines.append(f"{marker} {source['source_id']} — {source['title']}")
        lines.append(f"  Authority: {source['authority']}")
        lines.append(f"  Type: {source['document_type']}")
        lines.append(f"  Season: {source['season']}")
        lines.append(f"  Document: {status.get('path') or 'not found locally'}")
        lines.append("  Topics:")
        for topic in source["topics"]:
            refs = "; ".join(topic["authority_refs"])
            lines.append(f"    - {topic['key']}: {topic['label']} ({refs})")
        lines.append("")
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "text": str(txt_path)}


if __name__ == "__main__":  # pragma: no cover
    paths = write_public_hockey_registry_outputs(Path.cwd())
    print(json.dumps(paths, indent=2))
