from __future__ import annotations

"""v1246 Initiative and Proposal Pacing.

This module prepares content-free, project-scoped initiative candidates and
pacing decisions.  It may recommend surfacing, asking one bounded question,
deferring, waiting, suppressing, or deliberate silence.  It never sends,
notifies, changes global preferences, mutates projects, or grants authority.
"""

import html
import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1246.8"
MILESTONE_NAME = "Initiative and Proposal Pacing"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"
MAX_RECORDS = 400

PROPOSAL_KINDS = {
    "development", "clarification", "risk", "continuation", "maintenance",
    "learning", "priority", "recovery",
}
PACING_CLASSIFICATIONS = {
    "surface_now", "ask_one_bounded_question", "defer_for_evidence",
    "wait_for_condition", "suppress_duplicate", "suppress_low_confidence",
    "suppress_operator_load", "deliberate_silence",
}
REVIEW_DISPOSITIONS = {"accept_surface", "defer", "dismiss", "request_changes"}

AUTHORITY_FLAGS = {
    "initiative_pacing_inspection_authorized": True,
    "initiative_candidate_preparation_authorized": True,
    "initiative_pacing_decision_preparation_authorized": True,
    "initiative_pacing_review_authorized": True,
    "message_send_authorized": False,
    "notification_send_authorized": False,
    "operator_preference_global_mutation_authorized": False,
    "priority_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "project_mutation_authorized": False,
    "requirement_mutation_authorized": False,
    "lesson_mutation_authorized": False,
    "goal_mutation_authorized": False,
    "motivation_mutation_authorized": False,
    "cognition_write_authorized": False,
    "provider_contact_authorized": False,
    "prompt_transmission_authorized": False,
    "tool_invocation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "session_launch_authorized": False,
    "session_resume_authorized": False,
    "automatic_retry_authorized": False,
    "background_continuation_authorized": False,
    "approval_creation_authorized": False,
    "approval_consumption_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
}

