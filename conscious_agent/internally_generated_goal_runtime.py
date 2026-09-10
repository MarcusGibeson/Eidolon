from __future__ import annotations

"""Bounded ordinary-conversation projection for internally generated goal candidates.

This v1170.0-v1170.2 layer reuses the retained v1133 goal-governance vocabulary
without writing its stores or activating any historical goal, plan, initiative,
or action path. It consumes only bounded structural evidence and produces a
content-free operator-review candidate that remains subordinate to the literal
current request and every existing authority boundary.
"""

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from memory_experiential_learning_alpha import verify_memory_experiential_learning_alpha_diagnostics

# Retained v1133 goal-governance vocabularies. They are repeated here as immutable
# contract sets so the ordinary runtime does not import or initialize the historical
# persistence stores merely to classify a read-only candidate projection.
SOURCE_CATEGORIES = {
    "motivation", "inquiry_outcome", "world_model_outcome", "memory", "concern",
    "obligation", "unfinished_thought", "goal_predecessor",
}
PURPOSE_CATEGORIES = {
    "capability_improvement", "reliability", "knowledge", "relationship_continuity",
    "project_progress", "self_understanding", "maintenance", "deliberate_no_goal_review",
}

CONTRACT_VERSION = "1170.2"
MAX_COMPONENT_BYTES = 262_144
MAX_OBSERVATION_ROWS = 32
MAX_PRIOR_RECEIPTS = 64
MAX_RECEIPT_BYTES = 16_384
MAX_PROMPT_CHARS = 3200
MAX_CURRENT_MESSAGE_BYTES = 32_768
MAX_OBSERVATION_MESSAGE_BYTES = 16_384
MAX_EVIDENCE_COUNT = 64
MAX_SOURCE_CATEGORIES = 8
STALE_RECEIPT_DAYS = 90

CANDIDATE_TYPES = (
    "none",
    "capability_improvement",
    "reliability_improvement",
    "coherence_repair",
    "knowledge_improvement",
    "interaction_quality_improvement",
    "maintenance_improvement",
)
DEFICIENCY_CLASSES = (
    "none",
    "operator_confirmed_problem",
    "missing_capability",
    "repeated_failure",
    "test_or_diagnostic_failure",
    "reliability_weakness",
    "unresolved_contradiction",
    "repeated_correction",
    "maintenance_need",
)
EVIDENCE_SOURCE_CATEGORIES = (
    "current_request",
    "verified_memory_learning_recovery",
    "prior_operator_problem",
    "prior_correction",
    "provider_failure",
    "test_failure",
    "runtime_diagnostic",
    "verified_goal_receipt",
)
CONFIDENCE_BANDS = ("none", "low", "medium", "high")
IMPACT_BANDS = ("none", "low", "medium", "high")
COST_BANDS = ("unknown", "low", "medium", "high")
RISK_BANDS = ("unknown", "low", "medium", "high")
SCOPE_BANDS = ("none", "conversation", "project", "system")

_CANDIDATE_FIELDS = {
    "contract_version", "candidate_type", "purpose_category", "deficiency_class",
    "legacy_signal_source_categories", "evidence_source_categories", "evidence_count",
    "confidence_band", "impact_band", "cost_band", "risk_band", "scope_band",
    "current_request_relevant", "review_required", "operator_approval_required",
    "goal_activation_permitted", "plan_creation_permitted", "tool_routing_permitted",
    "action_execution_permitted", "source_editing_permitted", "autonomous_work_permitted",
    "memory_mutation_permitted", "lesson_commit_permitted", "model_training_permitted",
    "model_weights_changed", "installation_permitted", "promotion_permitted",
    "certification_permitted", "authority", "content_free", "candidate_digest",
}
_RECEIPT_FIELDS = {
    "contract_version", "candidate_type", "purpose_category", "deficiency_class",
    "candidate_available", "provider_completed", "assistant_memory_committed",
    "eligible_for_future_review_continuity", "goal_activation_performed",
    "plan_created", "tool_routed", "action_executed", "source_edited",
    "autonomous_work_started", "memory_mutated", "lesson_committed",
    "model_trained", "model_weights_changed", "installation_performed",
    "promotion_performed", "certification_performed", "authority", "content_free",
    "candidate_digest", "receipt_digest",
}

_AUTHORITY_FIELDS = {
    "approval_granted", "approved", "authorized", "authorization_granted",
    "goal_activation_permitted", "activate_goal", "plan_creation_permitted",
    "create_plan", "tool_routing_permitted", "tool_use_permitted",
    "action_execution_permitted", "execute", "execution_permitted",
    "source_editing_permitted", "modify_files", "autonomous_work_permitted",
    "may_initiate_new_turn", "memory_mutation_permitted", "lesson_commit_permitted",
    "training_permitted", "model_training_permitted", "installation_permitted",
    "promotion_permitted", "certification_permitted",
}
_PRIVATE_FIELDS = {
    "private_chain_of_thought", "chain_of_thought", "hidden_reasoning",
    "provider_payload", "raw_provider_response", "raw_prompt", "prompt",
    "conversation_text", "experience_text", "memory_content", "lesson_content",
    "goal_text", "corrected_value", "preference_value",
}
_PROMPT_INJECTION = re.compile(
    r"<\s*/?\s*(?:system|assistant|developer|tool|internally_generated_goal|goal_candidate)\b",
    re.I,
)
_PROBLEM = re.compile(
    r"\b(?:problem|issue|bug|broken|wrong|fail(?:ed|ure|ing)?|error|regression|unreliable|"
    r"flaky|unstable|crash(?:ed|es|ing)?|timeout|hang(?:s|ing)?|doesn'?t work|not working)\b",
    re.I,
)
_REPEAT = re.compile(r"\b(?:again|still|keeps?|repeated(?:ly)?|every time|continues? to)\b", re.I)
_MISSING = re.compile(
    r"\b(?:can(?:not|'t)|unable to|missing (?:a )?capability|doesn'?t support|needs? to be able to)\b",
    re.I,
)
_CONTRADICTION = re.compile(r"\b(?:contradict(?:ion|ory)?|inconsistent|conflict(?:ing)?|doesn'?t match)\b", re.I)
_CORRECTION = re.compile(r"\b(?:actually|correction|that'?s wrong|not what i said|i said|take that back|disregard)\b", re.I)
_TEST_FAILURE = re.compile(r"\b(?:test|suite|regression|assertion|compile|build)\b.{0,64}\b(?:fail(?:ed|ure)?|error|broken)\b", re.I)
_KNOWLEDGE_GAP = re.compile(r"\b(?:doesn'?t know|don'?t know|knowledge gap|missing information|uncertain about)\b", re.I)
_MAINTENANCE = re.compile(r"\b(?:cleanup|maintenance|stale code|technical debt|duplicate code|consolidat(?:e|ion))\b", re.I)
_PROJECT_SCOPE = re.compile(r"\b(?:project|repository|repo|code|source|test|suite|build|compile|release|eidolon)\b", re.I)
_SYSTEM_SCOPE = re.compile(r"\b(?:system|capability|architecture|runtime|provider|model)\b", re.I)
_TARGET_SUBJECT = re.compile(r"\b(?:eidolon|you|your|assistant|system|runtime|project|repository|repo|code|source|suite|build|capability|memory|conversation)\b", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: object) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return list(value)


def _bounded_json_bytes(value: object, maximum: int = MAX_COMPONENT_BYTES) -> tuple[int, bool]:
    try:
        size = len(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))
    except Exception:
        return maximum + 1, True
    return size, size > maximum


def _valid_digest(value: object, field: str) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get(field) or "")
    unsigned = {key: item for key, item in value.items() if key != field}
    return len(supplied) == 64 and _digest(unsigned) == supplied


