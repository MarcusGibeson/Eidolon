from __future__ import annotations

"""User-attributable family relationships with bounded kinship inference."""

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping


CONTRACT_VERSION = "v1500.7"
USER = "the user"
_PERSON = r"[A-Z][A-Za-z'-]{1,39}(?:\s+[A-Z][A-Za-z'-]{1,39}){0,2}"
_ROLE_REFERENCE = (
    r"(?:my\s+)?(?:biological\s+)?(?:mom|mother|dad|father)|"
    r"(?:my\s+)?(?:stepmom|stepmother|stepdad|stepfather|fiancee|fiance|wife|husband|stepdaughter|stepson)"
)
_PERSON_REFERENCE = rf"(?:{_ROLE_REFERENCE}|{_PERSON})"
_DIRECT = re.compile(
    rf"\b(?P<name>{_PERSON})\s+(?i:is\s+my\s+)"
    r"(?P<role>(?i:biological (?:mom|mother|dad|father)|mom|mother|dad|father|stepmom|stepmother|"
    r"stepdad|stepfather|fiancee|fiance|wife|husband|stepdaughter|stepson|daughter|son))\b",
)
_NAMED_PARENT = re.compile(
    rf"(?i:\bmy\s+)(?P<biological>(?i:biological\s+))?"
    rf"(?P<role>(?i:mom|mother|dad|father|stepmom|stepmother|stepdad|stepfather))\s*,?\s*(?P<name>{_PERSON})\b"
    rf"(?=\s*(?:[.!?]|$|,?\s+(?i:and|who)\b))",
)
_BIOLOGICAL_CHILD = re.compile(
    rf"\b(?P<child>{_PERSON})\s+(?i:is\s+)(?P<parent>{_PERSON})'s\s+"
    rf"(?i:biological\s+)(?P<role>(?i:daughter|son))\b",
)
_MARRIED_CLAUSE = re.compile(
    rf"\b(?P<stepparent>{_PERSON})\s+(?i:is\s+my\s+)"
    rf"(?P<step_role>(?i:stepmom|stepmother|stepdad|stepfather))\b"
    rf"[^.!?]{{0,100}}(?i:\bmarried\s+to\s+my\s+)"
    rf"(?P<parent_role>(?i:mom|mother|dad|father))\s*,?\s*(?P<parent>{_PERSON})\b",
)
_ROLE_NAME = re.compile(
    rf"(?i:\bmy\s+)(?P<role>(?i:fiancee|fiance|wife|husband|stepdaughter|stepson|daughter|son))"
    rf"(?:'s|s)\s+(?i:name\s+is\s+)(?P<name>{_PERSON})\b"
)
_HAVE_PARTNER = re.compile(
    rf"(?i:\bi\s+have\s+(?:a\s+)?)(?P<role>(?i:fiancee|fiance|wife|husband))\b"
    rf"[^.!?]{{0,100}}(?i:\b(?:her|his|their)\s+name\s+is\s+)(?P<name>{_PERSON})\b"
)
_SPOUSE = re.compile(
    rf"\b(?P<first>{_PERSON})\s+(?i:is\s+married\s+to\s+)(?P<second>{_PERSON})\b"
)
_EX_SPOUSE = re.compile(
    rf"\b(?P<first>{_PERSON})\s+(?i:is\s+(?:also\s+)?)(?P<second>{_PERSON})'s\s+"
    rf"(?P<role>(?i:ex-wife|ex-husband|ex-spouse))\b"
)
_BETWEEN_QUERY = re.compile(
    rf"(?i:\b(?:what(?:'s| is)|describe)\s+(?:the\s+)?relationship\s+between\s+)"
    rf"(?P<first>{_PERSON})\s+(?i:and\s+)(?P<second>{_PERSON})\b",
)
_TO_QUERY = re.compile(
    rf"(?i:\b(?:who|what)\s+is\s+)(?P<first>{_PERSON})\s+(?i:to\s+)(?P<second>{_PERSON})\b"
)
_NATURAL_RELATION_QUERY = re.compile(
    rf"(?i:\b(?:who|what)\s+is\s+)(?P<first>{_PERSON_REFERENCE})\s+(?i:to\s+)(?P<second>{_PERSON_REFERENCE})\b|"
    rf"(?i:\bhow\s+is\s+)(?P<related_first>{_PERSON_REFERENCE})\s+(?i:related\s+to\s+)(?P<related_second>{_PERSON_REFERENCE})\b"
)
_WHO_QUERY = re.compile(rf"(?i:\bwho\s+is\s+)(?P<person>{_PERSON})\s*\?")
_ALIAS_QUERY = re.compile(
    r"\bwhen\s+i\s+say\s+(mom|mother|dad|father)\b[^?]{0,80}\bwho\b|"
    r"\bwho\b[^?]{0,80}\bwhen\s+i\s+say\s+(mom|mother|dad|father)\b",
    re.I,
)
_PRONOUN_PARENT_CORRECTION = re.compile(
    r"\b(?:he|she)(?:'s|\s+is)\s+my\s+"
    r"(biological\s+(?:mom|mother|dad|father)|mom|mother|dad|father|stepmom|stepmother|stepdad|stepfather)\b",
    re.I,
)
_CORRECTED_PRONOUN_RELATION = re.compile(
    rf"\b(?P<person>{_PERSON})\s+(?i:(?:is|would be)\s+(?:his|her|their)\s+)"
    r"(?P<role>(?i:step-granddad|step-grandfather|step-grandmother|step-grandma|grandfather|granddad|grandmother|grandma))\b",
)
_DURABLE = re.compile(r"^Family relationship: (.{1,120}) \| ([a-z_]+) \| (.{1,120})\.$")
_LEGACY_PARTNER = re.compile(r"^The user's fiancee is ([A-Z][A-Za-z'-]{1,39}(?: [A-Z][A-Za-z'-]{1,39}){0,2})\.$")
_LEGACY_STEPDAUGHTER = re.compile(r"^The user's stepdaughter is ([A-Z][A-Za-z'-]{1,39}(?: [A-Z][A-Za-z'-]{1,39}){0,2})\.$")
_LEGACY_BIOLOGICAL_DAUGHTER = re.compile(
    r"^([A-Z][A-Za-z'-]{1,39}(?: [A-Z][A-Za-z'-]{1,39}){0,2}) is "
    r"([A-Z][A-Za-z'-]{1,39}(?: [A-Z][A-Za-z'-]{1,39}){0,2})'s biological daughter\.$"
)

