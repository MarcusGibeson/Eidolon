from __future__ import annotations

"""Bounded newest-turn targeting and provider-neutral repetition resistance."""

from difflib import SequenceMatcher
import hashlib
import json
import re
from typing import Any, Iterable

CONTRACT_VERSION = "v1500.9"
MAX_HISTORY_RECORDS = 12
MAX_ANALYSIS_CHARS = 4096
_WORDS = re.compile(r"[a-z0-9']+")
_SENTENCES = re.compile(r"(?<=[.!?])\s+")
_SHORT_FOLLOW_UPS = {
    "why", "why is that", "how", "how so", "explain", "explain further",
    "tell me more", "what do you mean", "what about that", "what about it",
}
_TOPIC_SHIFTS = (
    "new topic", "different topic", "switching topics", "separately", "unrelated",
    "moving on", "instead lets", "instead let's",
)
_CORRECTION_CUES = (
    "actually", "no ", "no.", "that's wrong", "thats wrong", "i meant",
    "not ", "don't ", "dont ", "do not ", "that isn't", "that isnt",
    "that's not", "thats not", "you misunderstood", "you seem stuck", "you repeated",
)
_SHARED_RESPONSIBILITY_REJECTION = re.compile(
    r"\b(?:don['’]?t|do not|not to)\b[^.!?]{0,100}\b(?:shared responsibility|make (?:this|it) shared|"
    r"make (?:this|it) (?:our|both of our)|put (?:this|it) on (?:both of us|me))\b",
    re.IGNORECASE,
)
_SHARED_RESPONSIBILITY_CLOSING = re.compile(
    r"\b(?:let['’]?s|let us|we can|we should)\b[^.!?]{0,120}\b(?:work|make|find|improve|fix|ensure|do better)\b|"
    r"\b(?:work|make|find|improve|fix|do better)\b[^.!?]{0,80}\btogether\b",
    re.IGNORECASE,
)
_SPECIFIC_MISTAKE_QUERY = re.compile(
    r"\b(?:what|which)\b[^.!?]{0,80}\b(?:specific|exact|precise|precisely|concrete)\b[^.!?]{0,80}\b(?:mistake|misstep|error|wrong)\b|"
    r"\b(?:be precise|be specific)\b[^.!?]{0,100}\b(?:what did you do|what happened|caused me to feel unheard)\b",
    re.IGNORECASE,
)
_HYPOTHETICAL_MISTAKE_LANGUAGE = re.compile(
    r"\b(?:if|might|may|perhaps|maybe|could have)\b[^.!?]{0,100}\b(?:response|misstep|mistake|felt|feel|listening|address|acknowledge)\b",
    re.IGNORECASE,
)
_PRESENT_STAKES_QUERY = re.compile(
    r"\b(?:why (?:does|should) (?:that|this|it) matter|why is (?:that|this|it) important|"
    r"what does (?:that|this|it) mean)\b[^?!.]{0,80}\b(?:to|for) me\b[^?!.]{0,40}\b(?:right )?now\b",
    re.IGNORECASE,
)
_PRESENT_STAKES_GENERIC_ADVICE = re.compile(
    r"\b(?:reflect(?:ing)? on (?:your )?(?:feelings|experiences)|help you understand how you(?:'re| are) handling|"
    r"this awareness|appreciate your efforts more fully|celebrate your achievements|find(?:ing)? ways to (?:approach|manage|balance)|"
    r"manage (?:those |your )?(?:mixed )?emotions|clearer mindset|part of the human experience)\b",
    re.IGNORECASE,
)
_PRESENT_STAKES_EVIDENCE = re.compile(
    r"\b(?:i|i'm|i've|i was|me|my|we|we're|we've|our|you|you're|you've|your)\b|"
    r"\b(?:proud|worn out|tired|exhausted|relieved|excited|frustrated|hurt|worried|afraid|"
    r"finally|milestone|setback|failure|failed|distracted|today|right now)\b",
    re.IGNORECASE,
)


