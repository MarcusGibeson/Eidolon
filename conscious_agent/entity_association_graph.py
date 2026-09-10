from __future__ import annotations

"""Provider-neutral entity identity and typed association foundation."""

from collections import deque
from dataclasses import asdict, dataclass, replace
import hashlib
import re
from typing import Any, Iterable


CONTRACT_VERSION = "v1500.7"
MAX_ENTITIES = 256
MAX_EDGES = 512
MAX_ALIASES_PER_ENTITY = 12
MAX_PATH_DEPTH = 3
_PREDICATE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _compact(value: Any, limit: int = 120) -> str:
    return " ".join(str(value or "").split()).strip(" .,!?:;")[:limit]


def _token(value: Any) -> str:
    return _compact(value).casefold()


def _digest(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(_compact(part, 1000) for part in parts).encode("utf-8")).hexdigest()


def _entity_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _token(label)).strip("-")[:48] or "entity"
    return f"entity:{slug}:{_digest(label)[:12]}"


def _normalize_predicate(value: Any) -> str:
    raw = " ".join(str(value or "").split()).casefold()
    if not re.fullmatch(r"[a-z][a-z0-9_ -]{0,63}", raw):
        raise ValueError("association predicate must be lower snake case compatible")
    relation = raw.replace("-", "_").replace(" ", "_")
    if not _PREDICATE.fullmatch(relation):
        raise ValueError("association predicate must be lower snake case")
    return relation


@dataclass(frozen=True)
class EntityNode:
    entity_id: str
    label: str
    entity_kind: str
    aliases: tuple[str, ...]
    provenance_class: str
    evidence_digest: str


@dataclass(frozen=True)
class AssociationEdge:
    edge_id: str
    subject_id: str
    predicate: str
    object_id: str
    provenance_class: str
    evidence_digest: str
    confidence: float
    source_offset: int
    explicit_correction: bool
    active: bool = True
    supersedes_edge_id: str = ""


@dataclass(frozen=True)
class EntityResolution:
    status: str
    query_digest: str
    entity_ids: tuple[str, ...] = ()
    resolved_from_alias: bool = False

    @property
    def entity_id(self) -> str:
        return self.entity_ids[0] if self.status == "matched" and len(self.entity_ids) == 1 else ""


@dataclass(frozen=True)
class AssociationPath:
    edge_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    predicates: tuple[str, ...]

    @property
    def depth(self) -> int:
        return len(self.edge_ids)