_TOKEN = re.compile(r"^[a-z][a-z0-9_\-]{1,96}$")
_PROJECT = re.compile(r"^project_[a-z0-9_\-]{2,64}$")
_CANDIDATE = re.compile(r"^initiative_proposal_candidate_[a-f0-9]{24}$")
_DECISION = re.compile(r"^initiative_pacing_decision_[a-f0-9]{24}$")
_REVIEW = re.compile(r"^initiative_pacing_review_[a-f0-9]{24}$")
_SNAPSHOT = re.compile(r"^project_understanding_snapshot_[a-f0-9]{24}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_PRIVATE = ("secret", "password", "credential", "prompt", "content", "endpoint", "private", "username", "email", "absolute_path")

_SHOW_REGISTRY = re.compile(r"^show initiative proposal pacing registry[.!?]*$", re.I)
_SHOW_CANDIDATES = re.compile(r"^show initiative proposal candidates[.!?]*$", re.I)
_SHOW_DECISIONS = re.compile(r"^show initiative pacing decisions[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show initiative pacing reviews[.!?]*$", re.I)
_REVIEW_DECISION = re.compile(
    r"^review initiative pacing (?P<disposition>accept_surface|defer|dismiss|request_changes) "
    r"for decision (?P<decision>initiative_pacing_decision_[a-f0-9]{24}) "
    r"digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _dir(name: str, runtime_root=None) -> Path:
    return _root(runtime_root) / name


def _path(name: str, record_id: str, runtime_root=None) -> Path:
    return _dir(name, runtime_root) / f"{str(record_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "initiative-proposal-pacing.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for initiative pacing lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _hex(value: Any, reason: str, *, allow_empty: bool = False) -> str:
    text = str(value or "").lower().strip()
    if allow_empty and not text:
        return ""
    if not _HEX64.fullmatch(text):
        raise ValueError(reason)
    return text


def _token(value: Any, reason: str, *, pattern: re.Pattern[str] = _TOKEN, allow_empty: bool = False) -> str:
    text = str(value or "").lower().strip()
    if allow_empty and not text:
        return ""
    if not pattern.fullmatch(text) or any(part in text for part in _PRIVATE):
        raise ValueError(reason)
    return text


def _score(value: Any, reason: str) -> float:
    try:
        number = round(float(value), 4)
    except (TypeError, ValueError):
        raise ValueError(reason)
    if number < 0 or number > 1:
        raise ValueError(reason)
    return number


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "runtime_records_external": True,
        "project_scoped": True,
        "historical_records_immutable": True,
        "exact_lineage_required": True,
        "deliberate_silence_supported": True,
        "duplicate_suppression_supported": True,
        "cooldown_enforced": True,
        "operator_attention_cost_respected": True,
        "single_bounded_question_maximum": True,
        "proposal_sent": False,
        "notification_sent": False,
        "operator_preferences_modified": False,
        "priority_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "project_modified": False,
        "requirements_modified": False,
        "lessons_modified": False,
        "goals_modified": False,
        "motivations_modified": False,
        "cognition_written": False,
        "provider_contacted": False,
        "prompt_transmitted": False,
        "tool_invoked": False,
        "commands_executed": False,
        "tests_executed": False,
        "session_launched": False,
        "session_resumed": False,
        "automatic_retry_created": False,
        "background_continuation_created": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["initiative_pacing_result_digest"] = _digest(row)
    return row


def initiative_proposal_pacing_registry() -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "initiative_proposal_pacing_registry_ready",
        "proposal_kinds": sorted(PROPOSAL_KINDS),
        "pacing_classifications": sorted(PACING_CLASSIFICATIONS),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        "inspection_only": True,
        **_base(),
    }
    row["registry_digest"] = _digest(row)
    return row


def prepare_initiative_proposal_candidate(
    project_id: str,
    *,
    proposal_code: str,
    proposal_kind: str,
    subject_digest: str,
    evidence_digests: Iterable[str],
    origin_system_code: str,
    origin_record_id: str,
    origin_record_digest: str,
    goal_alignment: float,
    urgency: float,
    confidence: float,
    novelty: float,
    operator_attention_cost: float,
    unresolved_dependency_count: int = 0,
    awaiting_authority: bool = False,
    future_condition_code: str = "more_evidence",
    generation: int = 1,
    project_understanding_snapshot_id: str = "",
    project_understanding_snapshot_digest: str = "",
    previous_candidate_id: str = "",
    previous_candidate_digest: str = "",
    prior_review_id: str = "",
    prior_review_digest: str = "",
    meaningful_change_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        project = _token(project_id, "invalid_project_id", pattern=_PROJECT)
        code = _token(proposal_code, "invalid_proposal_code")
        kind = _token(proposal_kind, "invalid_proposal_kind")
        if kind not in PROPOSAL_KINDS:
            raise ValueError("unsupported_proposal_kind")
        evidence = sorted({_hex(value, "invalid_evidence_digest") for value in evidence_digests or []})
        if not evidence:
            raise ValueError("proposal_evidence_required")
        origin_system = _token(origin_system_code, "invalid_origin_system_code")
        origin_id = _token(origin_record_id, "invalid_origin_record_id")
        origin_digest = _hex(origin_record_digest, "invalid_origin_record_digest")
        dependencies = int(unresolved_dependency_count)
        gen = int(generation)
        if dependencies < 0 or gen < 1:
            raise ValueError("invalid_candidate_counts")
        condition = _token(future_condition_code, "invalid_future_condition_code")
        snapshot_id = str(project_understanding_snapshot_id or "").lower().strip()
        snapshot_digest = str(project_understanding_snapshot_digest or "").lower().strip()
        if bool(snapshot_id) != bool(snapshot_digest):
            raise ValueError("project_understanding_lineage_incomplete")
        if snapshot_id:
            if not _SNAPSHOT.fullmatch(snapshot_id):
                raise ValueError("invalid_project_understanding_snapshot_id")
            from cross_session_project_understanding import load_project_understanding_snapshot
            snapshot = load_project_understanding_snapshot(snapshot_id, runtime_root=runtime_root)
            if not snapshot.get("ok") or snapshot.get("project_understanding_snapshot_digest") != _hex(snapshot_digest, "invalid_project_understanding_snapshot_digest"):
                raise ValueError("stale_or_mismatched_project_understanding_snapshot")
            if snapshot.get("project_id") != project:
                raise ValueError("cross_project_understanding_snapshot")
        previous_id = str(previous_candidate_id or "").lower().strip()
        previous_digest = str(previous_candidate_digest or "").lower().strip()
        review_id = str(prior_review_id or "").lower().strip()
        review_digest = str(prior_review_digest or "").lower().strip()
        change_digest = _hex(meaningful_change_digest, "invalid_meaningful_change_digest", allow_empty=True)
        if gen == 1:
            if any((previous_id, previous_digest, review_id, review_digest, change_digest)):
                raise ValueError("initial_candidate_cannot_have_resurfacing_lineage")
        else:
            if not all((previous_id, previous_digest, review_id, review_digest, change_digest)):
                raise ValueError("resurfaced_candidate_requires_exact_review_and_change")
            if not _CANDIDATE.fullmatch(previous_id) or not _REVIEW.fullmatch(review_id):
                raise ValueError("invalid_resurfacing_lineage_id")
            previous = load_initiative_proposal_candidate(previous_id, runtime_root=runtime_root)
            review = load_initiative_pacing_review(review_id, runtime_root=runtime_root)
            if not previous.get("ok") or previous.get("initiative_proposal_candidate_digest") != _hex(previous_digest, "invalid_previous_candidate_digest"):
                raise ValueError("stale_or_mismatched_previous_candidate")
            if not review.get("ok") or review.get("initiative_pacing_review_digest") != _hex(review_digest, "invalid_prior_review_digest"):
                raise ValueError("stale_or_mismatched_prior_review")
            if previous.get("project_id") != project or review.get("project_id") != project:
                raise ValueError("cross_project_resurfacing_lineage")
            if review.get("candidate_id") != previous_id:
                raise ValueError("prior_review_candidate_mismatch")
            if int(previous.get("generation") or 0) + 1 != gen:
                raise ValueError("nonsequential_candidate_generation")
        identity = {
            "project_id": project,
            "proposal_code": code,
            "proposal_kind": kind,
            "subject_digest": _hex(subject_digest, "invalid_subject_digest"),
            "evidence_digests": evidence,
            "origin_system_code": origin_system,
            "origin_record_id": origin_id,
            "origin_record_digest": origin_digest,
            "goal_alignment": _score(goal_alignment, "invalid_goal_alignment"),
            "urgency": _score(urgency, "invalid_urgency"),
            "confidence": _score(confidence, "invalid_confidence"),
            "novelty": _score(novelty, "invalid_novelty"),
            "operator_attention_cost": _score(operator_attention_cost, "invalid_operator_attention_cost"),
            "unresolved_dependency_count": dependencies,
            "awaiting_authority": bool(awaiting_authority),
            "future_condition_code": condition,
            "generation": gen,
            "project_understanding_snapshot_id": snapshot_id,
            "project_understanding_snapshot_digest": snapshot_digest,
            "previous_candidate_id": previous_id,
            "previous_candidate_digest": previous_digest,
            "prior_review_id": review_id,
            "prior_review_digest": review_digest,
            "meaningful_change_digest": change_digest,
        }
        candidate_id = "initiative_proposal_candidate_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "initiative_proposal_candidate_prepared",
            "candidate_id": candidate_id,
            **identity,
            "evidence_count": len(evidence),
            "resurfaced": gen > 1,
            "meaningful_change_required_for_resurfacing": True,
            "operator_specific_review_only": True,
            **_base(),
        }, "initiative_proposal_candidate_digest")
        with _lock(runtime_root):
            path = _path("initiative_proposal_candidates", candidate_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "initiative_proposal_candidate_digest") else _failure("initiative_proposal_candidate_tampered", "existing_candidate_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("initiative_proposal_candidate_blocked", str(exc))


def load_initiative_proposal_candidate(candidate_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(candidate_id or "").lower().strip()
    if not _CANDIDATE.fullmatch(token):
        return _failure("initiative_proposal_candidate_not_found", "invalid_candidate_id")
    row = _read_json(_path("initiative_proposal_candidates", token, runtime_root))
    if not row:
        return _failure("initiative_proposal_candidate_not_found", "candidate_missing")
    return row if _valid(row, "initiative_proposal_candidate_digest") else _failure("initiative_proposal_candidate_tampered", "candidate_digest_mismatch")


def prepare_initiative_pacing_decision(
    candidate_id: str,
    *,
    expected_candidate_digest: str,
    context_digest: str,
    logical_day: int,
    operator_present: bool,
    operator_receptive: bool,
    conversation_active: bool,
    operator_load: float,
    evidence_complete: bool,
    condition_satisfied: bool,
    cooldown_until_day: int = 0,
    recent_surface_count: int = 0,
    duplicate_candidate_id: str = "",
    duplicate_candidate_digest: str = "",
    topic_dismissed: bool = False,
    meaningful_change_since_review: bool = False,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        cid = str(candidate_id or "").lower().strip()
        if not _CANDIDATE.fullmatch(cid):
            raise ValueError("invalid_candidate_id")
        expected = _hex(expected_candidate_digest, "invalid_candidate_digest")
        candidate = load_initiative_proposal_candidate(cid, runtime_root=runtime_root)
        if not candidate.get("ok") or candidate.get("initiative_proposal_candidate_digest") != expected:
            raise ValueError("stale_or_mismatched_candidate")
        day = int(logical_day)
        cooldown = int(cooldown_until_day)
        recent = int(recent_surface_count)
        if day < 0 or cooldown < 0 or recent < 0:
            raise ValueError("invalid_pacing_counts")
        load = _score(operator_load, "invalid_operator_load")
        duplicate_id = str(duplicate_candidate_id or "").lower().strip()
        duplicate_digest = str(duplicate_candidate_digest or "").lower().strip()
        if bool(duplicate_id) != bool(duplicate_digest):
            raise ValueError("duplicate_lineage_incomplete")
        if duplicate_id:
            if not _CANDIDATE.fullmatch(duplicate_id) or duplicate_id == cid:
                raise ValueError("invalid_duplicate_candidate_id")
            duplicate = load_initiative_proposal_candidate(duplicate_id, runtime_root=runtime_root)
            if not duplicate.get("ok") or duplicate.get("initiative_proposal_candidate_digest") != _hex(duplicate_digest, "invalid_duplicate_candidate_digest"):
                raise ValueError("stale_or_mismatched_duplicate_candidate")
            if duplicate.get("project_id") != candidate.get("project_id"):
                raise ValueError("cross_project_duplicate_candidate")
        reason = "bounded_restraint"
        classification = "deliberate_silence"
        missing_evidence_count = 0 if evidence_complete else 1
        if duplicate_id:
            classification, reason = "suppress_duplicate", "exact_duplicate_evidence"
        elif topic_dismissed and not meaningful_change_since_review and not condition_satisfied:
            classification, reason = "wait_for_condition", "dismissed_topic_requires_change_or_condition"
        elif float(candidate.get("confidence") or 0) < 0.4:
            classification, reason = "suppress_low_confidence", "confidence_below_surface_threshold"
        elif load > 0.75 or not operator_present or not operator_receptive:
            classification, reason = "suppress_operator_load", "operator_attention_boundary"
        elif not evidence_complete or int(candidate.get("unresolved_dependency_count") or 0) > 0:
            classification, reason = "defer_for_evidence", "missing_or_unresolved_evidence"
        elif day < cooldown and not meaningful_change_since_review:
            classification, reason = "wait_for_condition", "cooldown_active"
        elif candidate.get("awaiting_authority"):
            classification, reason = "deliberate_silence", "another_authority_review_pending"
        elif candidate.get("proposal_kind") == "clarification" and conversation_active:
            classification, reason = "ask_one_bounded_question", "one_question_can_resolve_uncertainty"
        elif condition_satisfied and conversation_active and float(candidate.get("urgency") or 0) >= 0.7 and float(candidate.get("confidence") or 0) >= 0.65 and float(candidate.get("novelty") or 0) >= 0.45 and float(candidate.get("operator_attention_cost") or 1) <= 0.65 and recent < 2:
            classification, reason = "surface_now", "material_novel_high_confidence_change"
        elif not condition_satisfied:
            classification, reason = "wait_for_condition", "future_condition_not_satisfied"
        identity = {
            "candidate_id": cid,
            "candidate_digest": expected,
            "project_id": candidate.get("project_id"),
            "context_digest": _hex(context_digest, "invalid_context_digest"),
            "logical_day": day,
            "operator_present": bool(operator_present),
            "operator_receptive": bool(operator_receptive),
            "conversation_active": bool(conversation_active),
            "operator_load": load,
            "evidence_complete": bool(evidence_complete),
            "condition_satisfied": bool(condition_satisfied),
            "cooldown_until_day": cooldown,
            "recent_surface_count": recent,
            "duplicate_candidate_id": duplicate_id,
            "duplicate_candidate_digest": duplicate_digest,
            "topic_dismissed": bool(topic_dismissed),
            "meaningful_change_since_review": bool(meaningful_change_since_review),
            "classification": classification,
            "reason_code": reason,
        }
        decision_id = "initiative_pacing_decision_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "initiative_pacing_decision_prepared",
            "decision_id": decision_id,
            **identity,
            "why_proposal_matters_code": "goal_aligned_evidence_backed" if float(candidate.get("goal_alignment") or 0) >= 0.5 else "weak_goal_alignment",
            "why_now_code": reason,
            "what_changed_digest": candidate.get("meaningful_change_digest") or "",
            "missing_evidence_count": missing_evidence_count + int(candidate.get("unresolved_dependency_count") or 0),
            "future_condition_code": candidate.get("future_condition_code"),
            "bounded_question_count": 1 if classification == "ask_one_bounded_question" else 0,
            "operator_review_required": classification in {"surface_now", "ask_one_bounded_question"},
            "automatic_surface_performed": False,
            **_base(),
        }, "initiative_pacing_decision_digest")
        with _lock(runtime_root):
            path = _path("initiative_pacing_decisions", decision_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "initiative_pacing_decision_digest") else _failure("initiative_pacing_decision_tampered", "existing_decision_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("initiative_pacing_decision_blocked", str(exc))


def load_initiative_pacing_decision(decision_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(decision_id or "").lower().strip()
    if not _DECISION.fullmatch(token):
        return _failure("initiative_pacing_decision_not_found", "invalid_decision_id")
    row = _read_json(_path("initiative_pacing_decisions", token, runtime_root))
    if not row:
        return _failure("initiative_pacing_decision_not_found", "decision_missing")
    return row if _valid(row, "initiative_pacing_decision_digest") else _failure("initiative_pacing_decision_tampered", "decision_digest_mismatch")


def review_initiative_pacing_decision(
    decision_id: str,
    *,
    expected_decision_digest: str,
    disposition: str,
    exact_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        did = str(decision_id or "").lower().strip()
        if not _DECISION.fullmatch(did):
            raise ValueError("invalid_decision_id")
        expected = _hex(expected_decision_digest, "invalid_decision_digest")
        decision = load_initiative_pacing_decision(did, runtime_root=runtime_root)
        if not decision.get("ok") or decision.get("initiative_pacing_decision_digest") != expected:
            raise ValueError("stale_or_mismatched_decision")
        choice = _token(disposition, "invalid_review_disposition")
        if choice not in REVIEW_DISPOSITIONS:
            raise ValueError("unsupported_review_disposition")
        required = f"review initiative pacing {choice} for decision {did} digest {expected}"
        if str(exact_phrase or "").strip().lower().rstrip(".!?") != required:
            raise ValueError("exact_review_phrase_required")
        identity = {
            "decision_id": did,
            "decision_digest": expected,
            "candidate_id": decision.get("candidate_id"),
            "project_id": decision.get("project_id"),
            "disposition": choice,
        }
        review_id = "initiative_pacing_review_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "initiative_pacing_review_recorded",
            "review_id": review_id,
            **identity,
            "proposal_specific_only": True,
            "surface_interpretation_accepted": choice == "accept_surface",
            "dismissed_for_resurfacing_control": choice == "dismiss",
            "global_preference_unchanged": True,
            "message_not_sent": True,
            **_base(),
        }, "initiative_pacing_review_digest")
        with _lock(runtime_root):
            path = _path("initiative_pacing_reviews", review_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "initiative_pacing_review_digest") else _failure("initiative_pacing_review_tampered", "existing_review_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("initiative_pacing_review_blocked", str(exc))


def load_initiative_pacing_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(review_id or "").lower().strip()
    if not _REVIEW.fullmatch(token):
        return _failure("initiative_pacing_review_not_found", "invalid_review_id")
    row = _read_json(_path("initiative_pacing_reviews", token, runtime_root))
    if not row:
        return _failure("initiative_pacing_review_not_found", "review_missing")
    return row if _valid(row, "initiative_pacing_review_digest") else _failure("initiative_pacing_review_tampered", "review_digest_mismatch")


def _public_list(directory: str, seal_field: str, keys: Iterable[str], plural: str, runtime_root=None) -> dict[str, Any]:
    rows = []
    root = _dir(directory, runtime_root)
    for path in sorted(root.glob("*.json")) if root.exists() else []:
        row = _read_json(path)
        if row and _valid(row, seal_field):
            rows.append({key: row.get(key) for key in keys})
    rows = rows[-MAX_RECORDS:]
    result = {"ok": True, "status": f"{plural}_ready", plural: rows, "count": len(rows), "read_only": True, **_base()}
    result[f"{plural}_digest"] = _digest(rows)
    return result


def public_initiative_proposal_candidates(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("initiative_proposal_candidates", "initiative_proposal_candidate_digest", ("candidate_id", "project_id", "proposal_code", "proposal_kind", "generation", "urgency", "confidence", "novelty", "operator_attention_cost", "awaiting_authority", "future_condition_code", "initiative_proposal_candidate_digest"), "initiative_proposal_candidates", runtime_root)


def public_initiative_pacing_decisions(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("initiative_pacing_decisions", "initiative_pacing_decision_digest", ("decision_id", "candidate_id", "project_id", "classification", "reason_code", "logical_day", "operator_review_required", "future_condition_code", "initiative_pacing_decision_digest"), "initiative_pacing_decisions", runtime_root)


def public_initiative_pacing_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("initiative_pacing_reviews", "initiative_pacing_review_digest", ("review_id", "decision_id", "candidate_id", "project_id", "disposition", "surface_interpretation_accepted", "initiative_pacing_review_digest"), "initiative_pacing_reviews", runtime_root)


def initiative_pacing_dashboard_record(*, runtime_root=None) -> dict[str, Any]:
    candidates = public_initiative_proposal_candidates(runtime_root=runtime_root)
    decisions = public_initiative_pacing_decisions(runtime_root=runtime_root)
    reviews = public_initiative_pacing_reviews(runtime_root=runtime_root)
    counts = {state: 0 for state in PACING_CLASSIFICATIONS}
    for row in decisions["initiative_pacing_decisions"]:
        if row.get("classification") in counts:
            counts[row["classification"]] += 1
    row = {
        "ok": True,
        "status": "initiative_proposal_pacing_dashboard_ready",
        "read_only": True,
        "get_only": True,
        "candidate_count": candidates["count"],
        "decision_count": decisions["count"],
        "review_count": reviews["count"],
        "classification_counts": counts,
        "initiative_proposal_candidates": candidates["initiative_proposal_candidates"],
        "initiative_pacing_decisions": decisions["initiative_pacing_decisions"],
        "initiative_pacing_reviews": reviews["initiative_pacing_reviews"],
        **_base(),
    }
    row["dashboard_digest"] = _digest({key: value for key, value in row.items() if key != "dashboard_digest"})
    return row


def render_initiative_pacing_dashboard_html(*, runtime_root=None) -> str:
    row = initiative_pacing_dashboard_record(runtime_root=runtime_root)
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Initiative and Proposal Pacing</title>"
        "<style>body{font-family:system-ui;background:#111827;color:#e5e7eb;margin:0;padding:28px}.card{background:#1f2937;border:1px solid #374151;border-radius:12px;padding:18px;max-width:980px;margin:auto}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.metric{background:#111827;padding:14px;border-radius:8px}.muted{color:#9ca3af}</style></head><body><div class='card'>"
        "<h1>Initiative and Proposal Pacing</h1><p class='muted'>GET-only inspection. Pacing evidence never sends, notifies, executes, resumes, retries, or changes global preferences.</p>"
        f"<div class='grid'><div class='metric'>Candidates<br><b>{html.escape(str(row['candidate_count']))}</b></div>"
        f"<div class='metric'>Decisions<br><b>{html.escape(str(row['decision_count']))}</b></div>"
        f"<div class='metric'>Reviews<br><b>{html.escape(str(row['review_count']))}</b></div></div>"
        "<p>Supported outcomes include surface now, one bounded question, evidence deferral, condition waiting, duplicate suppression, low-confidence suppression, operator-load suppression, and deliberate silence.</p>"
        "</div></body></html>"
    )


def initiative_pacing_response(row: Mapping[str, Any]) -> str:
    status = str(row.get("status") or "")
    if not row.get("ok"):
        return f"Initiative pacing control was blocked: {row.get('reason') or status}. No message, notification, project change, or authority was created."
    if status.endswith("registry_ready"):
        return "The initiative and proposal pacing registry is ready for read-only inspection."
    if status.endswith("review_recorded"):
        return f"Recorded initiative pacing review {row.get('review_id')} as {row.get('disposition')}. No message was sent and no global preference or execution authority changed."
    return "Initiative pacing evidence is ready for read-only inspection. No proposal was automatically surfaced."


def process_initiative_pacing_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    row: dict[str, Any] | None = None
    if _SHOW_REGISTRY.fullmatch(text):
        row = initiative_proposal_pacing_registry()
    elif _SHOW_CANDIDATES.fullmatch(text):
        row = public_initiative_proposal_candidates(runtime_root=runtime_root)
    elif _SHOW_DECISIONS.fullmatch(text):
        row = public_initiative_pacing_decisions(runtime_root=runtime_root)
    elif _SHOW_REVIEWS.fullmatch(text):
        row = public_initiative_pacing_reviews(runtime_root=runtime_root)
    else:
        match = _REVIEW_DECISION.fullmatch(text)
        if match:
            row = review_initiative_pacing_decision(
                match.group("decision"),
                expected_decision_digest=match.group("digest"),
                disposition=match.group("disposition").lower(),
                exact_phrase=text,
                runtime_root=runtime_root,
            )
    if row is None:
        return {"active": False}
    return {"active": True, "initiative_pacing": row, "response": initiative_pacing_response(row), "action_taken": False, "execution_started": False, "message_sent": False, "notification_sent": False}


def build_initiative_proposal_pacing_contract() -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "initiative_proposal_pacing_contract_ready",
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "proposal_eligibility_and_novelty": True,
        "urgency_confidence_and_attention_cost": True,
        "cooldowns_and_duplicate_suppression": True,
        "unresolved_dependency_awareness": True,
        "eight_pacing_classifications": True,
        "one_bounded_question_maximum": True,
        "operator_specific_review": True,
        "dismissed_topic_requires_change_or_condition": True,
        "resurfacing_requires_exact_review_and_meaningful_change": True,
        "ordinary_chat_review": True,
        "cli_and_get_only_inspection": True,
        "deliberate_silence_is_valid": True,
        "no_automatic_notification_or_surface": True,
        "no_global_preference_mutation": True,
        "no_execution_authority": True,
        "runtime_records_external": True,
        **_base(),
    }
    row["contract_digest"] = _digest(row)
    return row