_RELATION_ALIASES = {
    "biological mom": "biological_mother",
    "biological mother": "biological_mother",
    "mom": "mother",
    "mother": "mother",
    "biological dad": "biological_father",
    "biological father": "biological_father",
    "dad": "father",
    "father": "father",
    "stepmom": "stepmother",
    "stepmother": "stepmother",
    "stepdad": "stepfather",
    "stepfather": "stepfather",
    "fiancee": "fiancee",
    "fiance": "fiancee",
    "wife": "wife",
    "husband": "husband",
    "stepdaughter": "stepdaughter",
    "stepson": "stepson",
    "daughter": "daughter",
    "son": "son",
    "step-granddad": "step_grandfather",
    "step-grandfather": "step_grandfather",
    "step-grandma": "step_grandmother",
    "step-grandmother": "step_grandmother",
    "granddad": "grandfather",
    "grandfather": "grandfather",
    "grandma": "grandmother",
    "grandmother": "grandmother",
    "ex-wife": "ex_wife",
    "ex-husband": "ex_husband",
    "ex-spouse": "ex_spouse",
}

_REFERENCE_RELATIONS = {
    "mom": ("biological_mother", "mother"),
    "mother": ("biological_mother", "mother"),
    "biological mom": ("biological_mother",),
    "biological mother": ("biological_mother",),
    "dad": ("biological_father", "father"),
    "father": ("biological_father", "father"),
    "biological dad": ("biological_father",),
    "biological father": ("biological_father",),
    "stepmom": ("stepmother",), "stepmother": ("stepmother",),
    "stepdad": ("stepfather",), "stepfather": ("stepfather",),
    "fiancee": ("fiancee",), "fiance": ("fiancee",),
    "wife": ("wife",), "husband": ("husband",),
    "stepdaughter": ("stepdaughter",), "stepson": ("stepson",),
}

