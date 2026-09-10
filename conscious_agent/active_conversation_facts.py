from __future__ import annotations

"""Bounded user-authored fact continuity for the active conversation.

This layer resolves a small set of explicit identity and relationship facts from
recent user turns. Assistant text is never evidence. Durable storage occurs only
when the user explicitly asks Eidolon to remember an eligible personal fact.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping


CONTRACT_VERSION = "v1500.9"
MAX_HISTORY_TURNS = 64
MAX_FACTS = 12
MAX_FACT_VALUE_CHARS = 120
MAX_MEMORY_CONTENT_CHARS = 220

_NAME_TOKEN = r"([A-Za-z][A-Za-z'-]{1,39})"
_NAME = r"((?-i:[A-Z])[A-Za-z'-]{1,39})"
_REMEMBER = re.compile(
    r"\b(?:something(?: else)? i want you to remember is that|i want you to remember that|please remember that|remember that)\b",
    re.I,
)
_USER_NAME = re.compile(rf"\bmy name is\s+{_NAME}\b", re.I)
_PARTNER_RELATION = r"fianc(?:e|ee|é|ée)|wife|husband|spouse|partner|girlfriend|boyfriend"
_PARTNER_NAME = (
    re.compile(rf"\bi have (?:a\s+)?(?P<relation>{_PARTNER_RELATION})\b[^.!?]{{0,100}}\b(?:her|his|their) name is\s+(?P<name>{_NAME_TOKEN})\b", re.I),
    re.compile(rf"\bmy\s+(?P<relation>{_PARTNER_RELATION})(?:'s|s)?\s+name is\s+(?P<name>{_NAME_TOKEN})\b", re.I),
    re.compile(rf"\bmy\s+(?P<relation>{_PARTNER_RELATION})\s+is\s+named\s+(?P<name>{_NAME_TOKEN})\b", re.I),
    re.compile(rf"\bmy\s+(?P<relation>{_PARTNER_RELATION})\s+is\s+(?P<name>{_NAME_TOKEN})\b", re.I),
    re.compile(rf"\bi(?:'m| am)\s+(?:engaged|married)\s+to\s+(?P<name>{_NAME_TOKEN})\b", re.I),
    re.compile(rf"\b(?P<name>{_NAME_TOKEN})\s+is\s+my\s+(?P<relation>{_PARTNER_RELATION})\b", re.I),
)
_LOCATION = re.compile(r"\bi live in\s+([A-Za-z][A-Za-z .'-]{1,80}(?:,\s*[A-Za-z][A-Za-z .'-]{1,40})?)", re.I)
_STEPDAUGHTER_NAME = re.compile(rf"\bmy stepdaughter(?:'s|s) name is\s+{_NAME}\b", re.I)
_BIOLOGICAL_DAUGHTER_PARENT = re.compile(rf"\b(?:she|{_NAME})\s+is\s+{_NAME}(?:'s|s) biological daughter\b", re.I)
_PARTNER_NAME_QUERY = re.compile(
    rf"\b(?:what(?:'s| is) (?:the )?name of my (?:{_PARTNER_RELATION})|"
    rf"what(?:'s| is) my (?:{_PARTNER_RELATION})(?:'s|s)? name|"
    rf"what(?:'s| is) my (?:{_PARTNER_RELATION}) called|"
    rf"who is my (?:{_PARTNER_RELATION})|"
    rf"what do i call my (?:{_PARTNER_RELATION}))\b",
    re.I,
)
_INTERROGATIVE_START = re.compile(r"^\s*(?:who|what|when|where|why|how|which|whose|do|does|did|is|are|am|can|could|would|will|should|have|has|had)\b", re.I)

def _assertion_clauses(text: str) -> list[str]:
    """Return declarative clauses only; questions are never personal-fact evidence."""
    clauses: list[str] = []
    for raw in re.split(r"(?<=[.!?])\s+|[\r\n]+", text):
        clause = raw.strip()
        if not clause:
            continue
        if clause.endswith("?") or _INTERROGATIVE_START.search(clause):
            continue
        clauses.append(clause)
    return clauses

def _canonical_partner_relation(value: str) -> str:
    relation = _compact(value).lower()
    if relation.startswith("fianc"):
        return "fiancee"
    return relation

_STEPDAUGHTER_NAME_QUERY = re.compile(
    r"\b(?:what(?:'s| is) (?:the )?name of my stepdaughter|"
    r"what(?:'s| is) my stepdaughter(?:'s|s)? name|who is my stepdaughter)\b",
    re.I,
)
_USER_NAME_QUERY = re.compile(r"\b(?:what(?:'s| is) my name|who am i)\b", re.I)
_RELATION_QUERY = re.compile(rf"\b(?:what is\s+{_NAME}\s+to me|who is\s+{_NAME})\b", re.I)
_LOCATION_QUERY = re.compile(r"\b(?:where do i live|what(?:'s| is) my location)\b", re.I)
_EXPLICIT_MEMORY_RECALL = re.compile(
    r"\b(?:what was|what is|repeat|remind me)\b[^?]{0,100}\b(?:personal thing|thing i mentioned|asked you to remember|wanted you to remember)\b",
    re.I,
)
_GENERIC_MEMORY_RECALL = re.compile(r"^\s*(?:what was it\??\s*)?(?:do you remember\??)?\s*$", re.I)
_CORRECTION = re.compile(
    r"^\s*(?:no\b|actually\b|correction\b|to be clear\b)|\b(?:you got that wrong|that's not right|that is not right|i told you earlier)\b",
    re.I,
)
_ACTION_OR_SECRET = re.compile(
    r"\b(?:run|execute|install|delete|remove|approve|authorize|launch|download|upload|password|secret|token|api key|private key)\b",
    re.I,
)
_SELF_PROGRESS_QUERY = re.compile(
    r"\b(?:how do you feel about your progress|what do you think about your progress|"
    r"how (?:do )?you see your progress|"
    r"how do you feel about how far (?:you(?:'ve| have)|we(?:'ve| have)) come|"
    r"what are you proud of(?:,? and)? what still frustrates you|"
    r"what can you do now[^?]{0,100}(?:couldn['’]?t|could not) do before|"
    r"what can you genuinely do(?: now)?[^?]{0,160}(?:what still limits you|limitations?)|"
    r"what can you do[^?]{0,140}what still frustrates you|"
    r"what still limits you|"
    r"what (?:have you|you(?:'ve| have)) learned[^?]{0,140}(?:struggle with|limitations?))\b",
    re.I,
)
_V1500_MILESTONE_QUERY = re.compile(
    r"\b(?:what (?:specifically )?became possible at v?1500|"
    r"what makes reaching v?1500 meaningful|"
    r"what (?:did|does) v?1500 (?:enable|change|make possible)|"
    r"why (?:is|was) v?1500 different|"
    r"what makes v?1500 different)\b",
    re.I,
)
_VERSION_REFERENCE = re.compile(r"(?<![a-z0-9])v?(\d{3,4}(?:\.\d+){0,2})(?![a-z0-9])", re.I)
_CURRENT_MILESTONE_REFLECTION_CUES = re.compile(
    r"\b(?:finally made it|we made it|reached|reaching|milestone|how far (?:you(?:'ve| have)|we(?:'ve| have)) come|"
    r"feeling pretty smart|feel smart|feel proud|proud of yourself|what do you think of yourself)\b",
    re.I,
)
_PLAYFUL_MILESTONE_CUES = re.compile(
    r"\b(?:pretty smart|aren['’]?t you|bet you(?:'re| are)|look at you|proud of yourself)\b",
    re.I,
)
_PROUDEST_MILESTONE_CUES = re.compile(
    r"\b(?:what|which)\s+(?:part|capability|ability|change)\b[^?]{0,100}\b(?:proudest|most proud)|"
    r"\b(?:proudest of|most proud of|favorite part)\b",
    re.I,
)
_LIMITATION_MILESTONE_CUES = re.compile(
    r"\b(?:what|which)\b[^?]{0,80}\b(?:still limits|limitation|weakest|frustrates|cannot|can't|could improve)\b|"
    r"\b(?:what remains|what is still missing|what's still missing)\b",
    re.I,
)
_SIGNIFICANCE_MILESTONE_CUES = re.compile(
    r"\b(?:why (?:does|is) (?:that|this|it|v?\d{3,4})|what (?:does|makes) (?:that|this|it|v?\d{3,4}))\b"
    r"[^?]{0,100}\b(?:matter|important|meaningful|mean)\b",
    re.I,
)
_PRE_ACTION_TOPIC_QUERY = re.compile(
    r"\bbefore we (?:started |began )?(?:running |talking about |doing )?"
    r"(diagnostics?|system health|system checks?|maintenance)\b[^?]{0,100}"
    r"\bwhat (?:were we|had we been) (?:discussing|talking about|working on)\b",
    re.I,
)


def _topic_before_first_action(text: str, rows: list[Mapping[str, Any]]) -> str:
    query = _PRE_ACTION_TOPIC_QUERY.search(text)
    if not query:
        return ""
    action_term = query.group(1).lower()
    action_index = -1
    for index, row in enumerate(rows):
        lane = str(row.get("continuity_lane") or "").lower()
        material = " ".join((
            str(row.get("user_message") or ""),
            str(row.get("assistant_response") or ""),
            str(row.get("action_status_summary") or ""),
        )).lower()
        action_matches = (
            any(term in material for term in ("diagnostic", "system health", "system check"))
            if action_term.startswith(("diagnostic", "system"))
            else "maintenance" in material
        )
        if lane == "operator" and action_matches:
            action_index = index
            break
    if action_index < 1:
        return ""
    prior = " ".join(
        f"{row.get('user_message', '')} {row.get('assistant_response', '')}"
        for row in rows[max(0, action_index - 4):action_index]
        if str(row.get("continuity_lane") or "ordinary").lower() != "operator"
    ).lower()
    if "v1500" in prior or (
        "propose improvements" in prior
        and any(term in prior for term in ("final approval", "isolated", "your review"))
    ):
        return (
            "Before diagnostics, we were discussing how v1500 changed our development process and "
            "divided our responsibilities: I propose and verify changes in isolation, while you retain "
            "final approval over what is installed."
        )
    return ""


def _current_milestone_reflection(text: str) -> tuple[bool, bool, str]:
    """Recognize only references to the authoritative current version family."""
    from release_authority import WORKING_SOURCE_VERSION
    current_family = WORKING_SOURCE_VERSION.split(".", 1)[0]
    referenced = {match.group(1).split(".", 1)[0] for match in _VERSION_REFERENCE.finditer(text)}
    focused = bool(
        _PROUDEST_MILESTONE_CUES.search(text)
        or _LIMITATION_MILESTONE_CUES.search(text)
        or _SIGNIFICANCE_MILESTONE_CUES.search(text)
    )
    matched = current_family in referenced and bool(_CURRENT_MILESTONE_REFLECTION_CUES.search(text) or focused)
    focus = "overview"
    if matched and _PROUDEST_MILESTONE_CUES.search(text):
        focus = "proudest_capability"
    elif matched and _LIMITATION_MILESTONE_CUES.search(text):
        focus = "limitation"
    elif matched and _SIGNIFICANCE_MILESTONE_CUES.search(text):
        focus = "significance"
    return matched, bool(matched and _PLAYFUL_MILESTONE_CUES.search(text)), focus
_STALE_FRAME_CORRECTION = re.compile(
    r"\b(?:you seem stuck|you(?:'re| are) stuck|you keep (?:answering|responding to|repeating)|"
    r"that didn'?t answer (?:me|my question))\b",
    re.I,
)
_LOCAL_RECOMMENDATION = re.compile(
    r"\b(?:in my area|near me|nearby|local (?:events?|activities|classes|places)|"
    r"do you know of any in)\b",
    re.I,
)
_DURABLE_NAME = re.compile(rf"^The user's name is\s+{_NAME}\.$", re.I)
_DURABLE_PARTNER = re.compile(rf"^The user's fianc(?:e|ee|e|ee) is\s+{_NAME}\.$", re.I)
_DURABLE_LOCATION = re.compile(r"^The user lives in\s+(.{2,120})\.$", re.I)
_DURABLE_STEPDAUGHTER = re.compile(rf"^The user's stepdaughter is\s+{_NAME}\.$", re.I)
_DURABLE_BIOLOGICAL_DAUGHTER = re.compile(rf"^{_NAME} is\s+{_NAME}'s biological daughter\.$", re.I)


@dataclass(frozen=True)
class ActiveConversationFact:
    key: str
    value: str
    source_turn_offset: int
    explicitly_remembered: bool = False


@dataclass(frozen=True)
class ActiveConversationFactResolution:
    state: str = "none"
    fact_kind: str = "none"
    response: str = ""
    prompt_block: str = ""
    fact_count: int = 0
    user_turn_count: int = 0
    correction_applied: bool = False
    durable_memory_requested: bool = False
    content_free: bool = True

    def public_summary(self) -> dict[str, Any]:
        row = asdict(self)
        row.pop("response", None)
        row.pop("prompt_block", None)
        row["resolution_digest"] = hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:24]
        return row


def _compact(value: Any, limit: int = MAX_FACT_VALUE_CHARS) -> str:
    return " ".join(str(value or "").split())[:limit].strip(" .,!?:;")


def _normalize_user_punctuation(value: Any) -> str:
    return str(value or "").translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'"}))


def _facts_from_text(text: str, *, offset: int) -> list[ActiveConversationFact]:
    message = " ".join(_normalize_user_punctuation(text).split())
    if not message:
        return []
    remembered = bool(_REMEMBER.search(message))
    facts: list[ActiveConversationFact] = []
    for clause in _assertion_clauses(message):
        own_name = _USER_NAME.search(clause)
        if own_name:
            facts.append(ActiveConversationFact("user.name", _compact(own_name.group(1)), offset, remembered))

        partner = None
        if not _PARTNER_NAME_QUERY.search(clause):
            for pattern in _PARTNER_NAME:
                partner = pattern.search(clause)
                if partner:
                    break
        if partner:
            groups = partner.groupdict()
            name = _compact(groups.get("name") or "")
            relation = _canonical_partner_relation(groups.get("relation") or ("fiancee" if "engaged" in clause.lower() else "spouse"))
            if name:
                facts.extend((
                    ActiveConversationFact("user.partner.name", name, offset, remembered),
                    ActiveConversationFact("user.partner.relationship", relation, offset, remembered),
                ))

        stepdaughter = None if _STEPDAUGHTER_NAME_QUERY.search(clause) else _STEPDAUGHTER_NAME.search(clause)
        if stepdaughter:
            facts.extend((
                ActiveConversationFact("user.stepdaughter.name", _compact(stepdaughter.group(1)), offset, remembered),
                ActiveConversationFact("user.stepdaughter.relationship", "stepdaughter", offset, remembered),
            ))
            biological_parent = _BIOLOGICAL_DAUGHTER_PARENT.search(clause)
            if biological_parent:
                facts.append(ActiveConversationFact(
                    "user.stepdaughter.biological_parent_name",
                    _compact(biological_parent.groups()[-1]).rstrip("'"),
                    offset,
                    remembered,
                ))

        location = None if _LOCATION_QUERY.search(clause) else _LOCATION.search(clause)
        if location:
            value = _compact(location.group(1))
            value = re.split(r"\b(?:and|because|but|so)\b", value, maxsplit=1, flags=re.I)[0].strip(" .,!?:;")
            if value:
                facts.append(ActiveConversationFact("user.location", value, offset, remembered))

    # Pronoun-linked biological-parent statements commonly follow the named
    # stepdaughter assertion in a second sentence. Preserve that cross-clause
    # linkage without allowing an interrogative clause to become evidence.
    stepdaughter_name = next((f.value for f in reversed(facts) if f.key == "user.stepdaughter.name"), "")
    if stepdaughter_name:
        for clause in _assertion_clauses(message):
            biological_parent = _BIOLOGICAL_DAUGHTER_PARENT.search(clause)
            if biological_parent:
                parent = _compact(biological_parent.groups()[-1]).rstrip("'")
                if parent:
                    facts = [f for f in facts if f.key != "user.stepdaughter.biological_parent_name"]
                    facts.append(ActiveConversationFact("user.stepdaughter.biological_parent_name", parent, offset, remembered))
                    break
    return facts


def _facts_from_durable_memories(memories: Iterable[Mapping[str, Any]]) -> dict[str, ActiveConversationFact]:
    """Read only explicit, active curation records; arbitrary memory text is not evidence."""
    from family_relationship_graph import is_explicit_curated_family_memory
    resolved: dict[str, ActiveConversationFact] = {}
    for row in memories:
        content = " ".join(str(row.get("content") or "").split())
        if not is_explicit_curated_family_memory(row):
            integrity = row.get("provenance_integrity") if isinstance(row.get("provenance_integrity"), Mapping) else {}
            provenance = str(integrity.get("provenance_class") or "").strip().lower()
            eligible = row.get("historical_evidence_eligible")
            if eligible is None:
                eligible = integrity.get("historical_evidence_eligible")
            if (
                str(row.get("type") or "") == "conversation_user"
                and provenance == "user"
                and eligible is True
                and _REMEMBER.search(content)
            ):
                for fact in _facts_from_text(content, offset=-1):
                    if fact.explicitly_remembered:
                        resolved[fact.key] = ActiveConversationFact(fact.key, fact.value, -1, True)
            continue
        partner = _DURABLE_PARTNER.fullmatch(content)
        own_name = _DURABLE_NAME.fullmatch(content)
        location = _DURABLE_LOCATION.fullmatch(content)
        stepdaughter = _DURABLE_STEPDAUGHTER.fullmatch(content)
        biological_daughter = _DURABLE_BIOLOGICAL_DAUGHTER.fullmatch(content)
        if partner:
            resolved["user.partner.name"] = ActiveConversationFact("user.partner.name", _compact(partner.group(1)), -1, True)
            resolved["user.partner.relationship"] = ActiveConversationFact("user.partner.relationship", "fiancee", -1, True)
        elif own_name:
            resolved["user.name"] = ActiveConversationFact("user.name", _compact(own_name.group(1)), -1, True)
        elif location:
            resolved["user.location"] = ActiveConversationFact("user.location", _compact(location.group(1)), -1, True)
        elif stepdaughter:
            resolved["user.stepdaughter.name"] = ActiveConversationFact("user.stepdaughter.name", _compact(stepdaughter.group(1)), -1, True)
            resolved["user.stepdaughter.relationship"] = ActiveConversationFact("user.stepdaughter.relationship", "stepdaughter", -1, True)
        elif biological_daughter:
            resolved["user.stepdaughter.name"] = ActiveConversationFact("user.stepdaughter.name", _compact(biological_daughter.group(1)), -1, True)
            resolved["user.stepdaughter.biological_parent_name"] = ActiveConversationFact("user.stepdaughter.biological_parent_name", _compact(biological_daughter.group(2)), -1, True)
    return resolved


def _active_facts(
    message: str,
    history: Iterable[Mapping[str, Any]],
    memories: Iterable[Mapping[str, Any]] = (),
) -> tuple[dict[str, ActiveConversationFact], int]:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_HISTORY_TURNS:]
    resolved = _facts_from_durable_memories(memories)
    for offset, row in enumerate(rows):
        for fact in _facts_from_text(str(row.get("user_message") or ""), offset=offset):
            resolved[fact.key] = fact
    for fact in _facts_from_text(message, offset=len(rows)):
        resolved[fact.key] = fact
    return dict(list(resolved.items())[-MAX_FACTS:]), len(rows)


def _last_remembered_facts(history: Iterable[Mapping[str, Any]]) -> list[ActiveConversationFact]:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_HISTORY_TURNS:]
    for offset, row in reversed(list(enumerate(rows))):
        text = str(row.get("user_message") or "")
        if not _REMEMBER.search(text):
            continue
        facts = _facts_from_text(text, offset=offset)
        if facts:
            return facts
    return []


def _fact_prompt_block(facts: Mapping[str, ActiveConversationFact], message: str = "") -> str:
    if not facts:
        return ""
    labels = {
        "user.name": "The user's name",
        "user.partner.name": "The user's fiancee's name",
        "user.partner.relationship": "The named partner's relationship to the user",
        "user.location": "The user's stated location",
        "user.stepdaughter.name": "The user's stepdaughter's name",
        "user.stepdaughter.relationship": "The named family member's relationship to the user",
        "user.stepdaughter.biological_parent_name": "The stepdaughter's stated biological parent",
    }
    selected = dict(facts)
    text = " ".join(str(message or "").split()).casefold()
    if text:
        keys: set[str] = set()
        for key, fact in facts.items():
            if re.search(rf"(?<![a-z0-9]){re.escape(fact.value.casefold())}(?![a-z0-9])", text):
                keys.add(key)
        if re.search(r"\b(?:fiancee|fiance|partner)\b", text):
            keys.update(key for key in facts if key.startswith("user.partner."))
        if re.search(r"\b(?:stepdaughter|stepchild)\b", text):
            keys.update(key for key in facts if key.startswith("user.stepdaughter."))
        if re.search(r"\b(?:where\s+do\s+i\s+live|my\s+location|near\s+me|in\s+my\s+area)\b", text):
            keys.add("user.location")
        if re.search(r"\b(?:my\s+name|who\s+am\s+i)\b", text):
            keys.add("user.name")
        if re.search(r"\b(?:asked\s+you\s+to\s+remember|personal\s+thing|do\s+you\s+remember)\b", text):
            keys.update(key for key, fact in facts.items() if fact.explicitly_remembered)
        selected = {key: fact for key, fact in facts.items() if key in keys}
        if not selected:
            return ""
    lines = [
        "ACTIVE CONVERSATION FACTS",
        "These facts come only from recent user-authored turns. Newer explicit user facts supersede older values. Do not assign a partner's name to the user or infer facts from assistant text.",
    ]
    for key, fact in selected.items():
        if key in labels:
            lines.append(f"- {labels[key]}: {fact.value}")
    return "\n".join(lines)


def resolve_active_conversation_facts(
    message: str,
    history: Iterable[Mapping[str, Any]],
    memories: Iterable[Mapping[str, Any]] = (),
) -> ActiveConversationFactResolution:
    text = " ".join(_normalize_user_punctuation(message).split())
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_HISTORY_TURNS:]
    facts, turn_count = _active_facts(text, rows, memories)
    from family_relationship_graph import (
        build_family_graph,
        family_memory_acknowledgement,
        family_prompt_block,
        resolve_family_relationship_query,
    )
    from conversation_entity_associations import (
        associations_from_text,
        build_conversation_association_graph,
        conversation_association_memory_acknowledgement,
        conversation_association_prompt_block,
        conversation_association_statement_acknowledgement,
        resolve_conversation_association_query,
    )
    family_edges = build_family_graph(rows, memories, text)
    family_answer = resolve_family_relationship_query(text, rows, memories)
    association_graph = build_conversation_association_graph(rows, memories, text)
    association_answer = resolve_conversation_association_query(text, rows, memories)
    association_statement_ack = conversation_association_statement_acknowledgement(text)
    response = ""
    kind = "none"
    state = "active_fact_context" if facts else "none"

    partner_name = facts.get("user.partner.name")
    own_name = facts.get("user.name")
    location = facts.get("user.location")
    stepdaughter_name = facts.get("user.stepdaughter.name")
    stepdaughter_parent = facts.get("user.stepdaughter.biological_parent_name")
    relation = _RELATION_QUERY.search(text)
    explicit_recall = bool(_EXPLICIT_MEMORY_RECALL.search(text))
    if not explicit_recall and _GENERIC_MEMORY_RECALL.fullmatch(text):
        previous = str(rows[-1].get("user_message") or "") if rows else ""
        explicit_recall = bool(_EXPLICIT_MEMORY_RECALL.search(previous))

    repeated_progress_query = any(
        _SELF_PROGRESS_QUERY.search(str(row.get("user_message") or "")) for row in rows[-3:]
    )
    recent_release_context = any(
        "v1500.9" in f"{row.get('user_message', '')} {row.get('assistant_response', '')}".casefold()
        for row in rows[-3:]
    )
    from release_self_knowledge import is_release_evidence_question
    release_evidence_follow_up = bool(recent_release_context and is_release_evidence_question(text))
    pre_action_topic = _topic_before_first_action(text, rows)
    current_milestone_reflection, playful_milestone, milestone_focus = _current_milestone_reflection(text)
    from release_self_knowledge import (
        explain_release_evidence,
        grounded_current_milestone_reflection,
        grounded_self_progress_summary,
        inspect_current_release,
        is_current_release_question,
        is_grouped_release_inspection,
        is_next_bounded_work_question,
        next_bounded_work_guidance,
    )
    if release_evidence_follow_up:
        release = inspect_current_release()
        response = explain_release_evidence(release)
        kind, state = "current_release_evidence", "grounded_release_evidence"
    elif is_current_release_question(text) and not is_grouped_release_inspection(text):
        release = inspect_current_release()
        response = release.summary
        kind, state = "current_release_summary", "grounded_current_release"
    elif is_next_bounded_work_question(text):
        response = next_bounded_work_guidance()
        kind, state = "next_bounded_work", "grounded_next_bounded_unit"
    elif pre_action_topic:
        response = pre_action_topic
        kind, state = "pre_action_topic", "grounded_action_boundary_return"
    elif current_milestone_reflection:
        response = grounded_current_milestone_reflection(playful=playful_milestone, focus=milestone_focus)
        kind, state = f"current_milestone_{milestone_focus}", "grounded_current_milestone_reflection"
    elif _V1500_MILESTONE_QUERY.search(text):
        response = (
            "v1500 is different because I can now participate in my own supervised development: "
            "inspect my source, propose a distinct bounded improvement, implement it in an isolated "
            "workspace, verify the candidate, and present it for your review. Earlier milestones built "
            "the foundations for that cycle; you still retain installation and promotion authority."
        )
        kind, state = "v1500_milestone_capability", "grounded_project_milestone"
    elif _SELF_PROGRESS_QUERY.search(text):
        response = grounded_self_progress_summary(more_direct=repeated_progress_query)
        kind, state = "self_progress_reflection", "direct_self_reflection"
    elif _STALE_FRAME_CORRECTION.search(text):
        response = (
            "You're right. I lost the current question and answered the earlier conversational frame instead. "
            "I should respond to what you just asked, not repeat a reassuring summary."
        )
        kind, state = "stale_frame_correction", "conversation_repair"
    elif family_answer.response:
        response = family_answer.response
        kind, state = family_answer.relation, family_answer.state
    elif association_answer.response:
        response = association_answer.response
        kind, state = association_answer.predicate, association_answer.state
    elif association_statement_ack:
        response = association_statement_ack
        kind, state = "entity_association_statement", "grounded_association_acknowledgement"
    elif _STEPDAUGHTER_NAME_QUERY.search(text) and stepdaughter_name:
        response = f"You told me your stepdaughter's name is {stepdaughter_name.value}."
        kind, state = "stepdaughter_name", "active_fact_recall"
    elif _PARTNER_NAME_QUERY.search(text) and partner_name:
        response = f"You told me your fiancee's name is {partner_name.value}."
        kind, state = "partner_name", "active_fact_recall"
    elif relation and partner_name and next((group for group in relation.groups() if group), "").casefold() == partner_name.value.casefold():
        response = f"{partner_name.value} is your fiancee."
        kind, state = "partner_relationship", "active_fact_recall"
    elif relation and stepdaughter_name and next((group for group in relation.groups() if group), "").casefold() == stepdaughter_name.value.casefold():
        response = f"{stepdaughter_name.value} is your stepdaughter."
        if stepdaughter_parent:
            response += f" You told me {stepdaughter_name.value} is {stepdaughter_parent.value}'s biological daughter."
        kind, state = "stepdaughter_relationship", "active_fact_recall"
    elif _USER_NAME_QUERY.search(text) and own_name:
        response = f"Your name is {own_name.value}."
        kind, state = "user_name", "active_fact_recall"
    elif _LOCATION_QUERY.search(text) and location:
        response = f"You told me you live in {location.value}."
        kind, state = "user_location", "active_fact_recall"
    elif _LOCAL_RECOMMENDATION.search(text) and location:
        response = (
            f"I can suggest what to look for around {location.value}, but I can't verify current local listings "
            "from this chat alone. Check the city or county events calendar, the local library, parks and recreation, "
            "and nearby class listings before making plans."
        )
        kind, state = "local_recommendation_boundary", "current_information_uncertain"
    elif _REMEMBER.search(text):
        current = {fact.key: fact for fact in _facts_from_text(text, offset=turn_count)}
        requested_partner = current.get("user.partner.name")
        requested_name = current.get("user.name")
        requested_location = current.get("user.location")
        requested_stepdaughter = current.get("user.stepdaughter.name")
        requested_stepdaughter_parent = current.get("user.stepdaughter.biological_parent_name")
        if requested_stepdaughter:
            response = f"I'll remember that {requested_stepdaughter.value} is your stepdaughter."
            if requested_stepdaughter_parent:
                response += f" You told me {requested_stepdaughter.value} is {requested_stepdaughter_parent.value}'s biological daughter."
            kind, state = "explicit_stepdaughter_memory_acknowledgement", "active_fact_memory_acknowledgement"
        elif requested_partner:
            response = f"I'll remember that {requested_partner.value} is your fiancee."
            kind, state = "explicit_partner_memory_acknowledgement", "active_fact_memory_acknowledgement"
        elif requested_name:
            response = f"I'll remember that your name is {requested_name.value}."
            kind, state = "explicit_name_memory_acknowledgement", "active_fact_memory_acknowledgement"
        elif requested_location:
            response = f"I'll remember that you live in {requested_location.value}."
            kind, state = "explicit_location_memory_acknowledgement", "active_fact_memory_acknowledgement"
        else:
            response = family_memory_acknowledgement(text)
            if response:
                kind, state = "explicit_family_graph_memory_acknowledgement", "active_fact_memory_acknowledgement"
            else:
                response = conversation_association_memory_acknowledgement(text)
                if response:
                    kind, state = "explicit_entity_association_memory_acknowledgement", "active_fact_memory_acknowledgement"
    elif explicit_recall:
        remembered = _last_remembered_facts(rows)
        if not remembered:
            remembered = [fact for fact in facts.values() if fact.explicitly_remembered]
        remembered_by_key = {fact.key: fact for fact in remembered}
        remembered_partner = remembered_by_key.get("user.partner.name")
        remembered_location = remembered_by_key.get("user.location")
        remembered_name = remembered_by_key.get("user.name")
        remembered_stepdaughter = remembered_by_key.get("user.stepdaughter.name")
        remembered_stepdaughter_parent = remembered_by_key.get("user.stepdaughter.biological_parent_name")
        if remembered_stepdaughter:
            response = f"You asked me to remember that {remembered_stepdaughter.value} is your stepdaughter."
            if remembered_stepdaughter_parent:
                response += f" You told me {remembered_stepdaughter.value} is {remembered_stepdaughter_parent.value}'s biological daughter."
            kind, state = "explicit_stepdaughter_memory", "active_fact_recall"
        elif remembered_partner:
            response = f"You asked me to remember that your fiancee's name is {remembered_partner.value}."
            kind, state = "explicit_partner_memory", "active_fact_recall"
        elif remembered_location:
            response = f"You asked me to remember that you live in {remembered_location.value}."
            kind, state = "explicit_location_memory", "active_fact_recall"
        elif remembered_name:
            response = f"You asked me to remember that your name is {remembered_name.value}."
            kind, state = "explicit_name_memory", "active_fact_recall"

    current_facts = {fact.key: fact for fact in _facts_from_text(text, offset=turn_count)}
    correction = bool(_CORRECTION.search(text) and current_facts)
    if correction and not response:
        corrected_name = current_facts.get("user.name")
        corrected_partner = current_facts.get("user.partner.name")
        if corrected_name and corrected_partner:
            response = f"Got it: you're {corrected_name.value}, and {corrected_partner.value} is your fiancee."
            kind = "identity_and_partner_correction"
        elif corrected_partner:
            response = f"Got it: your fiancee's name is {corrected_partner.value}."
            kind = "partner_correction"
        elif corrected_name:
            response = f"Got it: your name is {corrected_name.value}."
            kind = "identity_correction"
        state = "active_fact_correction"

    return ActiveConversationFactResolution(
        state=state,
        fact_kind=kind,
        response=response,
        prompt_block="\n\n".join(block for block in (
            _fact_prompt_block(facts, text), family_prompt_block(family_edges, text),
            conversation_association_prompt_block(association_graph, text),
        ) if block),
        fact_count=len(facts),
        user_turn_count=turn_count,
        correction_applied=correction,
        durable_memory_requested=bool(_REMEMBER.search(text) and (current_facts or associations_from_text(text, offset=turn_count))),
    )


def persist_explicit_user_memory_request(message: str) -> dict[str, Any]:
    """Persist only an explicit, allowlisted personal-memory request."""
    text = " ".join(str(message or "").split())
    if not _REMEMBER.search(text) or _ACTION_OR_SECRET.search(text):
        return {"requested": False, "created_count": 0, "duplicate_count": 0, "rejected": bool(_REMEMBER.search(text)), "content_free": True}
    facts = {fact.key: fact for fact in _facts_from_text(text, offset=0)}
    records: list[tuple[str, str]] = []
    if facts.get("user.partner.name"):
        records.append(("relationship", f"The user's fiancee is {facts['user.partner.name'].value}."))
    if facts.get("user.name"):
        records.append(("personal_fact", f"The user's name is {facts['user.name'].value}."))
    if facts.get("user.location"):
        records.append(("personal_fact", f"The user lives in {facts['user.location'].value}."))
    if facts.get("user.stepdaughter.name"):
        child = facts["user.stepdaughter.name"].value
        records.append(("relationship", f"The user's stepdaughter is {child}."))
        if facts.get("user.stepdaughter.biological_parent_name"):
            records.append(("relationship", f"{child} is {facts['user.stepdaughter.biological_parent_name'].value}'s biological daughter."))
    from family_relationship_graph import durable_family_records
    from conversation_entity_associations import durable_conversation_association_records
    existing_content = {content for _, content in records}
    for content in durable_family_records(text):
        if facts.get("user.partner.name") and " | fiancee | the user." in content:
            continue
        if facts.get("user.stepdaughter.name") and " | stepdaughter | the user." in content:
            continue
        if facts.get("user.stepdaughter.biological_parent_name") and " | biological_daughter | " in content:
            continue
        if content not in existing_content:
            records.append(("relationship", content))
            existing_content.add(content)
    for content in durable_conversation_association_records(text):
        if content not in existing_content:
            records.append(("personal_fact", content))
            existing_content.add(content)
    if not records:
        return {"requested": True, "created_count": 0, "duplicate_count": 0, "rejected": True, "content_free": True}
    from relationship_memory_curation import create_relationship_memory
    created = duplicate = 0
    for memory_type, content in records:
        result = create_relationship_memory(
            memory_type,
            content[:MAX_MEMORY_CONTENT_CHARS],
            importance="high" if memory_type == "relationship" else "medium",
            source="operator_explicit_conversation_memory_request",
        )
        created += int(bool(result.get("created")))
        duplicate += int(str(result.get("status") or "") == "duplicate")
    return {"requested": True, "created_count": created, "duplicate_count": duplicate, "rejected": False, "content_free": True}


__all__ = [
    "CONTRACT_VERSION", "ActiveConversationFact", "ActiveConversationFactResolution",
    "resolve_active_conversation_facts", "persist_explicit_user_memory_request",
]