def _repair_subject(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    """Recover only bounded repair categories, never arbitrary transcript text."""
    recent = " ".join(
        f"{row['user_message']} {row['assistant_response']}" for row in rows[-8:]
    ).lower()
    subjects: list[str] = []
    if any(cue in recent for cue in (
        "losing the conversational target", "lose the conversational target",
        "losing track", "lost track", "stuck on my first message",
        "answering an older", "answer instead of responding",
    )):
        subjects.append("lost_target")
    if any(cue in recent for cue in (
        "repeating a polished answer", "repeated", "repeating", "repeat myself",
        "generic reassurance", "generic or repeated",
    )):
        subjects.append("repeated_answer")
    return tuple(subjects)


def _grounded_mistake_answer(subjects: tuple[str, ...]) -> str:
    if "lost_target" in subjects and "repeated_answer" in subjects:
        return (
            "The specific mistake was losing track of your current question and falling back to "
            "generic or repeated answers instead of responding to what you actually said."
        )
    if "lost_target" in subjects:
        return "The specific mistake was losing track of your current question and answering around what you actually said."
    if "repeated_answer" in subjects:
        return "The specific mistake was repeating a generic answer instead of responding directly to what you actually said."
    return ""


def _present_stakes_evidence(rows: list[dict[str, Any]]) -> tuple[str, int]:
    """Select recent user-authored circumstances without persisting them publicly."""
    candidates: list[tuple[int, int, str]] = []
    for row_offset, row in enumerate(reversed(rows[-6:])):
        for sentence_offset, sentence in enumerate(_SENTENCES.split(row["user_message"])):
            sentence = " ".join(sentence.split()).strip()
            if not sentence or sentence.endswith("?") or len(sentence) > 240:
                continue
            matches = len(_PRESENT_STAKES_EVIDENCE.findall(sentence))
            if matches:
                candidates.append((matches * 10 - row_offset, sentence_offset, sentence))
        if candidates:
            break
    selected = sorted(candidates, key=lambda item: (-item[0], item[1]))[:2]
    if not selected:
        return "", 0
    evidence = " ".join(item[2] for item in sorted(selected, key=lambda item: item[1]))
    return evidence[:360].strip(), len(selected)


def _shift_user_evidence_to_companion_voice(evidence: str) -> str:
    """Render bounded user-authored evidence from Eidolon's speaking perspective."""
    clauses: list[str] = []
    for raw_clause in _SENTENCES.split(evidence):
        clause = " ".join(raw_clause.split()).strip().rstrip(".!?")
        clause = re.sub(r"^earlier\s+i\s+(?:said|told you)\s+", "", clause, flags=re.IGNORECASE)
        if not clause:
            continue
        # Protect references to Eidolon before shifting the user's first person.
        clause = re.sub(r"\byou(?:'re| are)\b", "__EID_I_AM__", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\byou(?:'ve| have)\b", "__EID_I_HAVE__", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\byour\b", "__EID_MY__", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\byou\b", "__EID_ME__", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\bi\s+was\b", "you were", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\bi\s+am\b|\bi'm\b", "you are", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\bi\s+have\b|\bi've\b", "you have", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\bmy\b", "your", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\bmine\b", "yours", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\bme\b", "you", clause, flags=re.IGNORECASE)
        clause = re.sub(r"\bi\b", "you", clause, flags=re.IGNORECASE)
        clause = clause.replace("__EID_I_AM__", "I am")
        clause = clause.replace("__EID_I_HAVE__", "I have")
        clause = clause.replace("__EID_MY__", "my")
        clause = clause.replace("__EID_ME__", "me")
        clauses.append(clause[0].lower() + clause[1:] if clause else clause)
    return ", and ".join(clauses[:2])


def _grounded_present_stakes_answer(evidence: str) -> str:
    grounded = _shift_user_evidence_to_companion_voice(evidence)
    if not grounded:
        return ""
    return (
        f"It matters because {grounded}. "
        "You were asking me to stay with you in that specific experience, not coach you through it. "
        "If I turn it into general advice, I miss what you needed from this conversation."
    )


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _normalized(value: Any) -> str:
    return " ".join(_WORDS.findall(str(value or "").lower()[:MAX_ANALYSIS_CHARS]))


def _history_rows(history: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if history is None or isinstance(history, (str, bytes, dict)):
        return []
    rows: list[dict[str, Any]] = []
    for item in history:
        if len(rows) >= MAX_HISTORY_RECORDS:
            break
        if not isinstance(item, dict):
            continue
        user = str(item.get("user_message") or "").strip()
        assistant = str(item.get("assistant_response") or "").strip()
        success = item.get("success")
        state = str(item.get("completion_state") or item.get("status") or "").lower()
        if success is False or state in {"cancelled", "failed", "incomplete", "stale", "retracted"}:
            continue
        if user and assistant:
            rows.append({"user_message": user, "assistant_response": assistant})
    return rows


def build_conversation_target_projection(
    message: str,
    conversation_history: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Describe which conversational target must win without exposing transcript text."""
    normalized = _normalized(message)
    rows = _history_rows(conversation_history)
    short_follow_up = normalized.rstrip("?") in _SHORT_FOLLOW_UPS
    topic_shift = any(cue in normalized for cue in _TOPIC_SHIFTS)
    correction = any(
        normalized == cue.strip() or normalized.startswith(cue) or f" {cue.strip()} " in f" {normalized} "
        for cue in _CORRECTION_CUES
    )
    reject_shared_responsibility = bool(_SHARED_RESPONSIBILITY_REJECTION.search(str(message or "")))
    specific_mistake_query = bool(_SPECIFIC_MISTAKE_QUERY.search(str(message or "")))
    repair_subjects = _repair_subject(rows) if specific_mistake_query else ()
    grounded_mistake_answer = _grounded_mistake_answer(repair_subjects)
    present_stakes_query = bool(_PRESENT_STAKES_QUERY.search(str(message or "")))
    present_stakes_evidence, present_stakes_evidence_count = (
        _present_stakes_evidence(rows) if present_stakes_query else ("", 0)
    )
    question = "?" in str(message or "") or normalized.startswith(
        ("who ", "what ", "when ", "where ", "why ", "how ", "which ", "do ", "does ", "did ", "can ", "could ", "would ", "is ", "are ")
    )
    if topic_shift:
        target_kind = "explicit_topic_shift"
    elif correction:
        target_kind = "current_correction"
    elif short_follow_up:
        target_kind = "short_follow_up"
    elif question:
        target_kind = "current_question"
    else:
        target_kind = "current_statement"
    prompt_section = (
        "CONVERSATION TARGET CONTINUITY\n"
        "Treat the newest user message as the response target. Do not answer an older request instead.\n"
        + (
            "The newest message is a short follow-up; resolve it only against the latest completed user-assistant turn.\n"
            if short_follow_up and rows else ""
        )
        + (
            "The newest message corrects or challenges the prior answer; address the correction directly.\n"
            if correction else ""
        )
        + (
            "The user explicitly rejected shared responsibility; own Eidolon's part and do not append a collaborative fix-it closing.\n"
            if reject_shared_responsibility else ""
        )
        + (
            "The user asks for the specific prior mistake. State the concrete repair subject from recent history; do not make it hypothetical or generic.\n"
            if grounded_mistake_answer else ""
        )
        + (
            "The user asks why this matters to them right now. Name attributable current circumstances and explain the present relational or practical stake; do not give generic emotional-management advice.\n"
            if present_stakes_query else ""
        )
        + (
            "The newest message explicitly changes topic; do not pull the response back to the prior topic.\n"
            if topic_shift else ""
        )
        + "Add new substance. Do not repeat the previous assistant answer as the whole response."
    )
    public = {
        "contract_version": CONTRACT_VERSION,
        "target_kind": target_kind,
        "latest_message_primary": True,
        "short_follow_up": short_follow_up,
        "latest_completed_pair_available": bool(rows),
        "topic_shift": topic_shift,
        "correction": correction,
        "reject_shared_responsibility": reject_shared_responsibility,
        "specific_mistake_query": specific_mistake_query,
        "repair_subject_count": len(repair_subjects),
        "present_stakes_query": present_stakes_query,
        "present_stakes_evidence_count": present_stakes_evidence_count,
        "question": question,
        "history_pairs_considered": len(rows),
        "contains_conversation_text": False,
        "provider_contacted": False,
        "provider_request_added": False,
        "authority_granted": False,
    }
    public["evidence_digest"] = _digest(public)
    return {
        "policy": public,
        "prompt_section": prompt_section,
        "grounded_mistake_answer": grounded_mistake_answer,
        "repair_subjects": repair_subjects,
        "present_stakes_evidence": present_stakes_evidence,
    }


def _similarity(left: str, right: str) -> tuple[float, float]:
    a = _normalized(left)
    b = _normalized(right)
    if not a or not b:
        return 0.0, 0.0
    aset, bset = set(a.split()), set(b.split())
    union = aset | bset
    jaccard = len(aset & bset) / len(union) if union else 0.0
    return jaccard, SequenceMatcher(None, a, b).ratio()


def _fallback(target_kind: str) -> str:
    if target_kind == "current_correction":
        return "You're right. I repeated the earlier answer instead of addressing your correction."
    if target_kind == "short_follow_up":
        return "I repeated the earlier answer instead of adding the explanation you asked for."
    if target_kind == "explicit_topic_shift":
        return "I pulled the conversation back to the previous topic instead of following your new one."
    if target_kind == "current_question":
        return "I repeated my previous answer instead of answering your latest question. I don't have a grounded new answer yet."
    return "I repeated my previous response instead of responding to what you just said."


def enforce_conversation_target_output(
    response: str,
    projection: dict[str, Any] | None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
    *,
    casual_fast_path: bool,
) -> tuple[str, dict[str, Any]]:
    """Remove recent-answer repetition without another provider request."""
    text = str(response or "").strip()
    rows = _history_rows(conversation_history)
    policy = dict((projection or {}).get("policy") or {})
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "applied": False,
        "whole_response_replaced": False,
        "duplicate_sentences_removed": 0,
        "constraint_sentences_removed": 0,
        "grounded_repair_applied": False,
        "present_stakes_grounding_applied": False,
        "present_stakes_evidence_count": int(policy.get("present_stakes_evidence_count") or 0),
        "recent_answers_compared": min(3, len(rows)),
        "maximum_jaccard_percent": 0,
        "maximum_sequence_percent": 0,
        "contains_conversation_text": False,
        "provider_request_added": False,
        "authority_granted": False,
    }
    if not casual_fast_path or not text or not rows:
        diagnostics["diagnostic_digest"] = _digest(diagnostics)
        return text, diagnostics

    recent = [row["assistant_response"] for row in rows[-3:]]
    scores = [_similarity(text, prior) for prior in recent]
    max_jaccard = max((score[0] for score in scores), default=0.0)
    max_sequence = max((score[1] for score in scores), default=0.0)
    diagnostics["maximum_jaccard_percent"] = round(max_jaccard * 100)
    diagnostics["maximum_sequence_percent"] = round(max_sequence * 100)
    whole_duplicate = any(j >= 0.72 and s >= 0.86 for j, s in scores)
    if whole_duplicate:
        text = _fallback(str(policy.get("target_kind") or "current_statement"))
        diagnostics["applied"] = True
        diagnostics["whole_response_replaced"] = True
    else:
        kept: list[str] = []
        removed = 0
        for sentence in _SENTENCES.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
            duplicate = any(
                j >= 0.86 and s >= 0.9
                for j, s in (_similarity(sentence, prior_sentence)
                             for prior in recent
                             for prior_sentence in _SENTENCES.split(prior))
            )
            if duplicate:
                removed += 1
            else:
                kept.append(sentence)
        if removed and kept:
            text = " ".join(kept)
            diagnostics["applied"] = True
            diagnostics["duplicate_sentences_removed"] = removed
    if policy.get("reject_shared_responsibility") and text:
        units = [unit.strip() for unit in _SENTENCES.split(text) if unit.strip()]
        constrained = [unit for unit in units if not _SHARED_RESPONSIBILITY_CLOSING.search(unit)]
        removed = len(units) - len(constrained)
        if removed:
            text = " ".join(constrained) if constrained else _fallback(str(policy.get("target_kind") or "current_correction"))
            diagnostics["applied"] = True
            diagnostics["constraint_sentences_removed"] = removed
    grounded_mistake_answer = str((projection or {}).get("grounded_mistake_answer") or "").strip()
    if grounded_mistake_answer and text:
        normalized_response = _normalized(text)
        subjects = tuple((projection or {}).get("repair_subjects") or ())
        mentions_lost_target = any(term in normalized_response for term in (
            "losing track", "lost track", "current question", "conversational target",
        ))
        mentions_repetition = any(term in normalized_response for term in (
            "repeat", "repeated", "repeating", "generic answer", "generic response",
        ))
        missing_subject = (
            ("lost_target" in subjects and not mentions_lost_target)
            or ("repeated_answer" in subjects and not mentions_repetition)
        )
        if missing_subject or _HYPOTHETICAL_MISTAKE_LANGUAGE.search(text):
            text = grounded_mistake_answer
            diagnostics["applied"] = True
            diagnostics["grounded_repair_applied"] = True
    present_stakes_evidence = str((projection or {}).get("present_stakes_evidence") or "").strip()
    if (
        policy.get("present_stakes_query")
        and present_stakes_evidence
        and _PRESENT_STAKES_GENERIC_ADVICE.search(text)
    ):
        text = _grounded_present_stakes_answer(present_stakes_evidence)
        diagnostics["applied"] = True
        diagnostics["present_stakes_grounding_applied"] = True
    diagnostics["diagnostic_digest"] = _digest(diagnostics)
    return text, diagnostics
