"""Epic 4D.1 temporal intelligence foundation for Athena.

Historical Intelligence makes time a first-class dimension. This module builds a
canonical timeline from existing Knowledge outputs and can project those temporal
events back into the context graph without changing objective evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import OUTPUT_DIR
from Core.version import ATHENA_VERSION
from Knowledge.Graph.builder import build_canonical_context_graph
from Knowledge.Graph.canonical_graph import CanonicalContextGraph, GraphNode, GraphRelationship, utc_now_iso
from Knowledge.Graph.evidence_chain import load_graph

TEMPORAL_VERSION = "4D.1-temporal-foundation"
TIMELINE_FILE = "temporal_evidence_timeline.json"
TIMELINE_SUMMARY_FILE = "temporal_evidence_summary.json"
TEMPORAL_GRAPH_FILE = "canonical_context_graph_temporal.json"

EVENT_TYPE_WEIGHTS: Dict[str, float] = {
    "contract_snapshot": 0.92,
    "transaction": 0.88,
    "asset_movement": 0.86,
    "production_snapshot": 0.82,
    "knowledge_pack_snapshot": 0.78,
}


def _slug(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def _records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("records", "players", "teams", "packs", "sources", "transactions"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def _parse_datetime(value: Any) -> Optional[str]:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, (int, float)):
        # Treat bare years as season anchors rather than unix timestamps.
        if 1800 <= int(value) <= 2200:
            return f"{int(value):04d}-01-01T00:00:00+00:00"
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}T00:00:00+00:00"
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-01-01T00:00:00+00:00"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def _season_to_anchor(value: Any) -> Optional[str]:
    if value in (None, "", [], {}):
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-10-01T00:00:00+00:00"
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-10-01T00:00:00+00:00"
    return _parse_datetime(text)


@dataclass
class TemporalEvent:
    id: str
    type: str
    label: str
    occurred_at: Optional[str]
    subject_id: str
    source: str
    confidence: float = 0.75
    evidence_type: str = "temporal"
    related_ids: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _confidence(value: Any, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0.0, min(1.0, numeric))


def _player_id(value: Any) -> str:
    return f"player:{_slug(value)}"


def _transaction_events(rows: Iterable[Dict[str, Any]]) -> List[TemporalEvent]:
    events: List[TemporalEvent] = []
    for tx in rows:
        tx_id = str(tx.get("transaction_id") or tx.get("id") or _slug(tx.get("summary")))
        occurred_at = _parse_datetime(tx.get("timestamp") or tx.get("created_at") or tx.get("date"))
        assets = tx.get("assets") if isinstance(tx.get("assets"), list) else []
        participants = tx.get("participants") if isinstance(tx.get("participants"), list) else []
        subject = f"transaction:{_slug(tx_id)}"
        related: List[str] = []
        for asset in assets:
            if isinstance(asset, dict) and (asset.get("asset_id") or asset.get("player", {}).get("fantrax_scorer_id")):
                related.append(_player_id(asset.get("asset_id") or asset.get("player", {}).get("fantrax_scorer_id")))
        events.append(TemporalEvent(
            id=f"event:transaction:{_slug(tx_id)}",
            type="transaction",
            label=str(tx.get("summary") or tx.get("transaction_type") or tx_id),
            occurred_at=occurred_at,
            subject_id=subject,
            source="transaction_master",
            confidence=0.88 if occurred_at else 0.7,
            related_ids=sorted(set(related)),
            properties={
                "transaction_id": tx_id,
                "transaction_type": tx.get("transaction_type"),
                "status": tx.get("status"),
                "season_week": tx.get("season_week"),
                "fee_total": tx.get("fee_total"),
                "participants": participants,
                "summary": tx.get("summary"),
            },
        ))
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            asset_id = asset.get("asset_id") or asset.get("player", {}).get("fantrax_scorer_id")
            if not asset_id:
                continue
            movement = str(asset.get("movement") or "movement").lower()
            player_id = _player_id(asset_id)
            team_name = asset.get("movement_context", {}).get("team_name") if isinstance(asset.get("movement_context"), dict) else None
            related_ids = [f"event:transaction:{_slug(tx_id)}"]
            if team_name:
                related_ids.append(f"team:{_slug(team_name)}")
            events.append(TemporalEvent(
                id=f"event:asset_movement:{_slug(tx_id)}:{_slug(asset_id)}:{_slug(movement)}",
                type="asset_movement",
                label=f"{asset.get('asset_name') or asset_id} {movement}",
                occurred_at=occurred_at,
                subject_id=player_id,
                source="transaction_master",
                confidence=0.86 if occurred_at else 0.68,
                related_ids=related_ids,
                properties={
                    "transaction_id": tx_id,
                    "asset_id": asset_id,
                    "asset_name": asset.get("asset_name"),
                    "movement": movement,
                    "team_name": team_name,
                    "claim_type": asset.get("movement_context", {}).get("claim_type") if isinstance(asset.get("movement_context"), dict) else None,
                },
            ))
    return events


def _contract_events(rows: Iterable[Dict[str, Any]]) -> List[TemporalEvent]:
    events: List[TemporalEvent] = []
    for contract in rows:
        player_key = contract.get("fantrax_player_id") or contract.get("player_id") or contract.get("player_name")
        if not player_key:
            continue
        expiry = contract.get("expiry_year") or contract.get("contract_expiry_year")
        occurred_at = _parse_datetime(contract.get("fetched_at")) or utc_now_iso()
        cid = f"contract:{_slug(player_key)}:{_slug(expiry)}"
        events.append(TemporalEvent(
            id=f"event:contract_snapshot:{_slug(player_key)}:{_slug(expiry)}",
            type="contract_snapshot",
            label=f"{contract.get('player_name') or player_key} contract snapshot",
            occurred_at=occurred_at,
            subject_id=_player_id(player_key),
            source="player_contracts",
            confidence=_confidence(contract.get("confidence"), 0.9),
            related_ids=[cid],
            properties={
                "expiry_year": expiry,
                "years_remaining": contract.get("years_remaining") or contract.get("contract_years_remaining"),
                "contract_status": contract.get("contract_status"),
                "fantasy_team": contract.get("fantasy_team"),
                "source_live": contract.get("source_live"),
            },
        ))
    return events


def _production_events(rows: Iterable[Dict[str, Any]]) -> List[TemporalEvent]:
    events: List[TemporalEvent] = []
    for row in rows:
        player_key = row.get("player_id") or row.get("fantrax_player_id") or row.get("player_name")
        if not player_key:
            continue
        season = row.get("season") or row.get("season_id")
        occurred_at = _season_to_anchor(season)
        events.append(TemporalEvent(
            id=f"event:production_snapshot:{_slug(player_key)}:{_slug(season)}",
            type="production_snapshot",
            label=f"{row.get('player_name') or player_key} production {season or 'snapshot'}",
            occurred_at=occurred_at,
            subject_id=_player_id(player_key),
            source="player_production",
            confidence=_confidence(row.get("match_confidence") or row.get("confidence"), 0.82),
            related_ids=[],
            properties={
                "season": season,
                "games_played": row.get("games_played"),
                "goals": row.get("goals"),
                "assists": row.get("assists"),
                "points": row.get("points"),
                "points_per_game": row.get("points_per_game"),
                "production_rank": row.get("production_rank"),
                "production_percentile": row.get("production_percentile"),
                "source_status": row.get("source_status"),
            },
        ))
    return events


def _knowledge_pack_events(rows: Iterable[Dict[str, Any]]) -> List[TemporalEvent]:
    events: List[TemporalEvent] = []
    for pack in rows:
        source_id = str(pack.get("source_id") or pack.get("pack_root") or "knowledge_pack")
        occurred_at = _parse_datetime(pack.get("generated_at") or pack.get("updated_at")) or utc_now_iso()
        kid = f"knowledge_pack:{_slug(source_id)}"
        events.append(TemporalEvent(
            id=f"event:knowledge_pack_snapshot:{_slug(source_id)}",
            type="knowledge_pack_snapshot",
            label=f"{source_id} knowledge pack snapshot",
            occurred_at=occurred_at,
            subject_id=kid,
            source="public_hockey_knowledge_packs",
            confidence=0.9 if pack.get("source_document_present") else 0.65,
            related_ids=[kid],
            properties={
                "source_id": source_id,
                "source_document_present": pack.get("source_document_present"),
                "pack_root": pack.get("pack_root"),
            },
        ))
    return events


def _sort_events(events: List[TemporalEvent]) -> List[TemporalEvent]:
    return sorted(events, key=lambda e: (e.occurred_at or "9999-12-31T23:59:59+00:00", e.type, e.id))


def build_temporal_evidence(project_root: Path | None = None) -> Dict[str, Any]:
    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"
    events: List[TemporalEvent] = []
    events.extend(_contract_events(_records(read_optional_json(output_dir / "player_contracts.json"))))
    tx_rows = _records(read_optional_json(output_dir / "transaction_master.json"))
    hist_rows = _records(read_optional_json(output_dir / "transaction_history.json"))
    combined_tx: Dict[str, Dict[str, Any]] = {}
    for row in [*tx_rows, *hist_rows]:
        combined_tx[str(row.get("transaction_id") or id(row))] = row
    events.extend(_transaction_events(combined_tx.values()))
    events.extend(_production_events(_records(read_optional_json(output_dir / "player_production.json"))))
    events.extend(_knowledge_pack_events(_records(read_optional_json(output_dir / "public_hockey_knowledge_packs.json"))))

    events = _sort_events(events)
    by_type: Dict[str, int] = {}
    by_subject: Dict[str, int] = {}
    missing_dates = 0
    for event in events:
        by_type[event.type] = by_type.get(event.type, 0) + 1
        by_subject[event.subject_id] = by_subject.get(event.subject_id, 0) + 1
        if not event.occurred_at:
            missing_dates += 1
    timeline = {
        "athena_version": ATHENA_VERSION,
        "temporal_version": TEMPORAL_VERSION,
        "generated_at": utc_now_iso(),
        "principle": "time_is_first_class_contextual_evidence",
        "event_count": len(events),
        "events": [event.to_dict() for event in events],
    }
    summary = {
        "athena_version": ATHENA_VERSION,
        "temporal_version": TEMPORAL_VERSION,
        "status": "ready" if events else "empty",
        "event_count": len(events),
        "event_types": by_type,
        "subjects_with_events": len(by_subject),
        "missing_event_dates": missing_dates,
        "earliest_event": next((e.occurred_at for e in events if e.occurred_at), None),
        "latest_event": next((e.occurred_at for e in reversed(events) if e.occurred_at), None),
        "timeline_file": str(output_dir / TIMELINE_FILE),
    }
    write_json(output_dir / TIMELINE_FILE, timeline)
    write_json(output_dir / TIMELINE_SUMMARY_FILE, summary)
    return {"timeline": timeline, "summary": summary}


def _relationship_id(source_id: str, rel_type: str, target_id: str) -> str:
    return f"rel:{_slug(source_id)}:{_slug(rel_type)}:{_slug(target_id)}"


def enrich_graph_with_temporal_events(project_root: Path | None = None) -> Dict[str, Any]:
    root = Path(project_root) if project_root is not None else None
    output_dir = OUTPUT_DIR if root is None else root / "Output"
    # Rebuild the structural graph first so temporal enrichment starts from the verified canonical state.
    build_canonical_context_graph(root)
    timeline_payload = build_temporal_evidence(root)
    graph = load_graph(root)

    for event in timeline_payload["timeline"].get("events", []):
        event_id = event["id"]
        graph.add_node(GraphNode(
            id=event_id,
            type="temporal_event",
            label=event.get("label") or event_id,
            evidence_type="temporal",
            source=event.get("source") or "temporal_evidence",
            confidence=_confidence(event.get("confidence"), EVENT_TYPE_WEIGHTS.get(event.get("type"), 0.75)),
            properties={
                "event_type": event.get("type"),
                "occurred_at": event.get("occurred_at"),
                "subject_id": event.get("subject_id"),
                **(event.get("properties") if isinstance(event.get("properties"), dict) else {}),
            },
        ))
        subject_id = event.get("subject_id")
        if subject_id in graph.nodes:
            graph.add_relationship(GraphRelationship(
                id=_relationship_id(subject_id, "has_temporal_event", event_id),
                source_id=subject_id,
                target_id=event_id,
                type="has_temporal_event",
                source="temporal_evidence",
                confidence=_confidence(event.get("confidence"), 0.75),
                properties={"event_type": event.get("type"), "occurred_at": event.get("occurred_at")},
            ))
        for related_id in event.get("related_ids", []) if isinstance(event.get("related_ids"), list) else []:
            if related_id in graph.nodes:
                graph.add_relationship(GraphRelationship(
                    id=_relationship_id(event_id, "temporally_related_to", related_id),
                    source_id=event_id,
                    target_id=related_id,
                    type="temporally_related_to",
                    source="temporal_evidence",
                    confidence=_confidence(event.get("confidence"), 0.75),
                    properties={"event_type": event.get("type"), "occurred_at": event.get("occurred_at")},
                ))

    payload = graph.to_dict()
    payload["metadata"] = {
        **payload.get("metadata", {}),
        "athena_version": ATHENA_VERSION,
        "temporal_version": TEMPORAL_VERSION,
        "graph_temporal_enrichment": "4D.1",
        "generated_at": utc_now_iso(),
    }
    write_json(output_dir / TEMPORAL_GRAPH_FILE, payload)
    summary = {
        "athena_version": ATHENA_VERSION,
        "temporal_version": TEMPORAL_VERSION,
        "status": "ready" if payload.get("node_count", 0) else "empty",
        "node_count": payload.get("node_count", 0),
        "relationship_count": payload.get("relationship_count", 0),
        "temporal_event_nodes": sum(1 for n in payload.get("nodes", []) if n.get("type") == "temporal_event"),
        "has_temporal_event_relationships": sum(1 for r in payload.get("relationships", []) if r.get("type") == "has_temporal_event"),
        "temporally_related_relationships": sum(1 for r in payload.get("relationships", []) if r.get("type") == "temporally_related_to"),
        "temporal_graph_file": str(output_dir / TEMPORAL_GRAPH_FILE),
    }
    write_json(output_dir / "canonical_context_graph_temporal_summary.json", summary)
    return {"graph": payload, "summary": summary, "timeline": timeline_payload["timeline"]}


def timeline_for_entity(entity_id: str, *, project_root: Path | None = None, limit: int = 20) -> Dict[str, Any]:
    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"
    payload = read_optional_json(output_dir / TIMELINE_FILE)
    if not isinstance(payload, dict):
        payload = build_temporal_evidence(project_root)["timeline"]
    events = [e for e in payload.get("events", []) if isinstance(e, dict) and (e.get("subject_id") == entity_id or entity_id in (e.get("related_ids") or []))]
    events = sorted(events, key=lambda e: (e.get("occurred_at") or "9999-12-31T23:59:59+00:00", e.get("id") or ""))[: max(1, int(limit or 20))]
    return {
        "status": "available" if events else "empty",
        "athena_version": ATHENA_VERSION,
        "temporal_version": TEMPORAL_VERSION,
        "entity_id": entity_id,
        "event_count": len(events),
        "events": events,
        "known_gaps": [] if events else ["No temporal events are currently connected to the requested entity."],
    }


if __name__ == "__main__":
    result = enrich_graph_with_temporal_events()
    print("Historical Intelligence Temporal Foundation")
    print("===========================================")
    print(f"Status: {result['summary']['status']}")
    print(f"Temporal events: {result['summary']['temporal_event_nodes']}")
    print(f"Graph nodes: {result['summary']['node_count']}")
    print(f"Graph relationships: {result['summary']['relationship_count']}")
