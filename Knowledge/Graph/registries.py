"""Canonical entity and relationship registries for Athena's context graph."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class EntityDefinition:
    type: str
    description: str
    canonical_id_prefix: str
    required_properties: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelationshipDefinition:
    type: str
    source_types: tuple[str, ...]
    target_types: tuple[str, ...]
    description: str
    directed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EntityRegistry:
    def __init__(self, definitions: Iterable[EntityDefinition] | None = None):
        self._definitions = {d.type: d for d in (definitions or DEFAULT_ENTITIES)}

    def has(self, entity_type: str) -> bool:
        return entity_type in self._definitions

    def get(self, entity_type: str) -> EntityDefinition | None:
        return self._definitions.get(entity_type)

    def validate_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        entity_type = str(node.get("type") or "")
        definition = self.get(entity_type)
        if definition is None:
            return {"ok": False, "reason": f"Unknown entity type: {entity_type}"}
        missing = [p for p in definition.required_properties if node.get("properties", {}).get(p) in (None, "")]
        return {"ok": not missing, "missing_properties": missing, "definition": definition.to_dict()}

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in sorted(self._definitions.items())}


class RelationshipRegistry:
    def __init__(self, definitions: Iterable[RelationshipDefinition] | None = None):
        self._definitions = {d.type: d for d in (definitions or DEFAULT_RELATIONSHIPS)}

    def has(self, relationship_type: str) -> bool:
        return relationship_type in self._definitions

    def get(self, relationship_type: str) -> RelationshipDefinition | None:
        return self._definitions.get(relationship_type)

    def validate_relationship(self, relationship: Dict[str, Any], nodes_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        rel_type = str(relationship.get("type") or "")
        definition = self.get(rel_type)
        if definition is None:
            return {"ok": False, "reason": f"Unknown relationship type: {rel_type}"}
        source = nodes_by_id.get(str(relationship.get("source_id") or ""))
        target = nodes_by_id.get(str(relationship.get("target_id") or ""))
        if source is None or target is None:
            return {"ok": False, "reason": "Relationship references missing source or target node."}
        source_ok = source.get("type") in definition.source_types
        target_ok = target.get("type") in definition.target_types
        return {"ok": source_ok and target_ok, "source_type_ok": source_ok, "target_type_ok": target_ok, "definition": definition.to_dict()}

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in sorted(self._definitions.items())}


DEFAULT_ENTITIES = (
    EntityDefinition("player", "Canonical athlete/player entity.", "player"),
    EntityDefinition("team", "Canonical team entity across fantasy and public contexts.", "team"),
    EntityDefinition("league", "League/competition context entity.", "league"),
    EntityDefinition("manager", "Fantasy manager or owner entity.", "manager"),
    EntityDefinition("coach", "Coach or staff context entity.", "coach"),
    EntityDefinition("division", "Division context entity.", "division"),
    EntityDefinition("conference", "Conference context entity.", "conference"),
    EntityDefinition("achievement", "Award, milestone, honor, or accomplishment.", "achievement"),
    EntityDefinition("contract", "Contract or keeper-control context.", "contract"),
    EntityDefinition("rule", "Rule, CBA clause, or policy item.", "rule"),
    EntityDefinition("knowledge_pack", "Document-backed compact knowledge pack.", "knowledge_pack"),
    EntityDefinition("game", "Game/event entity.", "game"),
    EntityDefinition("schedule", "Schedule context entity.", "schedule"),
    EntityDefinition("api", "Future external API/provider evidence source.", "api"),
)

DEFAULT_RELATIONSHIPS = (
    RelationshipDefinition("member_of", ("team", "division"), ("league", "conference"), "Entity is a member of a larger competition grouping."),
    RelationshipDefinition("rostered_by", ("player",), ("team",), "Player is rostered by a fantasy/team entity."),
    RelationshipDefinition("plays_for", ("player",), ("team",), "Player plays for a public/professional team."),
    RelationshipDefinition("has_contract", ("player",), ("contract",), "Player has associated contract evidence."),
    RelationshipDefinition("uses_rules_from", ("league",), ("knowledge_pack",), "League interpretation can cite a document-backed knowledge pack."),
    RelationshipDefinition("governed_by", ("league", "game", "contract"), ("rule", "knowledge_pack"), "Entity is governed or explained by rule evidence."),
    RelationshipDefinition("coached_by", ("player", "team"), ("coach",), "Entity is influenced by coaching context."),
    RelationshipDefinition("earned", ("player", "team"), ("achievement",), "Entity earned an achievement."),
    RelationshipDefinition("scheduled_in", ("game", "team", "player"), ("schedule",), "Entity participates in schedule context."),
)