_ROLE_ENTITY_ALIASES = {
    "biological_mother": ("mom", "mother", "biological mom", "biological mother", "my mom", "my mother"),
    "mother": ("mom", "mother", "my mom", "my mother"),
    "biological_father": ("dad", "father", "biological dad", "biological father", "my dad", "my father"),
    "father": ("dad", "father", "my dad", "my father"),
    "stepmother": ("stepmom", "stepmother", "my stepmom", "my stepmother"),
    "stepfather": ("stepdad", "stepfather", "my stepdad", "my stepfather"),
    "fiancee": ("fiancee", "fiance", "my fiancee", "my fiance"),
    "wife": ("wife", "my wife"), "husband": ("husband", "my husband"),
    "stepdaughter": ("stepdaughter", "my stepdaughter"),
    "stepson": ("stepson", "my stepson"),
}

_SINGLE_USER_RELATIONS = {
    "biological_mother", "mother", "biological_father", "father",
    "fiancee", "wife", "husband",
}

_INVERSE_RELATIONS = {
    "spouse": "spouse", "ex_spouse": "ex-spouse", "ex_wife": "ex-spouse", "ex_husband": "ex-spouse",
    "biological_mother": "child", "mother": "child", "biological_father": "child", "father": "child",
    "stepmother": "stepchild", "stepfather": "stepchild",
    "fiancee": "fiance", "wife": "spouse", "husband": "spouse",
    "stepdaughter": "stepparent", "stepson": "stepparent", "daughter": "parent", "son": "parent",
    "biological_daughter": "parent", "biological_son": "parent",
    "step_grandfather": "step-grandchild", "step_grandmother": "step-grandchild",
    "grandfather": "grandchild", "grandmother": "grandchild",
}


@dataclass(frozen=True)
class FamilyEdge:
    subject: str
    relation: str
    object: str
    source_offset: int
    explicit_correction: bool = False


@dataclass(frozen=True)
class FamilyAnswer:
    response: str = ""
    state: str = "none"
    relation: str = "none"
    evidence_count: int = 0


def is_explicit_curated_family_memory(row: Mapping[str, Any]) -> bool:
    if not isinstance(row, Mapping):
        return False
    state = str(row.get("curation_state") or row.get("state") or row.get("status") or "active").lower()
    if state != "active" or not bool(row.get("use_in_conversation", True)):
        return False
    curation = row.get("curation_provenance") if isinstance(row.get("curation_provenance"), Mapping) else {}
    public = row.get("provenance") if isinstance(row.get("provenance"), Mapping) else {}
    source = str(row.get("source") or curation.get("source") or public.get("source") or "")
    explicit = bool(curation.get("operator_explicit") or public.get("operator_explicit"))
    raw_eligible = row.get("relationship_eligible") is True
    curated_projection = str(row.get("type") or "") in {"relationship", "personal_fact"} and bool(public.get("available"))
    return bool(
        source == "operator_explicit_conversation_memory_request"
        and explicit
        and (raw_eligible or curated_projection)
    )


def _clean(value: Any) -> str:
    cleaned = " ".join(str(value or "").split()).strip(" .,!?:;")
    cleaned = re.sub(r"^(?:and|now|good|great)\s+", "", cleaned, flags=re.I)
    return cleaned[:120]


def _relation(value: str) -> str:
    return _RELATION_ALIASES.get(_clean(value).casefold(), "")


def _edge(subject: str, relation: str, obj: str, offset: int, correction: bool = False) -> FamilyEdge:
    return FamilyEdge(_clean(subject), relation, _clean(obj), offset, correction)


def _query_pair(text: str) -> tuple[str, str] | None:
    for pattern in (_BETWEEN_QUERY, _TO_QUERY, _NATURAL_RELATION_QUERY):
        match = pattern.search(text)
        if match:
            groups = match.groupdict()
            first = groups.get("first") or groups.get("related_first") or ""
            second = groups.get("second") or groups.get("related_second") or ""
            return _clean(first), _clean(second)
    return None


def _resolve_reference(value: str, edges: Iterable[FamilyEdge]) -> str:
    clean = _clean(value)
    role = re.sub(r"^my\s+", "", clean, flags=re.I).casefold()
    relations = _REFERENCE_RELATIONS.get(role)
    if not relations:
        return clean
    rows = list(edges)
    return next(
        (item.subject for relation in relations for item in reversed(rows)
         if item.object == USER and item.relation == relation),
        clean,
    )


def _alias_from_query(text: str) -> str:
    match = _ALIAS_QUERY.search(text)
    return _clean(next((group for group in match.groups() if group), "")).casefold() if match else ""