class EntityAssociationGraph:
    """Bounded graph with explicit provenance and correction-aware edge state."""

    def __init__(self) -> None:
        self._entities: dict[str, EntityNode] = {}
        self._edges: list[AssociationEdge] = []
        self._alias_index: dict[str, set[str]] = {}

    def add_entity(
        self,
        label: str,
        *,
        entity_kind: str = "concept",
        aliases: Iterable[str] = (),
        provenance_class: str = "user_authored",
        evidence_ref: str = "",
    ) -> EntityNode:
        clean_label = _compact(label)
        if not clean_label:
            raise ValueError("entity label is required")
        indexed = tuple(sorted(self._alias_index.get(_token(clean_label), set())))
        if len(indexed) == 1:
            existing = self._entities[indexed[0]]
            merged = tuple(dict.fromkeys((*existing.aliases, *(
                value for value in (_compact(alias) for alias in aliases)
                if value and _token(value) != _token(existing.label)
            ))))[:MAX_ALIASES_PER_ENTITY]
            if merged != existing.aliases:
                existing = replace(existing, aliases=merged)
                self._entities[existing.entity_id] = existing
                self._index_entity(existing)
            return existing
        entity_id = _entity_id(clean_label)
        alias_values = tuple(dict.fromkeys(
            value for value in (_compact(alias) for alias in aliases)
            if value and _token(value) != _token(clean_label)
        ))[:MAX_ALIASES_PER_ENTITY]
        existing = self._entities.get(entity_id)
        if existing:
            merged = tuple(dict.fromkeys((*existing.aliases, *alias_values)))[:MAX_ALIASES_PER_ENTITY]
            if merged != existing.aliases:
                existing = replace(existing, aliases=merged)
                self._entities[entity_id] = existing
                self._index_entity(existing)
            return existing
        if len(self._entities) >= MAX_ENTITIES:
            raise ValueError("entity limit reached")
        node = EntityNode(
            entity_id=entity_id,
            label=clean_label,
            entity_kind=_compact(entity_kind, 48).casefold() or "concept",
            aliases=alias_values,
            provenance_class=_compact(provenance_class, 64).casefold() or "unknown",
            evidence_digest=_digest(evidence_ref) if evidence_ref else "",
        )
        self._entities[entity_id] = node
        self._index_entity(node)
        return node

    def _index_entity(self, node: EntityNode) -> None:
        for value in (node.label, *node.aliases):
            self._alias_index.setdefault(_token(value), set()).add(node.entity_id)

    def resolve(self, value: str) -> EntityResolution:
        token = _token(value)
        ids = tuple(sorted(self._alias_index.get(token, set())))
        if not ids:
            return EntityResolution("not_found", _digest(token))
        if len(ids) > 1:
            return EntityResolution("ambiguous", _digest(token), ids)
        node = self._entities[ids[0]]
        return EntityResolution("matched", _digest(token), ids, _token(node.label) != token)

    def node(self, entity_id: str) -> EntityNode | None:
        return self._entities.get(str(entity_id or ""))

    def add_association(
        self,
        subject: str,
        predicate: str,
        obj: str,
        *,
        provenance_class: str = "user_authored",
        evidence_ref: str = "",
        confidence: float = 1.0,
        source_offset: int = -1,
        explicit_correction: bool = False,
        replace_between: bool = False,
        replace_subject_predicate: bool = False,
        replace_object_predicate: bool = False,
    ) -> AssociationEdge:
        relation = _normalize_predicate(predicate)
        subject_node = self.add_entity(subject, provenance_class=provenance_class, evidence_ref=evidence_ref)
        object_node = self.add_entity(obj, provenance_class=provenance_class, evidence_ref=evidence_ref)
        if len(self._edges) >= MAX_EDGES:
            raise ValueError("association edge limit reached")
        active_match_indexes = [
            index for index, edge in enumerate(self._edges)
            if edge.active and (
                (replace_object_predicate and edge.object_id == object_node.entity_id and edge.predicate == relation)
                or (edge.subject_id == subject_node.entity_id and (
                    (replace_subject_predicate and edge.predicate == relation)
                    or (replace_between and edge.object_id == object_node.entity_id)
                    or (edge.object_id == object_node.entity_id and edge.predicate == relation)
                ))
            )
        ]
        supersedes = ""
        if active_match_indexes:
            prior_index = active_match_indexes[-1]
            prior = self._edges[prior_index]
            if (
                not explicit_correction
                and prior.predicate == relation
                and prior.source_offset >= int(source_offset)
            ):
                return prior
            supersedes = prior.edge_id
            for index in active_match_indexes:
                self._edges[index] = replace(self._edges[index], active=False)
        evidence_digest = _digest(evidence_ref) if evidence_ref else ""
        edge_id = "edge:" + _digest(
            subject_node.entity_id, relation, object_node.entity_id, source_offset,
            explicit_correction, evidence_digest, len(self._edges),
        )[:24]
        edge = AssociationEdge(
            edge_id=edge_id,
            subject_id=subject_node.entity_id,
            predicate=relation,
            object_id=object_node.entity_id,
            provenance_class=_compact(provenance_class, 64).casefold() or "unknown",
            evidence_digest=evidence_digest,
            confidence=round(max(0.0, min(1.0, float(confidence))), 4),
            source_offset=int(source_offset),
            explicit_correction=bool(explicit_correction),
            supersedes_edge_id=supersedes,
        )
        self._edges.append(edge)
        return edge

    def active_edges(self, *, predicate: str = "") -> tuple[AssociationEdge, ...]:
        relation = _normalize_predicate(predicate) if str(predicate or "").strip() else ""
        return tuple(edge for edge in self._edges if edge.active and (not relation or edge.predicate == relation))

    def direct(self, subject: str, obj: str, *, predicate: str = "") -> AssociationEdge | None:
        subject_resolution, object_resolution = self.resolve(subject), self.resolve(obj)
        if not subject_resolution.entity_id or not object_resolution.entity_id:
            return None
        relation = _normalize_predicate(predicate) if str(predicate or "").strip() else ""
        return next((
            edge for edge in reversed(self._edges)
            if edge.active and edge.subject_id == subject_resolution.entity_id
            and edge.object_id == object_resolution.entity_id
            and (not relation or edge.predicate == relation)
        ), None)

    def paths(self, start: str, end: str, *, max_depth: int = MAX_PATH_DEPTH) -> tuple[AssociationPath, ...]:
        depth_limit = max(1, min(MAX_PATH_DEPTH, int(max_depth)))
        start_id, end_id = self.resolve(start).entity_id, self.resolve(end).entity_id
        if not start_id or not end_id:
            return ()
        adjacency: dict[str, list[AssociationEdge]] = {}
        for edge in self.active_edges():
            adjacency.setdefault(edge.subject_id, []).append(edge)
        queue = deque([(start_id, (start_id,), (), ())])
        results: list[AssociationPath] = []
        while queue:
            current, entity_ids, edge_ids, predicates = queue.popleft()
            if len(edge_ids) >= depth_limit:
                continue
            for edge in adjacency.get(current, []):
                if edge.object_id in entity_ids:
                    continue
                next_entities = (*entity_ids, edge.object_id)
                next_edges = (*edge_ids, edge.edge_id)
                next_predicates = (*predicates, edge.predicate)
                if edge.object_id == end_id:
                    results.append(AssociationPath(next_edges, next_entities, next_predicates))
                else:
                    queue.append((edge.object_id, next_entities, next_edges, next_predicates))
        return tuple(sorted(results, key=lambda path: (path.depth, path.predicates, path.edge_ids)))

    def public_summary(self) -> dict[str, Any]:
        active = self.active_edges()
        ambiguous_aliases = sum(1 for ids in self._alias_index.values() if len(ids) > 1)
        row = {
            "contract_version": CONTRACT_VERSION,
            "entity_count": len(self._entities),
            "edge_count": len(self._edges),
            "active_edge_count": len(active),
            "superseded_edge_count": sum(not edge.active for edge in self._edges),
            "explicit_correction_count": sum(edge.explicit_correction for edge in self._edges),
            "ambiguous_alias_count": ambiguous_aliases,
            "provider_contacted": False,
            "runtime_persisted": False,
            "authority_granted": False,
            "contains_entity_labels": False,
            "contains_evidence_text": False,
        }
        row["summary_digest"] = _digest(*row.values())[:24]
        return row

    def export_private(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "entities": [asdict(node) for node in self._entities.values()],
            "edges": [asdict(edge) for edge in self._edges],
        }


__all__ = [
    "CONTRACT_VERSION", "AssociationEdge", "AssociationPath", "EntityAssociationGraph",
    "EntityNode", "EntityResolution", "MAX_PATH_DEPTH",
]
