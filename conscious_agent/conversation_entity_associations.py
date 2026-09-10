from __future__ import annotations

"""Bounded user-authored non-family association extraction and recall."""

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping

from entity_association_graph import EntityAssociationGraph


CONTRACT_VERSION = "v1500.7"
USER = "the user"
MAX_HISTORY_TURNS = 64
_LABEL = r"[A-Za-z0-9][A-Za-z0-9_.+-]*(?:\s+[A-Za-z0-9][A-Za-z0-9_.+-]*){0,4}"
_REMEMBER = re.compile(
    r"\b(?:something(?: else)? i want you to remember is that|i want you to remember that|"
    r"please remember that|remember that)\b",
    re.I,
)
_CORRECTION = re.compile(
    r"^\s*(?:no\b|actually\b|correction\b|to be clear\b)|"
    r"\b(?:you got that wrong|that's not right|that is not right|instead of)\b",
    re.I,
)
_ACTION_OR_SECRET = re.compile(
    r"\b(?:run|execute|install|delete|remove|approve|authorize|launch|download|upload|"
    r"password|secret|token|api key|private key)\b",
    re.I,
)
_USES = re.compile(
    rf"\b(?P<subject>(?:Project\s+)?{_LABEL})\s+"
    rf"(?:uses|runs\s+on|is\s+powered\s+by)\s+(?P<object>{_LABEL})"
    r"(?=$|[.!?;,]|\s+(?:but|and|not)\b)",
    re.I,
)
_BELONGS = re.compile(
    rf"\b(?P<subject>{_LABEL})\s+belongs\s+to\s+(?P<object>(?:Project\s+)?{_LABEL})"
    r"(?=$|[.!?;,]|\s+(?:but|and)\b)",
    re.I,
)
_CONTAINS = re.compile(
    rf"\b(?P<subject>(?:Project\s+)?{_LABEL})\s+(?:contains|includes)\s+(?P<object>{_LABEL})"
    r"(?=$|[.!?;,]|\s+(?:but|and)\b)",
    re.I,
)
_OWNS = re.compile(
    rf"\bI\s+(?:own|created|maintain)\s+(?P<object>(?:Project\s+)?{_LABEL})"
    r"(?=$|[.!?;,]|\s+(?:but|and)\b)",
    re.I,
)
_MY_PROJECT = re.compile(
    rf"\b(?P<subject>(?:Project\s+)?{_LABEL})\s+is\s+my\s+project\b",
    re.I,
)
_PREFERRED_PROVIDER = re.compile(
    rf"\bmy\s+preferred\s+(?:local\s+)?provider\s+is\s+(?P<object>{_LABEL})"
    r"(?=$|[.!?;,]|\s+(?:but|and)\b)",
    re.I,
)
_PREFER_OVER = re.compile(
    rf"\bI\s+prefer\s+(?P<subject>{_LABEL})\s+(?:over|to)\s+(?P<object>{_LABEL})"
    r"(?=$|[.!?;,]|\s+(?:but|and)\b)",
    re.I,
)
_USES_QUERY = re.compile(rf"\bwhat\s+(?:provider\s+)?does\s+(?P<subject>(?:Project\s+)?{_LABEL})\s+use\s*\?", re.I)
_BELONGS_QUERY = re.compile(
    rf"\b(?:which|what)\s+project\s+does\s+(?P<subject>{_LABEL})\s+belong\s+to\s*\?",
    re.I,
)
_CONTAINS_QUERY = re.compile(rf"\bwhat\s+does\s+(?P<subject>(?:Project\s+)?{_LABEL})\s+contain\s*\?", re.I)
_OWNER_QUERY = re.compile(rf"\bwho\s+(?:owns|created|maintains)\s+(?P<subject>(?:Project\s+)?{_LABEL})\s*\?", re.I)
_PREFERENCE_QUERY = re.compile(r"\b(?:what|which\s+provider)\s+do\s+i\s+prefer\s*\?", re.I)
_USES_FOLLOWUP_QUERY = re.compile(r"\bwhat\s+does\s+(?:it|that\s+project)\s+use\s*\?", re.I)
_BELONGS_FOLLOWUP_QUERY = re.compile(r"\b(?:which|what)\s+project\s+does\s+(?:it|that\s+file)\s+belong\s+to\s*\?", re.I)
_DURABLE = re.compile(r"^Entity association: (.{1,120}) \| ([a-z][a-z0-9_]{0,63}) \| (.{1,120})\.$")
_FORGET_PREFIX = re.compile(
    r"^\s*(?:please\s+)?(?:forget|retract|stop\s+remembering)\s+(?:that\s+)?(?P<statement>.+?)\s*[.!?]*\s*$",
    re.I,
)
_FORGET_USES_QUERY = re.compile(
    rf"^what\s+(?P<subject>(?:Project\s+)?{_LABEL})\s+(?:uses?|runs\s+on|is\s+powered\s+by)$",
    re.I,
)
_FORGET_BELONGS_QUERY = re.compile(
    rf"^(?:which|what)\s+project\s+(?P<subject>{_LABEL})\s+belongs\s+to$",
    re.I,
)
_FORGET_OWNER_QUERY = re.compile(
    rf"^who\s+(?:owns|created|maintains)\s+(?P<subject>(?:Project\s+)?{_LABEL})$",
    re.I,
)
_FORGET_PROVIDER_PREFERENCE = re.compile(r"^(?:which\s+provider|what)\s+i\s+prefer$", re.I)