def edges_from_text(text: str, *, offset: int, previous_query: tuple[str, str] | None = None) -> list[FamilyEdge]:
    message = " ".join(str(text or "").translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'"})).split())
    if _query_pair(message) or _WHO_QUERY.search(message) or _ALIAS_QUERY.search(message):
        return []
    edges: list[FamilyEdge] = []
    married = _MARRIED_CLAUSE.search(message)
    if married:
        stepparent = married.group("stepparent")
        step_role = married.group("step_role")
        parent_role = married.group("parent_role")
        parent = married.group("parent")
        edges.extend((
            _edge(stepparent, _relation(step_role), USER, offset),
            _edge(parent, _relation(parent_role), USER, offset),
            _edge(stepparent, "spouse", parent, offset),
        ))
    for match in _DIRECT.finditer(message):
        edges.append(_edge(match.group("name"), _relation(match.group("role")), USER, offset))
    for match in _NAMED_PARENT.finditer(message):
        biological, role, name = match.group("biological"), match.group("role"), match.group("name")
        label = ("biological " if biological else "") + role
        edges.append(_edge(name, _relation(label), USER, offset))
    named_children: list[str] = []
    for match in _ROLE_NAME.finditer(message):
        name, role = match.group("name"), match.group("role")
        edges.append(_edge(name, _relation(role), USER, offset))
        if role.casefold() in {"stepdaughter", "stepson", "daughter", "son"}:
            named_children.append(name)
    for match in _HAVE_PARTNER.finditer(message):
        edges.append(_edge(match.group("name"), _relation(match.group("role")), USER, offset))
    for match in _BIOLOGICAL_CHILD.finditer(message):
        child, parent, child_role = match.group("child"), match.group("parent"), match.group("role")
        if child.casefold() in {"she", "he", "they"} and named_children:
            child = named_children[-1]
        edges.append(_edge(child, f"biological_{child_role.casefold()}", parent, offset))
    for match in _SPOUSE.finditer(message):
        edges.append(_edge(match.group("first"), "spouse", match.group("second"), offset))
    named_people = [item.subject for item in edges if item.subject.casefold() not in {"she", "he", "they"}]
    for match in _EX_SPOUSE.finditer(message):
        first = match.group("first")
        if first.casefold() in {"she", "he", "they"} and named_people:
            first = named_people[0]
        edges.append(_edge(first, _relation(match.group("role")), match.group("second"), offset))
    correction = _CORRECTED_PRONOUN_RELATION.search(message)
    if correction and previous_query:
        person, raw_relation = correction.group("person"), correction.group("role")
        other = next((name for name in previous_query if name.casefold() != person.casefold()), "")
        if other:
            edges.append(_edge(person, _relation(raw_relation), other, offset, True))
    unique: dict[tuple[str, str, str], FamilyEdge] = {}
    for item in edges:
        if item.relation:
            unique[(item.subject.casefold(), item.relation, item.object.casefold())] = item
    return list(unique.values())


def edges_from_durable_memories(memories: Iterable[Mapping[str, Any]]) -> list[FamilyEdge]:
    edges: list[FamilyEdge] = []
    memory_rows = list(memories)
    for index, row in enumerate(memory_rows):
        if not is_explicit_curated_family_memory(row):
            continue
        source_offset = index - len(memory_rows)
        content = " ".join(str(row.get("content") or "").split())
        match = _DURABLE.fullmatch(content)
        if match and match.group(2) in set(_RELATION_ALIASES.values()) | {"spouse", "biological_daughter", "biological_son"}:
            edges.append(_edge(match.group(1), match.group(2), match.group(3), source_offset))
            continue
        partner = _LEGACY_PARTNER.fullmatch(content)
        stepdaughter = _LEGACY_STEPDAUGHTER.fullmatch(content)
        biological_daughter = _LEGACY_BIOLOGICAL_DAUGHTER.fullmatch(content)
        if partner:
            edges.append(_edge(partner.group(1), "fiancee", USER, source_offset))
        elif stepdaughter:
            edges.append(_edge(stepdaughter.group(1), "stepdaughter", USER, source_offset))
        elif biological_daughter:
            edges.append(_edge(biological_daughter.group(1), "biological_daughter", biological_daughter.group(2), source_offset))
    return edges


def build_family_graph(
    history: Iterable[Mapping[str, Any]],
    memories: Iterable[Mapping[str, Any]] = (),
    current_message: str = "",
) -> list[FamilyEdge]:
    edges = edges_from_durable_memories(memories)
    previous_query: tuple[str, str] | None = None
    previous_alias = ""
    rows = [row for row in history if isinstance(row, Mapping)][-64:]
    messages = [str(row.get("user_message") or "") for row in rows]
    if current_message:
        messages.append(current_message)
    for offset, message in enumerate(messages):
        parsed = edges_from_text(message, offset=offset, previous_query=previous_query)
        parent_correction = _PRONOUN_PARENT_CORRECTION.search(message)
        if parent_correction and previous_alias:
            prior_roles = (
                {"mother", "biological_mother", "stepmother"}
                if previous_alias in {"mom", "mother"}
                else {"father", "biological_father", "stepfather"}
            )
            prior = next(
                (item for item in reversed(edges) if item.object == USER and item.relation in prior_roles), None
            )
            if prior:
                parsed.append(_edge(prior.subject, _relation(parent_correction.group(1)), USER, offset, True))
        edges.extend(parsed)
        pair = _query_pair(message)
        if pair:
            previous_query = pair
        alias = _alias_from_query(message)
        previous_alias = alias
    graph = family_entity_association_graph(edges)
    projected: list[FamilyEdge] = []
    for association in graph.active_edges():
        subject = graph.node(association.subject_id)
        obj = graph.node(association.object_id)
        if subject and obj:
            projected.append(FamilyEdge(
                subject.label, association.predicate, obj.label,
                association.source_offset, association.explicit_correction,
            ))
    return projected


def family_entity_association_graph(edges: Iterable[FamilyEdge]):
    from entity_association_graph import EntityAssociationGraph

    graph = EntityAssociationGraph()
    rows = list(edges)
    aliases_by_label: dict[str, list[str]] = {}
    for item in rows:
        if item.object == USER:
            aliases_by_label.setdefault(item.subject.casefold(), []).extend(_ROLE_ENTITY_ALIASES.get(item.relation, ()))
    for item in rows:
        for label in (item.subject, item.object):
            aliases = list((label.split()[0],) if label != USER and len(label.split()) > 1 else ())
            aliases.extend(aliases_by_label.get(label.casefold(), ()))
            graph.add_entity(
                label, entity_kind="person" if label != USER else "operator",
                aliases=aliases, provenance_class="operator_explicit" if item.source_offset < 0 else "user_authored",
            )
        graph.add_association(
            item.subject, item.relation, item.object,
            provenance_class="operator_explicit" if item.source_offset < 0 else "user_authored",
            source_offset=item.source_offset,
            explicit_correction=item.explicit_correction,
            replace_between=True,
            replace_object_predicate=item.object == USER and item.relation in _SINGLE_USER_RELATIONS,
        )
    return graph


def _find(edges: Iterable[FamilyEdge], subject: str, obj: str) -> FamilyEdge | None:
    return next((item for item in reversed(list(edges)) if _same_person(item.subject, subject) and _same_person(item.object, obj)), None)


def _person_to_user(edges: Iterable[FamilyEdge], name: str, relations: set[str]) -> FamilyEdge | None:
    return next((item for item in edges if _same_person(item.subject, name) and item.object == USER and item.relation in relations), None)


def _same_person(first: str, second: str) -> bool:
    a, b = first.casefold().split(), second.casefold().split()
    return bool(a and b and (a == b or (a[0] == b[0] and (len(a) == 1 or len(b) == 1))))


def _label(relation: str) -> str:
    return {
        "biological_mother": "biological mother", "mother": "mother",
        "biological_father": "biological father", "father": "father",
        "stepmother": "stepmother", "stepfather": "stepfather",
        "fiancee": "fiancee", "fiance": "fiance", "wife": "wife", "husband": "husband",
        "stepdaughter": "stepdaughter", "stepson": "stepson", "daughter": "daughter", "son": "son",
        "biological_daughter": "biological daughter", "biological_son": "biological son",
        "spouse": "spouse", "step_grandfather": "step-grandfather", "step_grandmother": "step-grandmother",
        "grandfather": "grandfather", "grandmother": "grandmother",
        "ex_wife": "ex-wife", "ex_husband": "ex-husband", "ex_spouse": "ex-spouse",
    }.get(relation, relation.replace("_", " "))


def resolve_family_relationship_query(
    message: str,
    history: Iterable[Mapping[str, Any]],
    memories: Iterable[Mapping[str, Any]] = (),
) -> FamilyAnswer:
    edges = build_family_graph(history, memories, message)
    parent_correction = _PRONOUN_PARENT_CORRECTION.search(message)
    if parent_correction:
        corrected_relation = _relation(parent_correction.group(1))
        corrected = next(
            (item for item in reversed(edges) if item.object == USER and item.relation == corrected_relation), None
        )
        if corrected:
            alias = "mom" if "mother" in corrected_relation else "dad"
            return FamilyAnswer(
                f"Got it: {corrected.subject} is your {_label(corrected_relation)}, and {alias} refers to {corrected.subject}.",
                "family_parent_correction", corrected_relation, 1,
            )
    alias = _alias_from_query(message)
    if alias:
        roles = (
            ("biological_mother", "mother", "stepmother")
            if alias in {"mom", "mother"}
            else ("biological_father", "father", "stepfather")
        )
        person = next(
            (item for relation in roles for item in edges if item.object == USER and item.relation == relation), None
        )
        if person:
            return FamilyAnswer(
                f"When you say {alias}, you're referring to {person.subject}, your {_label(person.relation)}.",
                "family_alias_recall", person.relation, 1,
            )
        return FamilyAnswer(
            f"I don't have enough attributable family information to know who you mean by {alias}.",
            "family_alias_uncertain", "unknown", 0,
        )
    pair = _query_pair(message)
    if not pair:
        who = _WHO_QUERY.search(message)
        if not who:
            return FamilyAnswer()
        requested = _clean(who.group("person"))
        user_edge = next(
            (item for item in edges if _same_person(item.subject, requested) and item.object == USER), None
        )
        if not user_edge:
            return FamilyAnswer(
                f"I don't have enough attributable family information to identify {requested}.",
                "family_identity_uncertain", "unknown", 0,
            )
        name = user_edge.subject
        response = f"{name} is your {_label(user_edge.relation)}."
        biological_child = next(
            (item for item in edges if _same_person(item.subject, name) and item.relation in {"biological_daughter", "biological_son"}), None
        )
        if biological_child:
            response += f" You told me {name} is {biological_child.object}'s {_label(biological_child.relation)}."
        spouse = next(
            (item for item in edges if item.relation == "spouse" and (_same_person(item.subject, name) or _same_person(item.object, name))), None
        )
        if spouse:
            other = spouse.object if _same_person(spouse.subject, name) else spouse.subject
            response += f" You also told me {name} is {other}'s spouse."
        return FamilyAnswer(
            response, "direct_user_attributable_identity", user_edge.relation,
            1 + int(bool(biological_child)) + int(bool(spouse)),
        )
    first, second = (_resolve_reference(pair[0], edges), _resolve_reference(pair[1], edges))
    direct = _find(edges, first, second)
    if direct:
        return FamilyAnswer(
            f"{first} is {second}'s {_label(direct.relation)}.",
            "direct_user_attributable_relationship", direct.relation, 1,
        )
    reverse = _find(edges, second, first)
    if reverse and reverse.relation in _INVERSE_RELATIONS and reverse.relation not in {"ex_wife", "ex_husband", "ex_spouse"}:
        inverse = _INVERSE_RELATIONS[reverse.relation]
        return FamilyAnswer(
            f"{first} is {second}'s {inverse}. You told me {second} is {first}'s {_label(reverse.relation)}.",
            "inverse_user_attributable_relationship", inverse.replace("-", "_"), 1,
        )
    if reverse and reverse.relation in {"ex_wife", "ex_husband", "ex_spouse"}:
        first_role = _person_to_user(edges, first, {"father", "biological_father", "stepfather"})
        inverse = "ex-husband" if first_role else "ex-spouse"
        return FamilyAnswer(
            f"{first} is {second}'s {inverse}. You told me {second} is {first}'s {_label(reverse.relation)}.",
            "direct_user_attributable_relationship", inverse.replace("-", "_"), 1,
        )

    first_parent = _person_to_user(edges, first, {"mother", "biological_mother", "father", "biological_father", "stepmother", "stepfather"})
    second_partner = _person_to_user(edges, second, {"fiancee", "fiance", "wife", "husband"})
    if first_parent and second_partner:
        parent = "mother" if "mother" in first_parent.relation else "father"
        future = second_partner.relation in {"fiancee", "fiance"}
        relation = f"future {parent}-in-law" if future else f"{parent}-in-law"
        return FamilyAnswer(
            f"{first} is {second}'s {relation}: {first} is your {_label(first_parent.relation)}, and {second} is your {_label(second_partner.relation)}.",
            "derived_user_attributable_relationship", relation.replace(" ", "_"), 2,
        )

    first_child = _person_to_user(edges, first, {"stepdaughter", "stepson", "daughter", "son"})
    second_parent = _person_to_user(edges, second, {"mother", "biological_mother", "father", "biological_father", "stepmother", "stepfather"})
    if first_child and second_parent:
        grandparent = "grandmother" if "mother" in second_parent.relation else "grandfather"
        if first_child.relation.startswith("step"):
            grandparent = "step-" + grandparent
        directional = bool(_TO_QUERY.search(message) or _NATURAL_RELATION_QUERY.search(message))
        if directional:
            child_relation = {
                "stepdaughter": "step-granddaughter", "stepson": "step-grandson",
                "daughter": "granddaughter", "son": "grandson",
            }.get(first_child.relation, "grandchild")
            return FamilyAnswer(
                f"{first} is {second}'s {child_relation}: {first} is your {_label(first_child.relation)}, and {second} is your {_label(second_parent.relation)}.",
                "derived_user_attributable_relationship", child_relation.replace("-", "_"), 2,
            )
        return FamilyAnswer(
            f"{second} is {first}'s {grandparent}: {second} is your {_label(second_parent.relation)}, and {first} is your {_label(first_child.relation)}.",
            "derived_user_attributable_relationship", grandparent.replace("-", "_"), 2,
        )
    return FamilyAnswer(
        f"I don't have enough attributable family information to determine the relationship between {first} and {second}.",
        "family_relationship_uncertain", "unknown", 0,
    )


def family_prompt_block(edges: Iterable[FamilyEdge], message: str = "") -> str:
    rows = list(edges)
    if not rows:
        return ""
    text = " ".join(str(message or "").split()).casefold()
    if text:
        seeds = {
            label.casefold() for item in rows for label in (item.subject, item.object)
            if label != USER and re.search(rf"(?<![a-z0-9]){re.escape(label.casefold())}(?![a-z0-9])", text)
        }
        role_words = {
            relation for alias, relations in _REFERENCE_RELATIONS.items()
            if re.search(rf"\b{re.escape(alias)}\b", text) for relation in relations
        }
        seeds.update(item.subject.casefold() for item in rows if item.object == USER and item.relation in role_words)
        rows = [
            item for item in rows
            if item.subject.casefold() in seeds or item.object.casefold() in seeds
        ]
        if not rows:
            return ""
    lines = [
        "USER-ATTRIBUTABLE FAMILY RELATIONSHIPS",
        "Use only these user-authored relationships. Do not invent missing family links.",
    ]
    for item in rows[-16:]:
        lines.append(f"- {item.subject} is {_label(item.relation)} of {item.object}.")
    return "\n".join(lines)


def family_memory_acknowledgement(message: str) -> str:
    edges = edges_from_text(message, offset=0)
    if not edges:
        return ""
    statements: list[str] = []
    for item in edges:
        if item.object == USER:
            statements.append(f"{item.subject} is your {_label(item.relation)}")
        else:
            statements.append(f"{item.subject} is {item.object}'s {_label(item.relation)}")
    if len(statements) == 1:
        joined = statements[0]
    else:
        joined = ", ".join(statements[:-1]) + f", and {statements[-1]}"
    return f"I'll remember that {joined}."


def durable_family_records(message: str) -> list[str]:
    return [f"Family relationship: {item.subject} | {item.relation} | {item.object}." for item in edges_from_text(message, offset=0)]


__all__ = [
    "CONTRACT_VERSION", "FamilyAnswer", "FamilyEdge", "build_family_graph", "durable_family_records",
    "edges_from_text", "family_entity_association_graph", "family_memory_acknowledgement",
    "family_prompt_block", "is_explicit_curated_family_memory",
    "resolve_family_relationship_query",
]