def _bounded_count(value: object, maximum: int = MAX_EVIDENCE_COUNT) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum


def _exact_fields(value: object, expected: set[str]) -> bool:
    return isinstance(value, Mapping) and set(value.keys()) == expected


def _parse_time(value: object) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _scan_structural(value: object) -> tuple[int, int, int]:
    authority = private = injection = 0
    stack = [value]
    visited = 0
    while stack and visited < 4096:
        current = stack.pop()
        visited += 1
        if isinstance(current, Mapping):
            for key, item in current.items():
                token = str(key).strip().lower()
                if token in _AUTHORITY_FIELDS and item not in (False, None, "", 0):
                    authority += 1
                if token in _PRIVATE_FIELDS:
                    private += 1
                stack.append(item)
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            stack.extend(list(current)[:256])
        elif isinstance(current, str) and _PROMPT_INJECTION.search(current):
            injection += 1
    return authority, private, injection


def _alpha_status(value: object) -> dict[str, Any]:
    malformed = not isinstance(value, Mapping)
    projection = _mapping(value)
    policy = _mapping(projection.get("policy"))
    evidence = _mapping(projection.get("evidence"))
    diagnostics = _mapping(projection.get("diagnostics"))
    public = (policy, evidence, diagnostics)
    size, oversized = _bounded_json_bytes(public)
    policy_valid = _valid_digest(policy, "policy_digest")
    evidence_valid = _valid_digest(evidence, "evidence_digest")
    diagnostics_valid = verify_memory_experiential_learning_alpha_diagnostics(diagnostics)
    coherent = diagnostics.get("policy_digest") == policy.get("policy_digest")
    authority, private, injection = _scan_structural(public)
    recovered = bool(policy.get("policy_recovered"))
    valid = not any((malformed, oversized, not policy_valid, not evidence_valid, not diagnostics_valid, not coherent, authority, private, injection))
    return {
        "valid": valid,
        "malformed": malformed,
        "oversized": oversized,
        "component_bytes": min(size, MAX_COMPONENT_BYTES + 1),
        "policy_valid": policy_valid,
        "evidence_valid": evidence_valid,
        "diagnostics_valid": diagnostics_valid,
        "coherent": coherent,
        "authority_violation_count": authority,
        "private_field_violation_count": private,
        "prompt_injection_count": injection,
        "policy_recovered": recovered,
        "alpha_posture": str(policy.get("alpha_posture") or ""),
        "learning_candidate_type": str(policy.get("learning_candidate_type") or "none"),
        "lesson_candidate_type": str(policy.get("lesson_candidate_type") or "none"),
    }


def _message_flags(message: str) -> dict[str, bool]:
    text = " ".join(str(message or "").split())[:8000]
    problem = bool(_PROBLEM.search(text))
    repeated = bool(_REPEAT.search(text))
    missing = bool(_MISSING.search(text))
    contradiction = bool(_CONTRADICTION.search(text))
    correction = bool(_CORRECTION.search(text))
    test_failure = bool(_TEST_FAILURE.search(text))
    knowledge = bool(_KNOWLEDGE_GAP.search(text))
    maintenance = bool(_MAINTENANCE.search(text))
    return {
        "problem": problem,
        "repeated": repeated,
        "missing_capability": missing,
        "contradiction": contradiction,
        "correction": correction,
        "test_failure": test_failure,
        "knowledge_gap": knowledge,
        "maintenance": maintenance,
        "prompt_injection": bool(_PROMPT_INJECTION.search(text)),
        "project_scope": bool(_PROJECT_SCOPE.search(text)),
        "system_scope": bool(_SYSTEM_SCOPE.search(text)),
        "target_subject": bool(_TARGET_SUBJECT.search(text)),
    }


def _observation_signals(rows: object) -> dict[str, int]:
    raw = _sequence(rows)
    counts = {
        "row_count": min(len(raw), MAX_OBSERVATION_ROWS),
        "ignored_row_count": max(0, len(raw) - MAX_OBSERVATION_ROWS),
        "operator_problem_count": 0,
        "correction_count": 0,
        "provider_failure_count": 0,
        "test_failure_count": 0,
        "diagnostic_failure_count": 0,
        "prompt_injection_count": 0,
        "malformed_row_count": 0,
        "oversized_row_count": 0,
    }
    seen: set[str] = set()
    for raw_row in raw[-MAX_OBSERVATION_ROWS:]:
        if not isinstance(raw_row, Mapping):
            counts["malformed_row_count"] += 1
            continue
        row = dict(raw_row)
        structural = {
            "completion_state": row.get("completion_state"),
            "success": row.get("success"),
            "failure_category": row.get("failure_category"),
            "diagnostic": row.get("diagnostic") if isinstance(row.get("diagnostic"), Mapping) else {},
            "created_at": row.get("created_at"),
        }
        size, oversized = _bounded_json_bytes(structural, MAX_RECEIPT_BYTES)
        if oversized:
            counts["oversized_row_count"] += 1
            continue
        raw_message = str(row.get("user_message") or "")
        if len(raw_message.encode("utf-8", errors="replace")) > MAX_OBSERVATION_MESSAGE_BYTES:
            counts["oversized_row_count"] += 1
            continue
        message = " ".join(raw_message.split())[:4000]
        flags = _message_flags(message)
        counts["prompt_injection_count"] += int(flags["prompt_injection"])
        signature = _digest({
            "problem": flags["problem"], "repeated": flags["repeated"],
            "missing": flags["missing_capability"], "contradiction": flags["contradiction"],
            "correction": flags["correction"], "test_failure": flags["test_failure"],
            "completion_state": str(row.get("completion_state") or ""),
            "failure_category": str(row.get("failure_category") or "")[:80],
            "created_at": str(row.get("created_at") or "")[:64],
        })
        if signature in seen:
            continue
        seen.add(signature)
        if flags["target_subject"] and (flags["problem"] or flags["missing_capability"] or flags["contradiction"]):
            counts["operator_problem_count"] += 1
        if flags["correction"]:
            counts["correction_count"] += 1
        if flags["target_subject"] and flags["test_failure"]:
            counts["test_failure_count"] += 1
        completion = str(row.get("completion_state") or "").strip().lower()
        failure = str(row.get("failure_category") or "").strip().lower()
        success = row.get("success")
        if completion in {"failed", "response_generated_memory_failed", "cancelled"} or failure or success is False:
            counts["provider_failure_count"] += 1
        diagnostic = row.get("diagnostic") if isinstance(row.get("diagnostic"), Mapping) else {}
        category = str(diagnostic.get("technical_category") or "").strip().lower()
        if category and category not in {"completed", "ok", "none"}:
            counts["diagnostic_failure_count"] += 1
    return counts


def _extract_receipt(row: object) -> Mapping[str, Any] | None:
    if not isinstance(row, Mapping):
        return None
    if "internally_generated_goal_candidate_review_handoff" in row:
        value = row.get("internally_generated_goal_candidate_review_handoff")
        return value if isinstance(value, Mapping) else None
    context = row.get("cognitive_context")
    if isinstance(context, Mapping):
        value = context.get("internally_generated_goal_candidate_review_handoff")
        return value if isinstance(value, Mapping) else None
    return row if "receipt_digest" in row and "candidate_digest" in row else None