@dataclass(frozen=True)
class ConversationAssociation:
    subject: str
    predicate: str
    object: str
    source_offset: int
    explicit_correction: bool = False


@dataclass(frozen=True)
class AssociationAnswer:
    response: str = ""
    state: str = "none"
    predicate: str = "none"
    evidence_count: int = 0


@dataclass(frozen=True)
class AssociationMutationRequest:
    action: str = "none"
    subject: str = ""
    predicate: str = ""
    object: str = ""
    recognized: bool = False


def _clean(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip(" .,!?:;")
    text = re.sub(
        r"^(?:actually|no|correction|to be clear|and|now|also|"
        r"something(?: else)? i want you to remember is that|i want you to remember that|"
        r"please remember that|remember that)\s+",
        "", text, flags=re.I,
    )
    return text[:120]


def _association(subject: str, predicate: str, obj: str, offset: int, correction: bool) -> ConversationAssociation:
    return ConversationAssociation(_clean(subject), predicate, _clean(obj), int(offset), bool(correction))


def associations_from_text(text: str, *, offset: int) -> list[ConversationAssociation]:
    message = " ".join(str(text or "").translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'"})).split())
    if not message or _ACTION_OR_SECRET.search(message):
        return []
    correction = bool(_CORRECTION.search(message))
    rows: list[ConversationAssociation] = []
    for match in _USES.finditer(message):
        rows.append(_association(match.group("subject"), "uses_provider", match.group("object"), offset, correction))
    for match in _BELONGS.finditer(message):
        rows.append(_association(match.group("subject"), "belongs_to_project", match.group("object"), offset, correction))
    for match in _CONTAINS.finditer(message):
        rows.append(_association(match.group("subject"), "contains", match.group("object"), offset, correction))
    for match in _OWNS.finditer(message):
        rows.append(_association(match.group("object"), "owned_by", USER, offset, correction))
    for match in _MY_PROJECT.finditer(message):
        rows.append(_association(match.group("subject"), "owned_by", USER, offset, correction))
    for match in _PREFERRED_PROVIDER.finditer(message):
        rows.append(_association(USER, "prefers_provider", match.group("object"), offset, correction))
    for match in _PREFER_OVER.finditer(message):
        rows.append(_association(match.group("subject"), "preferred_over", match.group("object"), offset, correction))
    unique: dict[tuple[str, str, str], ConversationAssociation] = {}
    for row in rows:
        if row.subject and row.object and row.subject.casefold() != row.object.casefold():
            unique[(row.subject.casefold(), row.predicate, row.object.casefold())] = row
    return list(unique.values())


def conversation_association_mutation_request(message: str) -> AssociationMutationRequest:
    """Parse only explicit correction or reversible forget requests."""
    text = " ".join(str(message or "").translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'"})).split())
    correction_rows = associations_from_text(text, offset=0)
    if len(correction_rows) == 1 and correction_rows[0].explicit_correction:
        row = correction_rows[0]
        return AssociationMutationRequest("correct", row.subject, row.predicate, row.object, True)
    match = _FORGET_PREFIX.fullmatch(text)
    if not match:
        return AssociationMutationRequest()
    statement = _clean(match.group("statement"))
    query_specs = (
        (_FORGET_USES_QUERY, "uses_provider", USER),
        (_FORGET_BELONGS_QUERY, "belongs_to_project", USER),
        (_FORGET_OWNER_QUERY, "owned_by", USER),
    )
    for pattern, predicate, default_object in query_specs:
        query = pattern.fullmatch(statement)
        if query:
            return AssociationMutationRequest("retract", _clean(query.group("subject")), predicate, "", True)
    if _FORGET_PROVIDER_PREFERENCE.fullmatch(statement):
        return AssociationMutationRequest("retract", USER, "prefers_provider", "", True)
    rows = associations_from_text(statement, offset=0)
    if len(rows) == 1:
        row = rows[0]
        return AssociationMutationRequest("retract", row.subject, row.predicate, row.object, True)
    return AssociationMutationRequest("retract", recognized=True)


def is_explicit_curated_association_memory(row: Mapping[str, Any]) -> bool:
    if not isinstance(row, Mapping):
        return False
    state = str(row.get("curation_state") or row.get("state") or row.get("status") or "active").lower()
    curation = row.get("curation_provenance") if isinstance(row.get("curation_provenance"), Mapping) else {}
    public = row.get("provenance") if isinstance(row.get("provenance"), Mapping) else {}
    source = str(row.get("source") or curation.get("source") or public.get("source") or "")
    explicit = bool(curation.get("operator_explicit") or public.get("operator_explicit"))
    return bool(
        state == "active" and bool(row.get("use_in_conversation", True))
        and str(row.get("type") or "") == "personal_fact"
        and source == "operator_explicit_conversation_memory_request"
        and explicit and _DURABLE.fullmatch(" ".join(str(row.get("content") or "").split()))
    )


def associations_from_durable_memories(memories: Iterable[Mapping[str, Any]]) -> list[ConversationAssociation]:
    rows: list[ConversationAssociation] = []
    memory_rows = list(memories)
    for index, memory in enumerate(memory_rows):
        if not is_explicit_curated_association_memory(memory):
            continue
        match = _DURABLE.fullmatch(" ".join(str(memory.get("content") or "").split()))
        if match:
            rows.append(_association(match.group(1), match.group(2), match.group(3), index - len(memory_rows), False))
    return rows


def _kind(label: str, predicate: str, *, subject: bool) -> str:
    lower = label.casefold()
    if lower == USER:
        return "operator"
    if lower.startswith("project ") or predicate in {"owned_by", "contains"} and subject:
        return "project"
    if re.search(r"\.[a-z0-9]{1,8}$", lower) or predicate == "belongs_to_project" and subject:
        return "file"
    if predicate in {"uses_provider", "prefers_provider", "preferred_over"} and not subject:
        return "provider"
    return "concept"


def build_conversation_association_graph(
    history: Iterable[Mapping[str, Any]],
    memories: Iterable[Mapping[str, Any]] = (),
    current_message: str = "",
) -> EntityAssociationGraph:
    rows = associations_from_durable_memories(memories)
    history_rows = [row for row in history if isinstance(row, Mapping)][-MAX_HISTORY_TURNS:]
    messages = [str(row.get("user_message") or "") for row in history_rows]
    if current_message:
        messages.append(current_message)
    for offset, message in enumerate(messages):
        rows.extend(associations_from_text(message, offset=offset))
    graph = EntityAssociationGraph()
    single_value = {"uses_provider", "belongs_to_project", "owned_by", "prefers_provider"}
    for row in rows:
        for label, subject in ((row.subject, True), (row.object, False)):
            aliases = (label[8:],) if label.casefold().startswith("project ") and len(label) > 8 else ()
            graph.add_entity(
                label, entity_kind=_kind(label, row.predicate, subject=subject), aliases=aliases,
                provenance_class="operator_explicit" if row.source_offset < 0 else "user_authored",
                evidence_ref=f"turn:{row.source_offset}:{row.predicate}",
            )
        graph.add_association(
            row.subject, row.predicate, row.object,
            provenance_class="operator_explicit" if row.source_offset < 0 else "user_authored",
            evidence_ref=f"turn:{row.source_offset}:{row.predicate}",
            source_offset=row.source_offset,
            explicit_correction=row.explicit_correction,
            replace_subject_predicate=row.predicate in single_value,
        )
    return graph


def _outgoing(graph: EntityAssociationGraph, subject: str, predicate: str) -> list[tuple[Any, Any]]:
    resolution = graph.resolve(subject)
    if not resolution.entity_id:
        return []
    rows = []
    for edge in graph.active_edges(predicate=predicate):
        if edge.subject_id == resolution.entity_id:
            obj = graph.node(edge.object_id)
            if obj:
                rows.append((edge, obj))
    return rows


def _latest_subject(history: Iterable[Mapping[str, Any]], predicate: str) -> str:
    """Resolve a pronoun only from the latest unambiguous user-authored association."""
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_HISTORY_TURNS:]
    for row in reversed(rows):
        message = str(row.get("user_message") or "")
        associations = [item for item in associations_from_text(message, offset=0) if item.predicate == predicate]
        subjects = {item.subject.casefold(): item.subject for item in associations}
        if associations:
            return next(iter(subjects.values())) if len(subjects) == 1 else ""
        pattern = _USES_QUERY if predicate == "uses_provider" else _BELONGS_QUERY
        match = pattern.search(message)
        if match:
            return _clean(match.group("subject"))
    return ""


def resolve_conversation_association_query(
    message: str,
    history: Iterable[Mapping[str, Any]],
    memories: Iterable[Mapping[str, Any]] = (),
) -> AssociationAnswer:
    text = " ".join(str(message or "").split())
    graph = build_conversation_association_graph(history, memories, text)
    followup_subject = ""
    followup_predicate = ""
    if _USES_FOLLOWUP_QUERY.search(text):
        followup_predicate = "uses_provider"
        followup_subject = _latest_subject(history, followup_predicate)
    elif _BELONGS_FOLLOWUP_QUERY.search(text):
        followup_predicate = "belongs_to_project"
        followup_subject = _latest_subject(history, followup_predicate)
    if followup_predicate:
        if not followup_subject:
            return AssociationAnswer(
                "I can't resolve what that refers to from the attributable conversation history.",
                "association_reference_uncertain", "unknown", 0,
            )
        rows = _outgoing(graph, followup_subject, followup_predicate)
        if not rows:
            return AssociationAnswer(
                f"I don't have enough attributable information to answer that about {followup_subject}.",
                "association_uncertain", "unknown", 0,
            )
        label = rows[-1][1].label
        response = (
            f"You told me {followup_subject} uses {label}."
            if followup_predicate == "uses_provider"
            else f"You told me {followup_subject} belongs to {label}."
        )
        return AssociationAnswer(response, "resolved_user_attributable_followup", followup_predicate, len(rows))
    query_specs = (
        (_USES_QUERY, "uses_provider", "uses"),
        (_BELONGS_QUERY, "belongs_to_project", "belongs"),
        (_CONTAINS_QUERY, "contains", "contains"),
        (_OWNER_QUERY, "owned_by", "owner"),
    )
    for pattern, predicate, kind in query_specs:
        match = pattern.search(text)
        if not match:
            continue
        subject = _clean(match.group("subject"))
        rows = _outgoing(graph, subject, predicate)
        if not rows:
            return AssociationAnswer(
                f"I don't have enough attributable information to answer that about {subject}.",
                "association_uncertain", "unknown", 0,
            )
        labels = [obj.label for _, obj in rows]
        if kind == "uses":
            response = f"You told me {subject} uses {labels[-1]}."
        elif kind == "belongs":
            response = f"You told me {subject} belongs to {labels[-1]}."
        elif kind == "owner":
            response = f"You told me you own {subject}." if labels[-1].casefold() == USER else f"You told me {labels[-1]} owns {subject}."
        else:
            response = f"You told me {subject} contains " + ", ".join(labels) + "."
        return AssociationAnswer(response, "direct_user_attributable_association", predicate, len(rows))
    if _PREFERENCE_QUERY.search(text):
        rows = _outgoing(graph, USER, "prefers_provider")
        if not rows:
            return AssociationAnswer(
                "I don't have enough attributable information to know which provider you prefer.",
                "association_uncertain", "unknown", 0,
            )
        return AssociationAnswer(
            f"You told me your preferred provider is {rows[-1][1].label}.",
            "direct_user_attributable_association", "prefers_provider", len(rows),
        )
    return AssociationAnswer()


def conversation_association_prompt_block(graph: EntityAssociationGraph, message: str = "") -> str:
    edges = graph.active_edges()
    if not edges:
        return ""
    text = " ".join(str(message or "").split()).casefold()
    if text:
        mentioned_ids: set[str] = set()
        for edge in edges:
            for entity_id in (edge.subject_id, edge.object_id):
                node = graph.node(entity_id)
                if node and any(
                    re.search(rf"(?<![a-z0-9]){re.escape(value.casefold())}(?![a-z0-9])", text)
                    for value in (node.label, *node.aliases)
                ):
                    mentioned_ids.add(entity_id)
        edges = tuple(
            edge for edge in edges
            if edge.subject_id in mentioned_ids or edge.object_id in mentioned_ids
        )
        if not edges:
            return ""
    lines = [
        "USER-ATTRIBUTABLE ENTITY ASSOCIATIONS",
        "Use only these user-authored associations. Do not infer missing links or treat assistant text as evidence.",
    ]
    for edge in edges[-16:]:
        subject, obj = graph.node(edge.subject_id), graph.node(edge.object_id)
        if subject and obj:
            lines.append(f"- {subject.label} {edge.predicate.replace('_', ' ')} {obj.label}.")
    return "\n".join(lines)


def conversation_association_memory_acknowledgement(message: str) -> str:
    rows = associations_from_text(message, offset=0)
    if not rows:
        return ""
    statements = [f"{row.subject} {row.predicate.replace('_', ' ')} {row.object}" for row in rows]
    joined = statements[0] if len(statements) == 1 else ", ".join(statements[:-1]) + f", and {statements[-1]}"
    return f"I'll remember that {joined}."


def conversation_association_statement_acknowledgement(message: str) -> str:
    """Acknowledge one bare association without asking a provider to paraphrase it."""
    text = " ".join(str(message or "").split())
    rows = associations_from_text(text, offset=0)
    if (
        len(rows) != 1 or bool(_REMEMBER.search(text)) or "?" in text or len(text.split()) > 16
        or re.search(r"\b(?:and|but|because|although|while|so that)\b", text, re.I)
    ):
        return ""
    row = rows[0]
    if row.predicate == "uses_provider":
        statement = f"{row.subject} uses {row.object}"
    elif row.predicate == "belongs_to_project":
        statement = f"{row.subject} belongs to {row.object}"
    elif row.predicate == "contains":
        statement = f"{row.subject} contains {row.object}"
    elif row.predicate == "owned_by" and row.object == USER:
        statement = f"you own {row.subject}"
    elif row.predicate == "prefers_provider" and row.subject == USER:
        statement = f"your preferred provider is {row.object}"
    elif row.predicate == "preferred_over":
        statement = f"you prefer {row.subject} over {row.object}"
    else:
        return ""
    return f"Got it: {statement}."


def durable_conversation_association_records(message: str) -> list[str]:
    return [
        f"Entity association: {row.subject} | {row.predicate} | {row.object}."
        for row in associations_from_text(message, offset=0)
    ]


__all__ = [
    "AssociationAnswer", "AssociationMutationRequest", "CONTRACT_VERSION", "ConversationAssociation",
    "associations_from_durable_memories", "associations_from_text",
    "build_conversation_association_graph", "conversation_association_memory_acknowledgement",
    "conversation_association_mutation_request",
    "conversation_association_prompt_block", "conversation_association_statement_acknowledgement",
    "durable_conversation_association_records",
    "is_explicit_curated_association_memory", "resolve_conversation_association_query",
]
