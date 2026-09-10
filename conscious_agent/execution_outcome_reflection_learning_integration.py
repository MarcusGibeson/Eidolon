from __future__ import annotations

"""Evidence-bound execution outcome reflection and learning integration.

v1229 derives content-free outcome evidence from the exact v1226-v1228
execution lineage, prepares a bounded reflection subject, and records an
operator-reviewed, project-scoped lesson. Reflection and learning records are
external evidence only. They do not modify cognition, projects, schedules,
queues, approvals, launches, providers, commands, tests, installation,
promotion, release, or model-management state.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from execution_session_authorization_bounded_launch import (
    inspect_bounded_development_execution_session,
    load_bounded_development_execution_session,
)
from live_execution_monitoring_operator_intervention import (
    inspect_live_execution_monitoring,
    load_live_execution_monitoring,
)
from execution_session_pause_resume_cancel_recovery import inspect_execution_session_control

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1229.8"
MAX_OUTCOMES = 100
MAX_REFLECTIONS = 100
MAX_LESSON_REVIEWS = 200
MAX_RECONSIDERATIONS = 200
MAX_LESSON_CODES = 4

OUTCOME_TYPES = {
    "completed", "failed", "cancelled", "paused", "recovered", "abandoned", "inconclusive",
}
ACHIEVEMENT_CLASSIFICATIONS = {"achieved", "partially_achieved", "failed", "inconclusive"}
LESSON_CODES = {
    "retain_bounded_approach",
    "strengthen_authorization_checks",
    "strengthen_recovery_checks",
    "strengthen_dependency_checks",
    "preserve_operator_intervention",
    "require_more_evidence",
    "avoid_repeating_approach",
    "no_durable_lesson",
}
LESSON_DISPOSITIONS = {"accept", "reject", "defer", "revise", "suspend"}
RECONSIDERATION_DECISIONS = {"retain", "revise", "suspend", "reopen", "unresolved"}
CONTRADICTORY_LESSON_PAIRS = {
    frozenset({"retain_bounded_approach", "avoid_repeating_approach"}),
    frozenset({"no_durable_lesson", "retain_bounded_approach"}),
    frozenset({"no_durable_lesson", "strengthen_authorization_checks"}),
    frozenset({"no_durable_lesson", "strengthen_recovery_checks"}),
    frozenset({"no_durable_lesson", "strengthen_dependency_checks"}),
    frozenset({"no_durable_lesson", "preserve_operator_intervention"}),
}

AUTHORITY_FLAGS = {
    "outcome_evidence_authorized": True,
    "reflection_subject_authorized": True,
    "lesson_review_authorized": True,
    "durable_project_scoped_learning_authorized": False,
    "cognition_write_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "launch_authorized": False,
    "background_execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

_PREPARE_OUTCOME = re.compile(
    r"^prepare execution outcome (?P<kind>completed|failed|cancelled|paused|recovered|abandoned|inconclusive) "
    r"for bounded development execution session (?P<launch>launch_[a-f0-9]{24}) digest (?P<launch_digest>[a-f0-9]{64}) "
    r"monitor digest (?P<monitor_digest>[a-f0-9]{64}) control digest (?P<control_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_OUTCOMES = re.compile(r"^show execution outcomes[.!?]*$", re.I)
_PREPARE_REFLECTION = re.compile(
    r"^prepare execution outcome reflection for outcome (?P<outcome>outcome_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_REFLECTIONS = re.compile(r"^show execution outcome reflections[.!?]*$", re.I)
_REVIEW = re.compile(
    r"^review execution outcome lesson (?P<decision>accept|reject|defer|suspend) for reflection "
    r"(?P<reflection>reflection_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_REVISE = re.compile(
    r"^review execution outcome lesson revise for reflection (?P<reflection>reflection_[a-f0-9]{24}) "
    r"digest (?P<digest>[a-f0-9]{64}) with lesson codes (?P<codes>[a-z_, -]+)[.!?]*$",
    re.I,
)
_SHOW_REVIEWS = re.compile(r"^show execution outcome lesson reviews[.!?]*$", re.I)
_RECONSIDER = re.compile(
    r"^reconsider execution outcome lesson (?P<decision>retain|revise|suspend|reopen|unresolved) for review "
    r"(?P<review>lesson_review_[a-f0-9]{24}) digest (?P<review_digest>[a-f0-9]{64}) using outcome "
    r"(?P<outcome>outcome_[a-f0-9]{24}) digest (?P<outcome_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_RECONSIDERATIONS = re.compile(r"^show execution outcome lesson reconsiderations[.!?]*$", re.I)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _outcome_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "execution_outcomes"


def _outcome_path(outcome_id: str, runtime_root=None) -> Path:
    return _outcome_root(runtime_root) / f"{str(outcome_id or '').lower()}.json"


def _outcome_index_path(launch_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "execution_outcome_indexes" / f"{str(launch_id or '').lower()}.json"


def _reflection_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "execution_outcome_reflections"


def _reflection_path(reflection_id: str, runtime_root=None) -> Path:
    return _reflection_root(runtime_root) / f"{str(reflection_id or '').lower()}.json"


def _reflection_index_path(outcome_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "execution_outcome_reflection_indexes" / f"{str(outcome_id or '').lower()}.json"


def _review_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "execution_outcome_lesson_reviews"


def _review_path(review_id: str, runtime_root=None) -> Path:
    return _review_root(runtime_root) / f"{str(review_id or '').lower()}.json"


def _review_index_path(reflection_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "execution_outcome_lesson_review_indexes" / f"{str(reflection_id or '').lower()}.json"


def _reconsideration_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "execution_outcome_lesson_reconsiderations"


def _reconsideration_path(reconsideration_id: str, runtime_root=None) -> Path:
    return _reconsideration_root(runtime_root) / f"{str(reconsideration_id or '').lower()}.json"


def _reconsideration_index_path(review_id: str, later_outcome_id: str, runtime_root=None) -> Path:
    token = _digest({"review_id": str(review_id or '').lower(), "later_outcome_id": str(later_outcome_id or '').lower()})
    return _root(runtime_root) / "execution_outcome_lesson_reconsideration_indexes" / f"{token}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "execution-outcome-reflection-learning.lock"
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
                raise TimeoutError("Timed out waiting for execution outcome reflection lock")
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


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "runtime_records_external": True,
        "operator_review_required": True,
        "facts_separated_from_interpretation": True,
        "uncertainty_preserved": True,
        "project_scoped_only": True,
        "generalized_beyond_project": False,
        "historical_truth_preserved": True,
        "reflection_is_not_cognition_write": True,
        "learning_is_revisable": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "cognition_written": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_name_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["execution_outcome_reflection_learning_result_digest"] = _digest(row)
    return row


def _rows(path: Path, validator) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not path.exists():
        return result
    for child in sorted(path.glob("*.json")):
        row = _read_json(child)
        if row and validator(row):
            result.append(row)
    return result


def _validate_outcome(row: Mapping[str, Any]) -> bool:
    return (
        _valid(row, "execution_outcome_record_digest")
        and str(row.get("outcome_id") or "").startswith("outcome_")
        and str(row.get("launch_id") or "").startswith("launch_")
        and str(row.get("outcome_type") or "") in OUTCOME_TYPES
        and str(row.get("achievement_classification") or "") in ACHIEVEMENT_CLASSIFICATIONS
        and isinstance(row.get("observed_fact_codes"), list)
        and isinstance(row.get("uncertainty_codes"), list)
        and row.get("cognition_written") is False
        and row.get("project_mutation_authorized") is False
    )


def _validate_reflection(row: Mapping[str, Any]) -> bool:
    return (
        _valid(row, "execution_outcome_reflection_record_digest")
        and str(row.get("reflection_id") or "").startswith("reflection_")
        and str(row.get("outcome_id") or "").startswith("outcome_")
        and str(row.get("reflection_status") or "") in {"candidate_ready", "deliberate_silence"}
        and all(code in LESSON_CODES for code in list(row.get("candidate_lesson_codes") or []))
        and row.get("cognition_written") is False
    )


def _validate_review(row: Mapping[str, Any]) -> bool:
    return (
        _valid(row, "execution_outcome_lesson_review_record_digest")
        and str(row.get("review_id") or "").startswith("lesson_review_")
        and str(row.get("reflection_id") or "").startswith("reflection_")
        and str(row.get("disposition") or "") in LESSON_DISPOSITIONS
        and all(code in LESSON_CODES for code in list(row.get("lesson_codes") or []))
        and row.get("cognition_written") is False
        and row.get("project_mutation_authorized") is False
    )


def _validate_reconsideration(row: Mapping[str, Any]) -> bool:
    return (
        _valid(row, "execution_outcome_lesson_reconsideration_record_digest")
        and str(row.get("reconsideration_id") or "").startswith("reconsideration_")
        and str(row.get("review_id") or "").startswith("lesson_review_")
        and str(row.get("later_outcome_id") or "").startswith("outcome_")
        and str(row.get("decision") or "") in RECONSIDERATION_DECISIONS
        and row.get("cognition_written") is False
        and row.get("project_mutation_authorized") is False
    )


def _load_outcome(outcome_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_outcome_path(str(outcome_id or "").lower(), runtime_root))
    return row if row and _validate_outcome(row) else {}


def _load_reflection(reflection_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_reflection_path(str(reflection_id or "").lower(), runtime_root))
    return row if row and _validate_reflection(row) else {}


def _load_review(review_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_review_path(str(review_id or "").lower(), runtime_root))
    return row if row and _validate_review(row) else {}


def _load_reconsideration(reconsideration_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_reconsideration_path(str(reconsideration_id or "").lower(), runtime_root))
    return row if row and _validate_reconsideration(row) else {}


def _achievement(outcome_type: str, progress_percent: int) -> str:
    if outcome_type == "completed":
        return "achieved"
    if outcome_type in {"failed", "abandoned"}:
        return "failed"
    if outcome_type in {"paused", "recovered", "cancelled"} and progress_percent > 0:
        return "partially_achieved"
    return "inconclusive"


def _outcome_supported(outcome_type: str, monitor: Mapping[str, Any], control: Mapping[str, Any]) -> tuple[bool, list[str], list[str]]:
    stage = str(monitor.get("current_stage") or "")
    state = str(control.get("session_state") or "")
    progress = int(monitor.get("progress_percent") or 0)
    blockers = list(monitor.get("blocker_codes") or [])
    risks = list(monitor.get("risk_codes") or [])
    facts = [f"monitor_stage:{stage}", f"control_state:{state}", f"progress_bucket:{min(100, max(0, progress)) // 25 * 25}"]
    uncertainties: list[str] = []
    supported = False
    if outcome_type == "completed":
        supported = stage == "completed_pending_review" and progress == 100
        if not supported: uncertainties.append("completion_not_verified")
    elif outcome_type == "failed":
        supported = stage == "blocked" and any(code != "authorization_required" for code in blockers)
        if not supported: uncertainties.append("failure_not_verified")
    elif outcome_type == "cancelled":
        supported = state == "cancelled"
        if not supported: uncertainties.append("cancellation_not_verified")
    elif outcome_type == "paused":
        supported = state == "paused"
        if not supported: uncertainties.append("pause_not_verified")
    elif outcome_type == "recovered":
        supported = state == "paused" and int(control.get("recovery_attempts") or 0) > 0
        if not supported: uncertainties.append("recovery_not_verified")
    elif outcome_type == "abandoned":
        supported = state == "cancelled"
        uncertainties.append("abandonment_is_operator_classification")
    elif outcome_type == "inconclusive":
        supported = True
        uncertainties.append("terminal_outcome_not_established")
    facts.extend(f"blocker:{code}" for code in blockers[:8])
    facts.extend(f"risk:{code}" for code in risks[:8])
    return supported, sorted(set(facts)), sorted(set(uncertainties))


def prepare_execution_outcome(
    launch_id: str,
    *,
    outcome_type: str,
    expected_launch_digest: str,
    expected_monitor_digest: str,
    expected_control_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        launch_id = str(launch_id or "").lower()
        outcome_type = str(outcome_type or "").lower()
        if outcome_type not in OUTCOME_TYPES:
            raise ValueError("unsupported_outcome_type")
        launch = inspect_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
        if launch.get("ok") is not True:
            launch = load_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
        monitor = inspect_live_execution_monitoring(launch_id, runtime_root=runtime_root)
        if monitor.get("ok") is not True:
            monitor = load_live_execution_monitoring(launch_id, runtime_root=runtime_root)
        control = inspect_execution_session_control(launch_id, runtime_root=runtime_root)
        if launch.get("ok") is not True or str(launch.get("launch_digest") or "") != str(expected_launch_digest or "").lower():
            raise ValueError("stale_or_invalid_launch")
        if monitor.get("ok") is not True or str(monitor.get("monitor_digest") or "") != str(expected_monitor_digest or "").lower():
            raise ValueError("stale_or_invalid_monitor")
        if control.get("ok") is not True or str(control.get("control_digest") or "") != str(expected_control_digest or "").lower():
            raise ValueError("stale_or_invalid_control")
        for key in ("project_reference", "queue_item_id", "proposal_id", "source_session_id"):
            if str(launch.get(key) or "") != str(monitor.get(key) or "") or str(launch.get(key) or "") != str(control.get(key) or ""):
                raise ValueError("cross_lineage_evidence")
        supported, facts, uncertainties = _outcome_supported(outcome_type, monitor, control)
        if not supported and outcome_type != "inconclusive":
            raise ValueError(uncertainties[0] if uncertainties else "outcome_not_supported")
        identity = {
            "launch_id": launch_id,
            "launch_digest": launch["launch_digest"],
            "monitor_digest": monitor["monitor_digest"],
            "control_digest": control["control_digest"],
            "outcome_type": outcome_type,
        }
        outcome_id = f"outcome_{_digest(identity)[:24]}"
        existing_index = _read_json(_outcome_index_path(launch_id, runtime_root))
        if existing_index:
            existing = _load_outcome(str(existing_index.get("outcome_id") or ""), runtime_root)
            if existing and existing.get("outcome_type") == outcome_type and existing.get("monitor_digest") == monitor.get("monitor_digest") and existing.get("control_digest") == control.get("control_digest"):
                return {**existing, "operation_status": "replayed"}
            if existing and existing.get("outcome_type") != "inconclusive":
                raise ValueError("conflicting_terminal_outcome")
        row = {
            "ok": True,
            "status": "execution_outcome_ready_for_reflection",
            "outcome_id": outcome_id,
            "outcome_digest": _digest(identity),
            "outcome_type": outcome_type,
            "achievement_classification": _achievement(outcome_type, int(monitor.get("progress_percent") or 0)),
            "launch_id": launch_id,
            "launch_digest": launch["launch_digest"],
            "monitor_id": monitor.get("monitor_id", ""),
            "monitor_digest": monitor["monitor_digest"],
            "control_id": control.get("control_id", ""),
            "control_digest": control["control_digest"],
            "project_reference": launch.get("project_reference", ""),
            "queue_item_id": launch.get("queue_item_id", ""),
            "proposal_id": launch.get("proposal_id", ""),
            "source_session_id": launch.get("source_session_id", ""),
            "observed_fact_codes": facts,
            "uncertainty_codes": uncertainties,
            "evidence_complete": not uncertainties or outcome_type in {"abandoned", "inconclusive"},
            "reflection_review_required": True,
            "operation_status": "created",
            **_base(),
        }
        row = _sealed(row, "execution_outcome_record_digest")
        with _lock(runtime_root):
            _atomic_json(_outcome_path(outcome_id, runtime_root), row)
            _atomic_json(_outcome_index_path(launch_id, runtime_root), {
                "outcome_id": outcome_id,
                "outcome_digest": row["outcome_digest"],
                "execution_outcome_record_digest": row["execution_outcome_record_digest"],
                "content_free": True,
            })
        return row
    except (OSError, ValueError) as exc:
        return _failure("execution_outcome_blocked", str(exc))


def _candidate_codes(outcome: Mapping[str, Any]) -> list[str]:
    kind = str(outcome.get("outcome_type") or "")
    facts = set(outcome.get("observed_fact_codes") or [])
    uncertainty = list(outcome.get("uncertainty_codes") or [])
    codes: list[str] = []
    if kind == "inconclusive" and uncertainty and not any(
        fact.startswith("blocker:") and fact != "blocker:authorization_required" for fact in facts
    ) and not any(fact.startswith("risk:") and fact != "risk:none" for fact in facts):
        return ["no_durable_lesson"]
    if kind == "completed": codes.append("retain_bounded_approach")
    if kind == "failed": codes.append("strengthen_dependency_checks")
    if kind in {"recovered", "paused", "cancelled", "abandoned"}: codes.append("preserve_operator_intervention")
    if kind == "recovered": codes.append("strengthen_recovery_checks")
    if any("authorization_required" in fact for fact in facts): codes.append("strengthen_authorization_checks")
    if uncertainty: codes.append("require_more_evidence")
    if kind == "inconclusive" and not codes: codes.append("no_durable_lesson")
    return list(dict.fromkeys(codes))[:MAX_LESSON_CODES]


def prepare_execution_outcome_reflection(outcome_id: str, *, expected_outcome_digest: str, runtime_root=None) -> dict[str, Any]:
    try:
        outcome = _load_outcome(str(outcome_id or "").lower(), runtime_root)
        if not outcome or str(outcome.get("outcome_digest") or "") != str(expected_outcome_digest or "").lower():
            raise ValueError("stale_or_invalid_outcome")
        existing_index = _read_json(_reflection_index_path(outcome["outcome_id"], runtime_root))
        if existing_index:
            existing = _load_reflection(str(existing_index.get("reflection_id") or ""), runtime_root)
            if existing and existing.get("outcome_digest") == outcome.get("outcome_digest"):
                return {**existing, "operation_status": "replayed"}
        codes = _candidate_codes(outcome)
        deliberate_silence = codes == ["no_durable_lesson"] or not codes
        identity = {"outcome_id": outcome["outcome_id"], "outcome_digest": outcome["outcome_digest"], "codes": codes}
        reflection_id = f"reflection_{_digest(identity)[:24]}"
        row = {
            "ok": True,
            "status": "execution_outcome_reflection_ready_for_review" if not deliberate_silence else "execution_outcome_reflection_deliberate_silence",
            "reflection_id": reflection_id,
            "reflection_digest": _digest(identity),
            "reflection_status": "deliberate_silence" if deliberate_silence else "candidate_ready",
            "outcome_id": outcome["outcome_id"],
            "outcome_digest": outcome["outcome_digest"],
            "outcome_type": outcome["outcome_type"],
            "achievement_classification": outcome["achievement_classification"],
            "project_reference": outcome["project_reference"],
            "candidate_lesson_codes": codes,
            "supporting_fact_codes": list(outcome.get("observed_fact_codes") or []),
            "uncertainty_codes": list(outcome.get("uncertainty_codes") or []),
            "lesson_review_required": not deliberate_silence,
            "deliberate_silence": deliberate_silence,
            "operation_status": "created",
            **_base(),
        }
        row = _sealed(row, "execution_outcome_reflection_record_digest")
        with _lock(runtime_root):
            _atomic_json(_reflection_path(reflection_id, runtime_root), row)
            _atomic_json(_reflection_index_path(outcome["outcome_id"], runtime_root), {
                "reflection_id": reflection_id,
                "reflection_digest": row["reflection_digest"],
                "execution_outcome_reflection_record_digest": row["execution_outcome_reflection_record_digest"],
                "content_free": True,
            })
        return row
    except (OSError, ValueError) as exc:
        return _failure("execution_outcome_reflection_blocked", str(exc))


def _normalize_lesson_codes(values: Iterable[str]) -> list[str]:
    codes = [str(value or "").strip().lower().replace("-", "_").replace(" ", "_") for value in values]
    codes = [code for code in codes if code]
    if not codes or len(codes) > MAX_LESSON_CODES or len(codes) != len(set(codes)):
        raise ValueError("invalid_lesson_codes")
    if any(code not in LESSON_CODES for code in codes):
        raise ValueError("unsupported_lesson_code")
    for pair in CONTRADICTORY_LESSON_PAIRS:
        if pair.issubset(set(codes)):
            raise ValueError("contradictory_lesson_codes")
    return codes


def _active_contradiction(project_reference: str, codes: Iterable[str], runtime_root=None) -> bool:
    proposed = set(codes)
    for row in _rows(_review_root(runtime_root), _validate_review):
        if row.get("project_reference") != project_reference or row.get("lesson_active") is not True:
            continue
        existing = set(row.get("lesson_codes") or [])
        for pair in CONTRADICTORY_LESSON_PAIRS:
            if pair & proposed and pair & existing and (pair.issubset(proposed | existing)):
                if proposed != existing:
                    return True
    return False


def review_execution_outcome_lesson(
    reflection_id: str,
    *,
    expected_reflection_digest: str,
    disposition: str,
    revised_lesson_codes: Iterable[str] | None = None,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        reflection = _load_reflection(str(reflection_id or "").lower(), runtime_root)
        disposition = str(disposition or "").lower()
        if not reflection or str(reflection.get("reflection_digest") or "") != str(expected_reflection_digest or "").lower():
            raise ValueError("stale_or_invalid_reflection")
        if disposition not in LESSON_DISPOSITIONS:
            raise ValueError("unsupported_lesson_disposition")
        if reflection.get("reflection_status") == "deliberate_silence" and disposition in {"accept", "revise"}:
            raise ValueError("no_lesson_candidate_to_accept")
        existing_index = _read_json(_review_index_path(reflection["reflection_id"], runtime_root))
        if existing_index:
            existing = _load_review(str(existing_index.get("review_id") or ""), runtime_root)
            if existing and existing.get("disposition") == disposition:
                return {**existing, "operation_status": "replayed"}
            if existing:
                raise ValueError("conflicting_lesson_review")
        codes = list(reflection.get("candidate_lesson_codes") or [])
        if disposition == "revise":
            codes = _normalize_lesson_codes(revised_lesson_codes or [])
        elif codes:
            codes = _normalize_lesson_codes(codes)
        if disposition in {"accept", "revise"} and _active_contradiction(str(reflection.get("project_reference") or ""), codes, runtime_root):
            raise ValueError("contradictory_active_project_lesson")
        identity = {
            "reflection_id": reflection["reflection_id"],
            "reflection_digest": reflection["reflection_digest"],
            "disposition": disposition,
            "lesson_codes": codes,
        }
        review_id = f"lesson_review_{_digest(identity)[:24]}"
        row = {
            "ok": True,
            "status": {
                "accept": "execution_outcome_lesson_accepted",
                "reject": "execution_outcome_lesson_rejected",
                "defer": "execution_outcome_lesson_deferred",
                "revise": "execution_outcome_lesson_revised",
                "suspend": "execution_outcome_lesson_suspended",
            }[disposition],
            "review_id": review_id,
            "review_digest": _digest(identity),
            "reflection_id": reflection["reflection_id"],
            "reflection_digest": reflection["reflection_digest"],
            "outcome_id": reflection["outcome_id"],
            "outcome_digest": reflection["outcome_digest"],
            "project_reference": reflection["project_reference"],
            "disposition": disposition,
            "lesson_codes": codes,
            "durable_project_scoped_learning_recorded": disposition == "accept",
            "lesson_active": disposition in {"accept", "revise"},
            "lesson_suspended": disposition == "suspend",
            "lesson_deferred": disposition == "defer",
            "lesson_rejected": disposition == "reject",
            "reconsideration_required_if_evidence_changes": disposition in {"accept", "revise", "suspend"},
            "operation_status": "created",
            **_base(),
        }
        row["durable_project_scoped_learning_authorized"] = disposition == "accept"
        row = _sealed(row, "execution_outcome_lesson_review_record_digest")
        with _lock(runtime_root):
            _atomic_json(_review_path(review_id, runtime_root), row)
            _atomic_json(_review_index_path(reflection["reflection_id"], runtime_root), {
                "review_id": review_id,
                "review_digest": row["review_digest"],
                "execution_outcome_lesson_review_record_digest": row["execution_outcome_lesson_review_record_digest"],
                "content_free": True,
            })
        return row
    except (OSError, ValueError) as exc:
        return _failure("execution_outcome_lesson_review_blocked", str(exc))


def reconsider_execution_outcome_lesson(
    review_id: str,
    *,
    expected_review_digest: str,
    later_outcome_id: str,
    expected_later_outcome_digest: str,
    decision: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        review = _load_review(str(review_id or "").lower(), runtime_root)
        later = _load_outcome(str(later_outcome_id or "").lower(), runtime_root)
        decision = str(decision or "").lower()
        if not review or str(review.get("review_digest") or "") != str(expected_review_digest or "").lower():
            raise ValueError("stale_or_invalid_lesson_review")
        if not later or str(later.get("outcome_digest") or "") != str(expected_later_outcome_digest or "").lower():
            raise ValueError("stale_or_invalid_later_outcome")
        if decision not in RECONSIDERATION_DECISIONS:
            raise ValueError("unsupported_reconsideration_decision")
        if review.get("project_reference") != later.get("project_reference"):
            raise ValueError("cross_project_reconsideration_rejected")
        index = _read_json(_reconsideration_index_path(review["review_id"], later["outcome_id"], runtime_root))
        if index:
            existing = _load_reconsideration(str(index.get("reconsideration_id") or ""), runtime_root)
            if existing and existing.get("decision") == decision:
                return {**existing, "operation_status": "replayed"}
            if existing:
                raise ValueError("conflicting_lesson_reconsideration")
        identity = {
            "review_id": review["review_id"], "review_digest": review["review_digest"],
            "later_outcome_id": later["outcome_id"], "later_outcome_digest": later["outcome_digest"],
            "decision": decision,
        }
        reconsideration_id = f"reconsideration_{_digest(identity)[:24]}"
        row = {
            "ok": True,
            "status": f"execution_outcome_lesson_reconsideration_{decision}",
            "reconsideration_id": reconsideration_id,
            "reconsideration_digest": _digest(identity),
            "review_id": review["review_id"],
            "review_digest": review["review_digest"],
            "later_outcome_id": later["outcome_id"],
            "later_outcome_digest": later["outcome_digest"],
            "project_reference": review["project_reference"],
            "decision": decision,
            "prior_lesson_codes": list(review.get("lesson_codes") or []),
            "later_outcome_type": later.get("outcome_type", ""),
            "later_uncertainty_codes": list(later.get("uncertainty_codes") or []),
            "lesson_retained": decision == "retain",
            "lesson_revision_required": decision == "revise",
            "lesson_suspended": decision == "suspend",
            "lesson_reopened_for_review": decision == "reopen",
            "lesson_unresolved": decision == "unresolved",
            "new_operator_review_required": decision in {"revise", "reopen", "unresolved"},
            "operation_status": "created",
            **_base(),
        }
        row = _sealed(row, "execution_outcome_lesson_reconsideration_record_digest")
        with _lock(runtime_root):
            _atomic_json(_reconsideration_path(reconsideration_id, runtime_root), row)
            _atomic_json(_reconsideration_index_path(review["review_id"], later["outcome_id"], runtime_root), {
                "reconsideration_id": reconsideration_id,
                "reconsideration_digest": row["reconsideration_digest"],
                "execution_outcome_lesson_reconsideration_record_digest": row["execution_outcome_lesson_reconsideration_record_digest"],
                "content_free": True,
            })
        return row
    except (OSError, ValueError) as exc:
        return _failure("execution_outcome_lesson_reconsideration_blocked", str(exc))


def _public(row: Mapping[str, Any], *, kind: str) -> dict[str, Any]:
    if row.get("ok") is not True:
        return {key: row.get(key) for key in ("ok", "status", "reason") if key in row} | _base()
    allowed_by_kind = {
        "outcome": {
            "ok", "status", "outcome_id", "outcome_digest", "outcome_type", "achievement_classification",
            "launch_id", "project_reference", "queue_item_id", "proposal_id", "observed_fact_codes",
            "uncertainty_codes", "evidence_complete", "reflection_review_required", "operation_status",
        },
        "reflection": {
            "ok", "status", "reflection_id", "reflection_digest", "reflection_status", "outcome_id",
            "outcome_digest", "outcome_type", "achievement_classification", "project_reference",
            "candidate_lesson_codes", "supporting_fact_codes", "uncertainty_codes", "lesson_review_required",
            "deliberate_silence", "operation_status",
        },
        "review": {
            "ok", "status", "review_id", "review_digest", "reflection_id", "reflection_digest", "outcome_id",
            "outcome_digest", "project_reference", "disposition", "lesson_codes",
            "durable_project_scoped_learning_recorded", "lesson_active", "lesson_suspended", "lesson_deferred",
            "lesson_rejected", "reconsideration_required_if_evidence_changes", "operation_status",
        },
        "reconsideration": {
            "ok", "status", "reconsideration_id", "reconsideration_digest", "review_id", "review_digest",
            "later_outcome_id", "later_outcome_digest", "project_reference", "decision", "prior_lesson_codes",
            "later_outcome_type", "later_uncertainty_codes", "lesson_retained", "lesson_revision_required",
            "lesson_suspended", "lesson_reopened_for_review", "lesson_unresolved", "new_operator_review_required",
            "operation_status",
        },
    }
    public = {key: row.get(key) for key in allowed_by_kind[kind] if key in row}
    public.update(_base())
    if kind == "review":
        public["durable_project_scoped_learning_authorized"] = bool(row.get("durable_project_scoped_learning_authorized"))
    public[f"public_execution_outcome_{kind}_digest"] = _digest(public)
    return public


def public_execution_outcomes(*, runtime_root=None) -> dict[str, Any]:
    rows = [_public(row, kind="outcome") for row in _rows(_outcome_root(runtime_root), _validate_outcome)][-MAX_OUTCOMES:]
    result = {"ok": True, "status": "execution_outcome_list_ready", "outcome_count": len(rows), "outcomes": rows, **_base()}
    result["public_execution_outcome_list_digest"] = _digest(result)
    return result


def public_execution_outcome_reflections(*, runtime_root=None) -> dict[str, Any]:
    rows = [_public(row, kind="reflection") for row in _rows(_reflection_root(runtime_root), _validate_reflection)][-MAX_REFLECTIONS:]
    result = {"ok": True, "status": "execution_outcome_reflection_list_ready", "reflection_count": len(rows), "reflections": rows, **_base()}
    result["public_execution_outcome_reflection_list_digest"] = _digest(result)
    return result


def public_execution_outcome_lesson_reviews(*, runtime_root=None) -> dict[str, Any]:
    rows = [_public(row, kind="review") for row in _rows(_review_root(runtime_root), _validate_review)][-MAX_LESSON_REVIEWS:]
    result = {"ok": True, "status": "execution_outcome_lesson_review_list_ready", "review_count": len(rows), "reviews": rows, **_base()}
    result["public_execution_outcome_lesson_review_list_digest"] = _digest(result)
    return result


def public_execution_outcome_lesson_reconsiderations(*, runtime_root=None) -> dict[str, Any]:
    rows = [_public(row, kind="reconsideration") for row in _rows(_reconsideration_root(runtime_root), _validate_reconsideration)][-MAX_RECONSIDERATIONS:]
    result = {"ok": True, "status": "execution_outcome_lesson_reconsideration_list_ready", "reconsideration_count": len(rows), "reconsiderations": rows, **_base()}
    result["public_execution_outcome_lesson_reconsideration_list_digest"] = _digest(result)
    return result


def execution_outcome_reflection_response(row: Mapping[str, Any]) -> str:
    if row.get("ok") is not True:
        return f"Execution outcome reflection was blocked: {row.get('reason', row.get('status') or 'invalid evidence')}."
    status = str(row.get("status") or "")
    if status == "execution_outcome_ready_for_reflection":
        return f"Execution outcome {row.get('outcome_id')} is sealed as {row.get('outcome_type')} and ready for bounded reflection. No learning or execution authority was granted."
    if status == "execution_outcome_reflection_ready_for_review":
        return f"Reflection {row.get('reflection_id')} prepared project-scoped candidate lessons for operator review. Cognition was not modified."
    if status == "execution_outcome_reflection_deliberate_silence":
        return f"Reflection {row.get('reflection_id')} found no supported durable lesson and recorded deliberate silence."
    if status.startswith("execution_outcome_lesson_reconsideration_"):
        return f"Lesson reconsideration {row.get('reconsideration_id')} recorded decision {row.get('decision')}. Any revision or reopening still requires operator review."
    if status.startswith("execution_outcome_lesson_"):
        return f"Lesson review {row.get('review_id')} recorded disposition {row.get('disposition')}. No project, schedule, launch, provider, command, test, or cognition action occurred."
    if status.endswith("_list_ready"):
        count = row.get("outcome_count", row.get("reflection_count", row.get("review_count", row.get("reconsideration_count", 0))))
        return f"There are {count} execution outcome reflection records."
    return f"Execution outcome reflection recorded: {status}."


def process_execution_outcome_reflection_learning_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    prepare = _PREPARE_OUTCOME.fullmatch(text)
    reflection = _PREPARE_REFLECTION.fullmatch(text)
    review = _REVIEW.fullmatch(text)
    revise = _REVISE.fullmatch(text)
    reconsider = _RECONSIDER.fullmatch(text)
    if prepare:
        result = _public(prepare_execution_outcome(
            prepare.group("launch").lower(),
            outcome_type=prepare.group("kind").lower(),
            expected_launch_digest=prepare.group("launch_digest").lower(),
            expected_monitor_digest=prepare.group("monitor_digest").lower(),
            expected_control_digest=prepare.group("control_digest").lower(),
            runtime_root=runtime_root,
        ), kind="outcome")
    elif _SHOW_OUTCOMES.fullmatch(text):
        result = public_execution_outcomes(runtime_root=runtime_root)
    elif reflection:
        result = _public(prepare_execution_outcome_reflection(
            reflection.group("outcome").lower(), expected_outcome_digest=reflection.group("digest").lower(), runtime_root=runtime_root
        ), kind="reflection")
    elif _SHOW_REFLECTIONS.fullmatch(text):
        result = public_execution_outcome_reflections(runtime_root=runtime_root)
    elif review:
        result = _public(review_execution_outcome_lesson(
            review.group("reflection").lower(), expected_reflection_digest=review.group("digest").lower(),
            disposition=review.group("decision").lower(), runtime_root=runtime_root
        ), kind="review")
    elif revise:
        codes = [part.strip() for part in revise.group("codes").replace("-", "_").split(",")]
        result = _public(review_execution_outcome_lesson(
            revise.group("reflection").lower(), expected_reflection_digest=revise.group("digest").lower(),
            disposition="revise", revised_lesson_codes=codes, runtime_root=runtime_root
        ), kind="review")
    elif _SHOW_REVIEWS.fullmatch(text):
        result = public_execution_outcome_lesson_reviews(runtime_root=runtime_root)
    elif reconsider:
        result = _public(reconsider_execution_outcome_lesson(
            reconsider.group("review").lower(), expected_review_digest=reconsider.group("review_digest").lower(),
            later_outcome_id=reconsider.group("outcome").lower(), expected_later_outcome_digest=reconsider.group("outcome_digest").lower(),
            decision=reconsider.group("decision").lower(), runtime_root=runtime_root,
        ), kind="reconsideration")
    elif _SHOW_RECONSIDERATIONS.fullmatch(text):
        result = public_execution_outcome_lesson_reconsiderations(runtime_root=runtime_root)
    else:
        return {"active": False}
    return {"active": True, "response": execution_outcome_reflection_response(result), "execution_outcome_reflection_learning": result}