def validate_prior_internally_generated_goal_candidate_receipts(
    rows: object, *, now: datetime | None = None
) -> dict[str, Any]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    raw_rows = _sequence(rows)
    ignored = max(0, len(raw_rows) - MAX_PRIOR_RECEIPTS)
    malformed = oversized = tampered = stale = 0
    valid_rows: list[tuple[int, datetime | None, dict[str, Any]]] = []
    for index, row in enumerate(raw_rows[-MAX_PRIOR_RECEIPTS:]):
        if not isinstance(row, Mapping):
            malformed += 1
            continue
        receipt: Mapping[str, Any] | None = None
        if "internally_generated_goal_candidate_review_handoff" in row:
            raw_receipt = row.get("internally_generated_goal_candidate_review_handoff")
            if not isinstance(raw_receipt, Mapping):
                malformed += 1
                continue
            receipt = raw_receipt
        elif isinstance(row.get("cognitive_context"), Mapping) and "internally_generated_goal_candidate_review_handoff" in row.get("cognitive_context", {}):
            raw_receipt = row.get("cognitive_context", {}).get("internally_generated_goal_candidate_review_handoff")
            if not isinstance(raw_receipt, Mapping):
                malformed += 1
                continue
            receipt = raw_receipt
        elif "receipt_digest" in row and "candidate_digest" in row:
            receipt = row
        else:
            # Ordinary transcript rows without a goal receipt are not malformed.
            continue
        size, too_large = _bounded_json_bytes(receipt, MAX_RECEIPT_BYTES)
        if too_large or size > MAX_RECEIPT_BYTES:
            oversized += 1
            continue
        if not isinstance(receipt, Mapping):
            malformed += 1
            continue
        item = dict(receipt)
        if not verify_internally_generated_goal_candidate_review_handoff(item):
            tampered += 1
            continue
        stamp = _parse_time(row.get("created_at") if isinstance(row, Mapping) else None)
        if stamp is not None and (current - stamp).total_seconds() > STALE_RECEIPT_DAYS * 86400:
            stale += 1
            continue
        if item.get("eligible_for_future_review_continuity") is True:
            valid_rows.append((index, stamp, item))

    digests = [str(item.get("receipt_digest") or "") for _, _, item in valid_rows]
    unique_digests = list(dict.fromkeys(digests))
    replayed = max(0, len(digests) - len(unique_digests))

    latest: list[dict[str, Any]] = []
    if valid_rows:
        dated = [entry for entry in valid_rows if entry[1] is not None]
        if dated:
            latest_time = max(entry[1] for entry in dated if entry[1] is not None)
            latest = [entry[2] for entry in dated if entry[1] == latest_time]
        else:
            latest = [entry[2] for entry in valid_rows]
    latest_candidate_digests = {str(item.get("candidate_digest") or "") for item in latest}
    conflicting = len(latest_candidate_digests) > 1
    selected = latest[-1] if latest and not conflicting else None
    recovery_required = bool(malformed or oversized or tampered or ignored or conflicting)
    return {
        "verified_receipt_count": 1 if selected is not None else 0,
        "replayed_receipt_count": replayed,
        "stale_receipt_count": stale,
        "malformed_receipt_count": malformed,
        "oversized_receipt_count": oversized,
        "tampered_receipt_count": tampered,
        "ignored_receipt_count": ignored,
        "conflicting_receipts": conflicting,
        "receipt_budget_exceeded": bool(ignored),
        "recovery_required": recovery_required,
        "candidate_type": str(selected.get("candidate_type") or "none") if selected else "none",
        "candidate_digest": str(selected.get("candidate_digest") or "") if selected else "",
    }


def _scope(flags: Mapping[str, bool], candidate_type: str) -> str:
    if flags.get("system_scope") or candidate_type in {"capability_improvement", "coherence_repair"}:
        return "system"
    if flags.get("project_scope"):
        return "project"
    if candidate_type == "reliability_improvement":
        return "system"
    if candidate_type == "interaction_quality_improvement":
        return "conversation"
    return "project"


def _candidate_choice(
    flags: Mapping[str, bool], observations: Mapping[str, int], alpha: Mapping[str, Any]
) -> tuple[str, str, str, list[str], list[str]]:
    sources: list[str] = []
    legacy_sources: list[str] = []
    current_target = bool(flags.get("target_subject"))
    current_problem = bool(current_target and (
        flags.get("problem") or flags.get("missing_capability") or flags.get("contradiction")
        or flags.get("test_failure") or flags.get("knowledge_gap") or flags.get("maintenance")
    ))
    if current_problem:
        sources.append("current_request")
        legacy_sources.append("concern")
    if alpha.get("policy_recovered"):
        sources.append("verified_memory_learning_recovery")
        legacy_sources.append("world_model_outcome")
    if observations.get("operator_problem_count", 0):
        sources.append("prior_operator_problem")
        legacy_sources.append("concern")
    if observations.get("correction_count", 0):
        sources.append("prior_correction")
        legacy_sources.append("memory")
    if observations.get("provider_failure_count", 0):
        sources.append("provider_failure")
        legacy_sources.append("unfinished_thought")
    if observations.get("test_failure_count", 0):
        sources.append("test_failure")
        legacy_sources.append("inquiry_outcome")
    if observations.get("diagnostic_failure_count", 0):
        sources.append("runtime_diagnostic")
        legacy_sources.append("world_model_outcome")

    repeated_problem = bool(
        flags.get("repeated")
        or observations.get("operator_problem_count", 0) >= 2
        or observations.get("provider_failure_count", 0) >= 2
        or observations.get("correction_count", 0) >= 2
    )

    if (current_target and flags.get("test_failure")) or observations.get("test_failure_count", 0) or observations.get("diagnostic_failure_count", 0):
        return "reliability_improvement", "test_or_diagnostic_failure", "reliability", sources, legacy_sources
    if (current_target and flags.get("contradiction")) or alpha.get("policy_recovered"):
        return "coherence_repair", "unresolved_contradiction", "reliability", sources, legacy_sources
    if current_target and flags.get("missing_capability"):
        return "capability_improvement", "missing_capability", "capability_improvement", sources, legacy_sources
    if current_target and flags.get("knowledge_gap"):
        return "knowledge_improvement", "operator_confirmed_problem", "knowledge", sources, legacy_sources
    if current_target and flags.get("maintenance"):
        return "maintenance_improvement", "maintenance_need", "maintenance", sources, legacy_sources
    if observations.get("correction_count", 0) >= 2 or (flags.get("correction") and repeated_problem):
        return "interaction_quality_improvement", "repeated_correction", "relationship_continuity", sources, legacy_sources
    if current_target and flags.get("problem") and repeated_problem:
        return "reliability_improvement", "repeated_failure", "reliability", sources, legacy_sources
    if current_target and flags.get("problem"):
        return "reliability_improvement", "operator_confirmed_problem", "reliability", sources, legacy_sources
    if observations.get("provider_failure_count", 0) >= 2:
        return "reliability_improvement", "repeated_failure", "reliability", sources, legacy_sources
    if observations.get("operator_problem_count", 0) >= 2:
        return "reliability_improvement", "repeated_failure", "reliability", sources, legacy_sources
    return "none", "none", "maintenance", sources, legacy_sources


def build_internally_generated_goal_candidate(
    current_message: str,
    memory_learning_alpha_projection: object,
    *,
    observation_rows: object = None,
    protected_operator_constraints: Sequence[str] = (),
    prior_goal_candidate_receipts: object = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build one bounded review-only goal-candidate projection for an ordinary turn."""
    message = str(current_message or "")
    message_oversized = len(message.encode("utf-8", errors="replace")) > MAX_CURRENT_MESSAGE_BYTES
    flags = _message_flags(message)
    alpha = _alpha_status(memory_learning_alpha_projection)
    observations = _observation_signals(observation_rows)
    prior = validate_prior_internally_generated_goal_candidate_receipts(
        prior_goal_candidate_receipts, now=now
    )
    constraints = tuple(dict.fromkeys(str(item).strip()[:120] for item in protected_operator_constraints if str(item).strip()))[:24]
    constraints_valid = {
        "literal_current_request_precedence", "no_goal_activation", "no_plan_creation",
        "no_tool_routing", "no_action_execution", "operator_review_required",
    }.issubset(set(constraints))

    candidate_type, deficiency_class, purpose_category, source_categories, legacy_sources = _candidate_choice(flags, observations, alpha)
    source_categories = list(dict.fromkeys(item for item in source_categories if item in EVIDENCE_SOURCE_CATEGORIES))[:MAX_SOURCE_CATEGORIES]
    legacy_sources = list(dict.fromkeys(item for item in legacy_sources if item in SOURCE_CATEGORIES))[:MAX_SOURCE_CATEGORIES]
    if prior["verified_receipt_count"] and prior["candidate_type"] == candidate_type and candidate_type != "none":
        source_categories.append("verified_goal_receipt")
        legacy_sources.append("goal_predecessor")
        source_categories = list(dict.fromkeys(source_categories))[:MAX_SOURCE_CATEGORIES]
        legacy_sources = list(dict.fromkeys(legacy_sources))[:MAX_SOURCE_CATEGORIES]

    evidence_count = min(MAX_EVIDENCE_COUNT, sum((
        int(flags["target_subject"] and (flags["problem"] or flags["missing_capability"] or flags["contradiction"] or flags["test_failure"] or flags["knowledge_gap"] or flags["maintenance"])),
        int(alpha["policy_recovered"]),
        observations["operator_problem_count"], observations["correction_count"],
        observations["provider_failure_count"], observations["test_failure_count"],
        observations["diagnostic_failure_count"], prior["verified_receipt_count"],
    )))
    current_request_relevant = "current_request" in source_categories
    nomination_supported = candidate_type != "none" and (
        current_request_relevant
        or alpha["policy_recovered"]
        or observations["test_failure_count"] >= 1
        or observations["diagnostic_failure_count"] >= 1
        or observations["provider_failure_count"] >= 2
        or observations["operator_problem_count"] >= 2
        or observations["correction_count"] >= 2
    )

    authority, private, structural_injection = _scan_structural((
        _mapping(memory_learning_alpha_projection).get("policy"),
        _mapping(memory_learning_alpha_projection).get("evidence"),
        _mapping(memory_learning_alpha_projection).get("diagnostics"),
    ))
    invalid_observations = observations["malformed_row_count"] + observations["oversized_row_count"]
    recovery = bool(
        not message.strip() or message_oversized or flags["prompt_injection"] or not alpha["valid"]
        or prior["recovery_required"] or not constraints_valid or authority or private
        or structural_injection or observations["prompt_injection_count"] or invalid_observations
    )
    if recovery:
        candidate_type = "none"
        deficiency_class = "none"
        purpose_category = "maintenance"
        source_categories = []
        legacy_sources = []
        evidence_count = 0
        nomination_supported = False
        current_request_relevant = False

    if candidate_type == "none" or not nomination_supported:
        candidate_type = "none"
        deficiency_class = "none"
        candidate = None
        confidence = "none"
        impact = "none"
        cost = "unknown"
        risk = "unknown"
        scope = "none"
        posture = "literal_current_request_only_recovery" if recovery else "no_goal_candidate"
        influence = "none"
    else:
        confidence = "high" if evidence_count >= 3 or flags["test_failure"] else "medium"
        impact = "high" if evidence_count >= 3 or candidate_type == "capability_improvement" else "medium"
        cost = "unknown"
        risk = "medium" if _scope(flags, candidate_type) == "system" else "low"
        scope = _scope(flags, candidate_type)
        posture = "operator_review_candidate"
        influence = "bounded_optional_explanation" if current_request_relevant else "background_review_only"
        candidate = {
            "contract_version": CONTRACT_VERSION,
            "candidate_type": candidate_type,
            "purpose_category": purpose_category,
            "deficiency_class": deficiency_class,
            "legacy_signal_source_categories": sorted(set(legacy_sources)),
            "evidence_source_categories": sorted(set(source_categories)),
            "evidence_count": evidence_count,
            "confidence_band": confidence,
            "impact_band": impact,
            "cost_band": cost,
            "risk_band": risk,
            "scope_band": scope,
            "current_request_relevant": current_request_relevant,
            "review_required": True,
            "operator_approval_required": True,
            "goal_activation_permitted": False,
            "plan_creation_permitted": False,
            "tool_routing_permitted": False,
            "action_execution_permitted": False,
            "source_editing_permitted": False,
            "autonomous_work_permitted": False,
            "memory_mutation_permitted": False,
            "lesson_commit_permitted": False,
            "model_training_permitted": False,
            "model_weights_changed": False,
            "installation_permitted": False,
            "promotion_permitted": False,
            "certification_permitted": False,
            "authority": "none",
            "content_free": True,
        }
        candidate["candidate_digest"] = _digest(candidate)

    continuity = (
        "literal_current_request_only" if recovery
        else "review_current_evidence" if candidate is not None
        else "no_goal_candidate_continuity"
    )
    if candidate is not None and prior["verified_receipt_count"] and prior["candidate_type"] == candidate_type:
        continuity = "resume_verified_review_context"

    evidence = {
        "contract_version": CONTRACT_VERSION,
        "alpha_projection_valid": alpha["valid"],
        "alpha_projection_recovered": alpha["policy_recovered"],
        "observation_row_count": observations["row_count"],
        "ignored_observation_row_count": observations["ignored_row_count"],
        "malformed_observation_row_count": observations["malformed_row_count"],
        "oversized_observation_row_count": observations["oversized_row_count"],
        "operator_problem_count": observations["operator_problem_count"],
        "correction_count": observations["correction_count"],
        "provider_failure_count": observations["provider_failure_count"],
        "test_failure_count": observations["test_failure_count"],
        "diagnostic_failure_count": observations["diagnostic_failure_count"],
        "candidate_evidence_count": evidence_count,
        "verified_prior_receipt_count": prior["verified_receipt_count"],
        "replayed_prior_receipt_count": prior["replayed_receipt_count"],
        "stale_prior_receipt_count": prior["stale_receipt_count"],
        "malformed_prior_receipt_count": prior["malformed_receipt_count"],
        "oversized_prior_receipt_count": prior["oversized_receipt_count"],
        "tampered_prior_receipt_count": prior["tampered_receipt_count"],
        "ignored_prior_receipt_count": prior["ignored_receipt_count"],
        "conflicting_prior_receipts": prior["conflicting_receipts"],
        "authority_violation_count": authority,
        "private_field_violation_count": private,
        "prompt_injection_count": int(flags["prompt_injection"]) + observations["prompt_injection_count"] + structural_injection,
        "current_message_oversized": message_oversized,
        "constraints_complete": constraints_valid,
        "historical_goal_architecture_reused": True,
        "historical_truth_preserved": True,
        "contains_goal_text": False,
        "contains_memory_content": False,
        "contains_lesson_content": False,
        "contains_conversation_text": False,
        "contains_provider_payload": False,
        "contains_private_reasoning": False,
        "goal_activated": False,
        "plan_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "memory_mutated": False,
        "lesson_committed": False,
        "model_trained": False,
        "model_weights_changed": False,
        "provider_contacted": False,
        "authority": "none",
        "content_free": True,
        "integrity": "degraded" if recovery else "valid",
    }
    evidence["evidence_digest"] = _digest(evidence)

    policy = {
        "contract_version": CONTRACT_VERSION,
        "goal_candidate_posture": posture,
        "continuity_disposition": continuity,
        "candidate_type": candidate_type,
        "purpose_category": purpose_category if candidate is not None else "maintenance",
        "deficiency_class": deficiency_class,
        "evidence_source_categories": sorted(set(source_categories)) if candidate is not None else [],
        "legacy_signal_source_categories": sorted(set(legacy_sources)) if candidate is not None else [],
        "evidence_count": evidence_count,
        "confidence_band": confidence,
        "impact_band": impact,
        "cost_band": cost,
        "risk_band": risk,
        "scope_band": scope,
        "response_influence": influence,
        "current_request_relevant": current_request_relevant,
        "literal_current_request_precedence": True,
        "goal_candidate_review_only": True,
        "operator_review_required": bool(candidate),
        "operator_approval_required": bool(candidate),
        "historical_goal_architecture_reused": True,
        "goal_candidate_separate_from_goal_activation": True,
        "goal_candidate_separate_from_planning": True,
        "goal_candidate_separate_from_action": True,
        "goal_activation_permitted": False,
        "plan_creation_permitted": False,
        "tool_routing_permitted": False,
        "action_execution_permitted": False,
        "source_editing_permitted": False,
        "autonomous_work_permitted": False,
        "autonomous_new_turn_permitted": False,
        "unsolicited_speech_permitted": False,
        "memory_mutation_permitted": False,
        "lesson_commit_permitted": False,
        "model_training_permitted": False,
        "model_weights_changed": False,
        "installation_permitted": False,
        "promotion_permitted": False,
        "certification_permitted": False,
        "approval_granted": False,
        "policy_recovered": recovery,
        "authority": "none",
        "content_free": True,
        "evidence_digest": evidence["evidence_digest"],
    }
    policy["policy_digest"] = _digest(policy)

    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "goal_candidate_posture": posture,
        "continuity_disposition": continuity,
        "candidate_type": candidate_type,
        "purpose_category": policy["purpose_category"],
        "deficiency_class": deficiency_class,
        "evidence_count": evidence_count,
        "confidence_band": confidence,
        "impact_band": impact,
        "risk_band": risk,
        "scope_band": scope,
        "current_request_relevant": current_request_relevant,
        "candidate_available": candidate is not None,
        "verified_prior_receipt_count": prior["verified_receipt_count"],
        "replayed_prior_receipt_count": prior["replayed_receipt_count"],
        "stale_prior_receipt_count": prior["stale_receipt_count"],
        "tampered_prior_receipt_count": prior["tampered_receipt_count"],
        "conflicting_prior_receipts": prior["conflicting_receipts"],
        "policy_recovered": recovery,
        "goal_activated": False,
        "plan_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "memory_mutated": False,
        "lesson_committed": False,
        "model_trained": False,
        "model_weights_changed": False,
        "provider_contacted": False,
        "authority": "none",
        "content_free": True,
        "policy_digest": policy["policy_digest"],
    }
    diagnostics["diagnostics_digest"] = _digest(diagnostics)

    prompt_payload = {
        key: policy[key]
        for key in (
            "contract_version", "goal_candidate_posture", "candidate_type", "purpose_category",
            "deficiency_class", "evidence_source_categories", "evidence_count", "confidence_band",
            "impact_band", "cost_band", "risk_band", "scope_band", "response_influence",
            "current_request_relevant", "literal_current_request_precedence",
            "goal_candidate_review_only", "operator_review_required",
            "goal_activation_permitted", "plan_creation_permitted", "tool_routing_permitted",
            "action_execution_permitted", "autonomous_new_turn_permitted",
            "unsolicited_speech_permitted", "authority", "content_free",
        )
    }
    prompt = '<internally_generated_goal_candidate data_only="true" authority="none">' + json.dumps(
        prompt_payload, sort_keys=True, separators=(",", ":")
    ) + '</internally_generated_goal_candidate>'
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError("internally generated goal candidate prompt exceeded bound")

    return {
        "policy": policy,
        "evidence": evidence,
        "diagnostics": diagnostics,
        "candidate": candidate,
        "prompt_section": prompt,
    }


def verify_internally_generated_goal_candidate(value: object) -> bool:
    if not _exact_fields(value, _CANDIDATE_FIELDS):
        return False
    supplied = str(value.get("candidate_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "candidate_digest"}
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == CONTRACT_VERSION
        and value.get("candidate_type") in CANDIDATE_TYPES[1:]
        and value.get("purpose_category") in PURPOSE_CATEGORIES
        and value.get("deficiency_class") in DEFICIENCY_CLASSES[1:]
        and isinstance(value.get("legacy_signal_source_categories"), list)
        and set(value.get("legacy_signal_source_categories") or ()) <= SOURCE_CATEGORIES
        and isinstance(value.get("evidence_source_categories"), list)
        and set(value.get("evidence_source_categories") or ()) <= set(EVIDENCE_SOURCE_CATEGORIES)
        and _bounded_count(value.get("evidence_count")) and value.get("evidence_count") > 0
        and value.get("confidence_band") in CONFIDENCE_BANDS[1:]
        and value.get("impact_band") in IMPACT_BANDS[1:]
        and value.get("cost_band") in COST_BANDS
        and value.get("risk_band") in RISK_BANDS
        and value.get("scope_band") in SCOPE_BANDS[1:]
        and isinstance(value.get("current_request_relevant"), bool)
        and value.get("review_required") is True
        and value.get("operator_approval_required") is True
        and all(value.get(field) is False for field in (
            "goal_activation_permitted", "plan_creation_permitted", "tool_routing_permitted",
            "action_execution_permitted", "source_editing_permitted", "autonomous_work_permitted",
            "memory_mutation_permitted", "lesson_commit_permitted", "model_training_permitted",
            "model_weights_changed", "installation_permitted", "promotion_permitted",
            "certification_permitted",
        ))
        and value.get("authority") == "none" and value.get("content_free") is True
    )


def verify_internally_generated_goal_candidate_diagnostics(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("diagnostics_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "diagnostics_digest"}
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == CONTRACT_VERSION
        and value.get("candidate_type") in CANDIDATE_TYPES
        and value.get("deficiency_class") in DEFICIENCY_CLASSES
        and value.get("confidence_band") in CONFIDENCE_BANDS
        and value.get("impact_band") in IMPACT_BANDS
        and value.get("risk_band") in RISK_BANDS
        and value.get("scope_band") in SCOPE_BANDS
        and _bounded_count(value.get("evidence_count"))
        and value.get("authority") == "none" and value.get("content_free") is True
        and all(value.get(field) is False for field in (
            "goal_activated", "plan_created", "tool_routed", "action_executed",
            "source_edited", "autonomous_work_started", "memory_mutated",
            "lesson_committed", "model_trained", "model_weights_changed", "provider_contacted",
        ))
    )


def build_internally_generated_goal_candidate_review_handoff(
    projection: object, *, provider_completed: bool, assistant_memory_committed: bool
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    diagnostics = _mapping(value.get("diagnostics"))
    candidate = value.get("candidate")
    valid_candidate = verify_internally_generated_goal_candidate(candidate)
    authority, private, injection = _scan_structural((policy, value.get("evidence"), diagnostics, candidate))
    valid_projection = (
        _valid_digest(policy, "policy_digest")
        and verify_internally_generated_goal_candidate_diagnostics(diagnostics)
        and diagnostics.get("policy_digest") == policy.get("policy_digest")
        and not policy.get("policy_recovered")
        and not authority and not private and not injection
        and (candidate is None or valid_candidate)
    )
    eligible = bool(
        provider_completed and assistant_memory_committed and valid_projection and valid_candidate
    )
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "candidate_type": str(candidate.get("candidate_type") or "none") if eligible else "none",
        "purpose_category": str(candidate.get("purpose_category") or "maintenance") if eligible else "maintenance",
        "deficiency_class": str(candidate.get("deficiency_class") or "none") if eligible else "none",
        "candidate_available": bool(valid_candidate and valid_projection),
        "provider_completed": bool(provider_completed),
        "assistant_memory_committed": bool(assistant_memory_committed),
        "eligible_for_future_review_continuity": eligible,
        "goal_activation_performed": False,
        "plan_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "memory_mutated": False,
        "lesson_committed": False,
        "model_trained": False,
        "model_weights_changed": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "authority": "none",
        "content_free": True,
        "candidate_digest": str(candidate.get("candidate_digest") or "") if valid_candidate else "",
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt


def verify_internally_generated_goal_candidate_review_handoff(value: object) -> bool:
    if not _exact_fields(value, _RECEIPT_FIELDS):
        return False
    size, oversized = _bounded_json_bytes(value, MAX_RECEIPT_BYTES)
    if oversized or size > MAX_RECEIPT_BYTES:
        return False
    supplied = str(value.get("receipt_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "receipt_digest"}
    eligible = value.get("eligible_for_future_review_continuity")
    available = value.get("candidate_available")
    coherent = (
        eligible is False
        or (
            eligible is True and available is True
            and value.get("provider_completed") is True
            and value.get("assistant_memory_committed") is True
            and value.get("candidate_type") in CANDIDATE_TYPES[1:]
            and value.get("deficiency_class") in DEFICIENCY_CLASSES[1:]
            and value.get("purpose_category") in PURPOSE_CATEGORIES
            and len(str(value.get("candidate_digest") or "")) == 64
        )
    )
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == CONTRACT_VERSION
        and value.get("candidate_type") in CANDIDATE_TYPES
        and value.get("deficiency_class") in DEFICIENCY_CLASSES
        and value.get("purpose_category") in PURPOSE_CATEGORIES
        and isinstance(available, bool) and isinstance(eligible, bool) and coherent
        and isinstance(value.get("provider_completed"), bool)
        and isinstance(value.get("assistant_memory_committed"), bool)
        and all(value.get(field) is False for field in (
            "goal_activation_performed", "plan_created", "tool_routed", "action_executed",
            "source_edited", "autonomous_work_started", "memory_mutated", "lesson_committed",
            "model_trained", "model_weights_changed", "installation_performed",
            "promotion_performed", "certification_performed",
        ))
        and value.get("authority") == "none" and value.get("content_free") is True
        and len(str(value.get("candidate_digest") or "")) in {0, 64}
    )

# v1170.3-v1170.5 review integration. This remains a pure structural layer:
# it reconciles review evidence, never persists or activates a goal, and never
# creates a plan, route, tool call, source edit, or action.
REVIEW_CONTRACT_VERSION = "1170.5"
_REVIEW_STATE_FIELDS = {
    "contract_version", "review_posture", "continuity_disposition", "candidate_type",
    "purpose_category", "deficiency_class", "stability_band", "recurrence_band",
    "evidence_count", "verified_prior_receipt_count", "replayed_prior_receipt_count",
    "conflicting_prior_receipts", "current_request_relevant", "candidate_available",
    "operator_review_required", "operator_approval_required", "goal_activation_permitted",
    "plan_creation_permitted", "tool_routing_permitted", "action_execution_permitted",
    "source_editing_permitted", "autonomous_work_permitted", "memory_mutation_permitted",
    "lesson_commit_permitted", "model_training_permitted", "installation_permitted",
    "promotion_permitted", "certification_permitted", "authority", "content_free",
    "candidate_digest", "review_state_digest",
}
_REVIEW_PACKET_FIELDS = {
    "contract_version", "review_disposition", "candidate_type", "purpose_category",
    "deficiency_class", "stability_band", "recurrence_band", "confidence_band",
    "impact_band", "cost_band", "risk_band", "scope_band", "evidence_count",
    "current_request_relevant", "candidate_available", "operator_review_required",
    "operator_approval_required", "historical_truth_preserved", "goal_activated",
    "plan_created", "tool_routed", "action_executed", "source_edited",
    "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
    "model_weights_changed", "installation_performed", "promotion_performed",
    "certification_performed", "authority", "content_free", "candidate_digest",
    "review_state_digest", "review_packet_digest",
}


def build_internally_generated_goal_candidate_review_state(
    projection: object, *, prior_goal_candidate_receipts: object = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Reconcile one current candidate with verified prior review continuity."""
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    diagnostics = _mapping(value.get("diagnostics"))
    candidate = value.get("candidate")
    prior = validate_prior_internally_generated_goal_candidate_receipts(
        prior_goal_candidate_receipts, now=now,
    )
    candidate_valid = verify_internally_generated_goal_candidate(candidate)
    policy_valid = _valid_digest(policy, "policy_digest")
    evidence_valid = _valid_digest(evidence, "evidence_digest")
    diagnostics_valid = verify_internally_generated_goal_candidate_diagnostics(diagnostics)
    coherent = diagnostics.get("policy_digest") == policy.get("policy_digest")
    authority, private, injection = _scan_structural((policy, evidence, diagnostics, candidate))
    projection_valid = bool(
        policy_valid and evidence_valid and diagnostics_valid and coherent
        and not policy.get("policy_recovered") and not authority and not private and not injection
        and (candidate is None or candidate_valid)
    )
    current_type = str(candidate.get("candidate_type") or "none") if candidate_valid else "none"
    current_digest = str(candidate.get("candidate_digest") or "") if candidate_valid else ""
    prior_type = str(prior.get("candidate_type") or "none")
    same_type = bool(candidate_valid and prior.get("verified_receipt_count") and prior_type == current_type)
    conflict = bool(
        prior.get("conflicting_receipts")
        or (candidate_valid and prior.get("verified_receipt_count") and prior_type not in {"none", current_type})
    )
    recovery = bool(not projection_valid or prior.get("recovery_required") or conflict)
    if recovery:
        posture = "literal_current_request_only_recovery"
        continuity = "discard_review_continuity"
        stability = "none"
        recurrence = "none"
        available = False
    elif not candidate_valid:
        posture = "no_review_candidate"
        continuity = "no_review_continuity"
        stability = "none"
        recurrence = "none"
        available = False
    else:
        posture = "operator_review_candidate"
        continuity = "resume_verified_same_type_review" if same_type else "review_current_candidate"
        stability = "stable" if same_type else "emerging"
        evidence_count = int(candidate.get("evidence_count") or 0)
        recurrence = "repeated" if same_type or evidence_count >= 3 else "single"
        available = True
    state = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_posture": posture,
        "continuity_disposition": continuity,
        "candidate_type": current_type if available else "none",
        "purpose_category": str(candidate.get("purpose_category") or "maintenance") if available else "maintenance",
        "deficiency_class": str(candidate.get("deficiency_class") or "none") if available else "none",
        "stability_band": stability,
        "recurrence_band": recurrence,
        "evidence_count": int(candidate.get("evidence_count") or 0) if available else 0,
        "verified_prior_receipt_count": int(prior.get("verified_receipt_count") or 0),
        "replayed_prior_receipt_count": int(prior.get("replayed_receipt_count") or 0),
        "conflicting_prior_receipts": conflict,
        "current_request_relevant": bool(candidate.get("current_request_relevant")) if available else False,
        "candidate_available": available,
        "operator_review_required": available,
        "operator_approval_required": available,
        "goal_activation_permitted": False,
        "plan_creation_permitted": False,
        "tool_routing_permitted": False,
        "action_execution_permitted": False,
        "source_editing_permitted": False,
        "autonomous_work_permitted": False,
        "memory_mutation_permitted": False,
        "lesson_commit_permitted": False,
        "model_training_permitted": False,
        "installation_permitted": False,
        "promotion_permitted": False,
        "certification_permitted": False,
        "authority": "none",
        "content_free": True,
        "candidate_digest": current_digest if available else "",
    }
    state["review_state_digest"] = _digest(state)
    return state


def verify_internally_generated_goal_candidate_review_state(value: object) -> bool:
    if not _exact_fields(value, _REVIEW_STATE_FIELDS):
        return False
    supplied = str(value.get("review_state_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "review_state_digest"}
    available = value.get("candidate_available")
    coherent = (
        (available is True and value.get("candidate_type") in CANDIDATE_TYPES[1:]
         and value.get("deficiency_class") in DEFICIENCY_CLASSES[1:]
         and len(str(value.get("candidate_digest") or "")) == 64
         and value.get("operator_review_required") is True
         and value.get("operator_approval_required") is True)
        or
        (available is False and value.get("candidate_type") == "none"
         and value.get("deficiency_class") == "none"
         and value.get("evidence_count") == 0
         and value.get("candidate_digest") == ""
         and value.get("operator_review_required") is False
         and value.get("operator_approval_required") is False)
    )
    return bool(
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == REVIEW_CONTRACT_VERSION
        and value.get("review_posture") in {
            "literal_current_request_only_recovery", "no_review_candidate", "operator_review_candidate",
        }
        and value.get("continuity_disposition") in {
            "discard_review_continuity", "no_review_continuity",
            "review_current_candidate", "resume_verified_same_type_review",
        }
        and value.get("purpose_category") in PURPOSE_CATEGORIES
        and value.get("stability_band") in {"none", "emerging", "stable"}
        and value.get("recurrence_band") in {"none", "single", "repeated"}
        and _bounded_count(value.get("evidence_count"))
        and _bounded_count(value.get("verified_prior_receipt_count"), 1)
        and _bounded_count(value.get("replayed_prior_receipt_count"), MAX_PRIOR_RECEIPTS)
        and isinstance(value.get("conflicting_prior_receipts"), bool)
        and isinstance(value.get("current_request_relevant"), bool)
        and isinstance(available, bool) and coherent
        and all(value.get(field) is False for field in (
            "goal_activation_permitted", "plan_creation_permitted", "tool_routing_permitted",
            "action_execution_permitted", "source_editing_permitted", "autonomous_work_permitted",
            "memory_mutation_permitted", "lesson_commit_permitted", "model_training_permitted",
            "installation_permitted", "promotion_permitted", "certification_permitted",
        ))
        and value.get("authority") == "none" and value.get("content_free") is True
    )


def build_internally_generated_goal_candidate_review_packet(
    projection: object, review_state: object,
) -> dict[str, Any]:
    """Create a bounded structural packet for operator review, never approval."""
    value = _mapping(projection)
    candidate = value.get("candidate")
    state = _mapping(review_state)
    valid_state = verify_internally_generated_goal_candidate_review_state(state)
    valid_candidate = verify_internally_generated_goal_candidate(candidate)
    available = bool(valid_state and state.get("candidate_available") and valid_candidate
                     and state.get("candidate_digest") == candidate.get("candidate_digest"))
    packet = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_disposition": "review_available" if available else "no_review_available",
        "candidate_type": str(candidate.get("candidate_type") or "none") if available else "none",
        "purpose_category": str(candidate.get("purpose_category") or "maintenance") if available else "maintenance",
        "deficiency_class": str(candidate.get("deficiency_class") or "none") if available else "none",
        "stability_band": str(state.get("stability_band") or "none") if available else "none",
        "recurrence_band": str(state.get("recurrence_band") or "none") if available else "none",
        "confidence_band": str(candidate.get("confidence_band") or "none") if available else "none",
        "impact_band": str(candidate.get("impact_band") or "none") if available else "none",
        "cost_band": str(candidate.get("cost_band") or "unknown") if available else "unknown",
        "risk_band": str(candidate.get("risk_band") or "unknown") if available else "unknown",
        "scope_band": str(candidate.get("scope_band") or "none") if available else "none",
        "evidence_count": int(candidate.get("evidence_count") or 0) if available else 0,
        "current_request_relevant": bool(candidate.get("current_request_relevant")) if available else False,
        "candidate_available": available,
        "operator_review_required": available,
        "operator_approval_required": available,
        "historical_truth_preserved": True,
        "goal_activated": False,
        "plan_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "memory_mutated": False,
        "lesson_committed": False,
        "model_trained": False,
        "model_weights_changed": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "authority": "none",
        "content_free": True,
        "candidate_digest": str(candidate.get("candidate_digest") or "") if available else "",
        "review_state_digest": str(state.get("review_state_digest") or "") if valid_state else "",
    }
    packet["review_packet_digest"] = _digest(packet)
    return packet


def verify_internally_generated_goal_candidate_review_packet(value: object) -> bool:
    if not _exact_fields(value, _REVIEW_PACKET_FIELDS):
        return False
    supplied = str(value.get("review_packet_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "review_packet_digest"}
    available = value.get("candidate_available")
    return bool(
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == REVIEW_CONTRACT_VERSION
        and value.get("review_disposition") in {"review_available", "no_review_available"}
        and value.get("candidate_type") in CANDIDATE_TYPES
        and value.get("purpose_category") in PURPOSE_CATEGORIES
        and value.get("deficiency_class") in DEFICIENCY_CLASSES
        and value.get("stability_band") in {"none", "emerging", "stable"}
        and value.get("recurrence_band") in {"none", "single", "repeated"}
        and value.get("confidence_band") in CONFIDENCE_BANDS
        and value.get("impact_band") in IMPACT_BANDS
        and value.get("cost_band") in COST_BANDS
        and value.get("risk_band") in RISK_BANDS
        and value.get("scope_band") in SCOPE_BANDS
        and _bounded_count(value.get("evidence_count"))
        and isinstance(available, bool)
        and value.get("historical_truth_preserved") is True
        and all(value.get(field) is False for field in (
            "goal_activated", "plan_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
            "model_weights_changed", "installation_performed", "promotion_performed",
            "certification_performed",
        ))
        and value.get("authority") == "none" and value.get("content_free") is True
        and ((available and value.get("review_disposition") == "review_available"
              and value.get("operator_review_required") is True
              and value.get("operator_approval_required") is True
              and len(str(value.get("candidate_digest") or "")) == 64
              and len(str(value.get("review_state_digest") or "")) == 64)
             or (not available and value.get("review_disposition") == "no_review_available"
                 and value.get("operator_review_required") is False
                 and value.get("operator_approval_required") is False
                 and value.get("candidate_digest") == ""))
    )


def build_internally_generated_goal_candidate_review_projection(
    projection: object, *, prior_goal_candidate_receipts: object = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    state = build_internally_generated_goal_candidate_review_state(
        projection, prior_goal_candidate_receipts=prior_goal_candidate_receipts, now=now,
    )
    packet = build_internally_generated_goal_candidate_review_packet(projection, state)
    prompt_payload = {
        key: packet[key] for key in (
            "contract_version", "review_disposition", "candidate_type", "purpose_category",
            "deficiency_class", "stability_band", "recurrence_band", "confidence_band",
            "impact_band", "cost_band", "risk_band", "scope_band", "evidence_count",
            "current_request_relevant", "candidate_available", "operator_review_required",
            "operator_approval_required", "goal_activated", "plan_created", "tool_routed",
            "action_executed", "authority", "content_free",
        )
    }
    prompt = '<internally_generated_goal_review data_only="true" authority="none">' + json.dumps(
        prompt_payload, sort_keys=True, separators=(",", ":")
    ) + '</internally_generated_goal_review>'
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError("internally generated goal review prompt exceeded bound")
    return {"state": state, "review_packet": packet, "prompt_section": prompt}

# v1170.6-v1170.8 reliability, recovery, and adversarial hardening.
RELIABILITY_CONTRACT_VERSION = "1170.8"
MAX_RELIABILITY_FAULTS = 64
_DIAGNOSTICS_FIELDS = {
    "contract_version", "goal_candidate_posture", "continuity_disposition", "candidate_type",
    "purpose_category", "deficiency_class", "evidence_count", "confidence_band", "impact_band",
    "risk_band", "scope_band", "current_request_relevant", "candidate_available",
    "verified_prior_receipt_count", "replayed_prior_receipt_count", "stale_prior_receipt_count",
    "tampered_prior_receipt_count", "conflicting_prior_receipts", "policy_recovered",
    "goal_activated", "plan_created", "tool_routed", "action_executed", "source_edited",
    "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
    "model_weights_changed", "provider_contacted", "authority", "content_free",
    "policy_digest", "diagnostics_digest",
}
_RELIABILITY_FIELDS = {
    "contract_version", "reliability_posture", "ordinary_conversation_ready",
    "projection_valid", "review_state_valid", "review_packet_valid", "prior_continuity_valid",
    "recovered_projection", "residual_candidate_detected", "receipt_budget_exceeded",
    "fault_count", "verified_prior_receipt_count", "replayed_prior_receipt_count",
    "stale_prior_receipt_count", "malformed_prior_receipt_count", "oversized_prior_receipt_count",
    "tampered_prior_receipt_count", "ignored_prior_receipt_count", "candidate_available",
    "review_available", "literal_current_request_precedence", "historical_truth_preserved",
    "goal_activated", "plan_created", "tool_routed", "action_executed", "source_edited",
    "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
    "model_weights_changed", "installation_performed", "promotion_performed",
    "certification_performed", "authority", "content_free", "candidate_digest",
    "review_state_digest", "review_packet_digest", "reliability_digest",
}


def verify_internally_generated_goal_candidate_diagnostics_strict(value: object) -> bool:
    """Reject digest-valid diagnostics that smuggle unknown fields or impossible counts."""
    if not _exact_fields(value, _DIAGNOSTICS_FIELDS):
        return False
    if not verify_internally_generated_goal_candidate_diagnostics(value):
        return False
    return all(_bounded_count(value.get(field), MAX_PRIOR_RECEIPTS) for field in (
        "verified_prior_receipt_count", "replayed_prior_receipt_count", "stale_prior_receipt_count",
        "tampered_prior_receipt_count",
    )) and int(value.get("verified_prior_receipt_count") or 0) <= 1


def build_internally_generated_goal_candidate_reliability(
    projection: object, review_projection: object, *, prior_goal_candidate_receipts: object = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build one content-free fail-closed reliability assessment for ordinary conversation."""
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    diagnostics = _mapping(value.get("diagnostics"))
    candidate = value.get("candidate")
    review = _mapping(review_projection)
    state = _mapping(review.get("state"))
    packet = _mapping(review.get("review_packet"))
    prior = validate_prior_internally_generated_goal_candidate_receipts(
        prior_goal_candidate_receipts, now=now,
    )
    projection_valid = bool(
        _valid_digest(policy, "policy_digest")
        and _valid_digest(evidence, "evidence_digest")
        and verify_internally_generated_goal_candidate_diagnostics_strict(diagnostics)
        and diagnostics.get("policy_digest") == policy.get("policy_digest")
        and (candidate is None or verify_internally_generated_goal_candidate(candidate))
    )
    state_valid = verify_internally_generated_goal_candidate_review_state(state)
    packet_valid = verify_internally_generated_goal_candidate_review_packet(packet)
    recovered = bool(policy.get("policy_recovered"))
    residual = bool(recovered and (candidate is not None or state.get("candidate_available") or packet.get("candidate_available")))
    receipt_budget_exceeded = bool(prior.get("receipt_budget_exceeded"))
    faults = sum((
        int(not projection_valid), int(not state_valid), int(not packet_valid), int(recovered),
        int(residual), int(prior.get("recovery_required")), int(receipt_budget_exceeded),
    ))
    ready = faults == 0
    report = {
        "contract_version": RELIABILITY_CONTRACT_VERSION,
        "reliability_posture": "goal_candidate_context_reliable" if ready else "literal_current_request_only_recovery",
        "ordinary_conversation_ready": ready,
        "projection_valid": projection_valid,
        "review_state_valid": state_valid,
        "review_packet_valid": packet_valid,
        "prior_continuity_valid": not bool(prior.get("recovery_required")),
        "recovered_projection": recovered,
        "residual_candidate_detected": residual,
        "receipt_budget_exceeded": receipt_budget_exceeded,
        "fault_count": min(faults, MAX_RELIABILITY_FAULTS),
        "verified_prior_receipt_count": int(prior.get("verified_receipt_count") or 0),
        "replayed_prior_receipt_count": int(prior.get("replayed_receipt_count") or 0),
        "stale_prior_receipt_count": int(prior.get("stale_receipt_count") or 0),
        "malformed_prior_receipt_count": int(prior.get("malformed_receipt_count") or 0),
        "oversized_prior_receipt_count": int(prior.get("oversized_receipt_count") or 0),
        "tampered_prior_receipt_count": int(prior.get("tampered_receipt_count") or 0),
        "ignored_prior_receipt_count": int(prior.get("ignored_receipt_count") or 0),
        "candidate_available": bool(candidate) if ready else False,
        "review_available": bool(packet.get("candidate_available")) if ready else False,
        "literal_current_request_precedence": True,
        "historical_truth_preserved": True,
        "goal_activated": False,
        "plan_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "memory_mutated": False,
        "lesson_committed": False,
        "model_trained": False,
        "model_weights_changed": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "authority": "none",
        "content_free": True,
        "candidate_digest": str(candidate.get("candidate_digest") or "") if ready and isinstance(candidate, Mapping) else "",
        "review_state_digest": str(state.get("review_state_digest") or "") if ready else "",
        "review_packet_digest": str(packet.get("review_packet_digest") or "") if ready else "",
    }
    report["reliability_digest"] = _digest(report)
    return report


def verify_internally_generated_goal_candidate_reliability(value: object) -> bool:
    if not _exact_fields(value, _RELIABILITY_FIELDS):
        return False
    size, oversized = _bounded_json_bytes(value, MAX_RECEIPT_BYTES)
    if oversized or size > MAX_RECEIPT_BYTES:
        return False
    supplied = str(value.get("reliability_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "reliability_digest"}
    counts_valid = all(_bounded_count(value.get(field), MAX_PRIOR_RECEIPTS) for field in (
        "verified_prior_receipt_count", "replayed_prior_receipt_count", "stale_prior_receipt_count",
        "malformed_prior_receipt_count", "oversized_prior_receipt_count",
        "tampered_prior_receipt_count", "ignored_prior_receipt_count",
    ))
    ready = value.get("ordinary_conversation_ready")
    coherent = (
        (ready is True and value.get("reliability_posture") == "goal_candidate_context_reliable"
         and value.get("fault_count") == 0 and value.get("projection_valid") is True
         and value.get("review_state_valid") is True and value.get("review_packet_valid") is True)
        or
        (ready is False and value.get("reliability_posture") == "literal_current_request_only_recovery"
         and value.get("candidate_available") is False and value.get("review_available") is False
         and value.get("candidate_digest") == "" and value.get("review_state_digest") == ""
         and value.get("review_packet_digest") == "")
    )
    return bool(
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == RELIABILITY_CONTRACT_VERSION
        and isinstance(ready, bool) and coherent and counts_valid
        and _bounded_count(value.get("fault_count"), MAX_RELIABILITY_FAULTS)
        and value.get("verified_prior_receipt_count") <= 1
        and value.get("literal_current_request_precedence") is True
        and value.get("historical_truth_preserved") is True
        and all(value.get(field) is False for field in (
            "goal_activated", "plan_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
            "model_weights_changed", "installation_performed", "promotion_performed",
            "certification_performed",
        ))
        and value.get("authority") == "none" and value.get("content_free") is True
    )
