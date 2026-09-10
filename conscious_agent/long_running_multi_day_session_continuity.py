from __future__ import annotations

"""v1244 long-running and multi-day session continuity.

The module records content-free progress checkpoints, durable continuity
manifests, next-day reconciliation assessments, and exact operator reviews.
It never resumes execution, reuses an authorization, renews a resource claim,
contacts a provider, invokes a tool, or mutates a project.
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
CONTRACT_VERSION = "v1244.8"
MILESTONE_NAME = "Long-Running and Multi-Day Session Continuity"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"
MAX_RECORDS = 400

SESSION_STATES = {"active", "paused", "recovery_required", "cancelled", "completed", "failed"}
STOP_REASONS = {
    "end_of_day", "operator_absence", "planned_pause", "provider_outage",
    "tool_unavailable", "dependency_blocked", "resource_blocked",
    "machine_shutdown", "crash_recovery", "manual_handoff", "unknown",
}
PROGRESS_STATES = {"in_progress", "awaiting_review", "blocked", "paused", "completed", "failed"}
ASSESSMENT_STATES = {
    "eligible_for_resume_proposal", "revalidation_required", "plan_revision_required",
    "workspace_recovery_required", "manual_reconciliation_required", "terminal",
}
REVIEW_DISPOSITIONS = {"accept_resume_proposal", "hold", "reject", "request_changes"}
FRESHNESS_SCOPES = (
    "project", "plan", "dependencies", "resources", "provider", "tools",
    "workspace", "environment", "quality", "authorization",
)
DEFAULT_FRESHNESS_WINDOWS = {
    "project": 1, "plan": 7, "dependencies": 1, "resources": 1, "provider": 1,
    "tools": 1, "workspace": 1, "environment": 1, "quality": 7, "authorization": 0,
}

AUTHORITY_FLAGS = {
    "continuity_inspection_authorized": True,
    "progress_checkpoint_preparation_authorized": True,
    "continuity_manifest_preparation_authorized": True,
    "continuity_reconciliation_preparation_authorized": True,
    "continuity_review_authorized": True,
    "resume_proposal_preparation_authorized": True,
    "resume_authorized": False,
    "session_launch_authorized": False,
    "session_pause_authorized": False,
    "session_cancel_authorized": False,
    "provider_contact_authorized": False,
    "provider_execution_authorized": False,
    "prompt_transmission_authorized": False,
    "provider_switch_authorized": False,
    "tool_invocation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "resource_claim_renewal_authorized": False,
    "dependency_state_mutation_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "plan_revision_authorized": False,
    "cognition_write_authorized": False,
    "automatic_retry_authorized": False,
    "automatic_resume_authorized": False,
    "background_execution_authorized": False,
    "approval_creation_authorized": False,
    "approval_consumption_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

_TOKEN = re.compile(r"^[a-z][a-z0-9_\-]{1,80}$")
_PROJECT = re.compile(r"^project_[a-z0-9_\-]{2,64}$")
_SESSION = re.compile(r"^(?:session|launch|execution_session|prepared_session)_[a-z0-9_\-]{2,80}$")
_PROGRESS = re.compile(r"^continuity_progress_[a-f0-9]{24}$")
_MANIFEST = re.compile(r"^continuity_manifest_[a-f0-9]{24}$")
_ASSESSMENT = re.compile(r"^continuity_assessment_[a-f0-9]{24}$")
_REVIEW = re.compile(r"^continuity_review_[a-f0-9]{24}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_PRIVATE = ("path", "secret", "password", "token", "credential", "prompt", "content", "endpoint", "url", "private", "username", "email")

_SHOW_REGISTRY = re.compile(r"^show long running session continuity registry[.!?]*$", re.I)
_SHOW_PROGRESS = re.compile(r"^show session continuity progress checkpoints[.!?]*$", re.I)
_SHOW_MANIFESTS = re.compile(r"^show session continuity manifests[.!?]*$", re.I)
_SHOW_ASSESSMENTS = re.compile(r"^show session continuity assessments[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show session continuity reviews[.!?]*$", re.I)
_REVIEW_ASSESSMENT = re.compile(
    r"^review session continuity (?P<decision>accept_resume_proposal|hold|reject|request_changes) "
    r"for assessment (?P<assessment>continuity_assessment_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _dir(name: str, runtime_root=None) -> Path:
    return _root(runtime_root) / name


def _path(name: str, record_id: str, runtime_root=None) -> Path:
    return _dir(name, runtime_root) / f"{str(record_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "long-running-multi-day-session-continuity.lock"
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
                raise TimeoutError("Timed out waiting for continuity lock")
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


def _token(value: Any, reason: str, *, pattern: re.Pattern[str] = _TOKEN) -> str:
    text = str(value or "").lower().strip()
    if not pattern.fullmatch(text) or any(part in text for part in _PRIVATE):
        raise ValueError(reason)
    return text


def _tokens(values: Iterable[Any], reason: str) -> list[str]:
    rows = sorted({str(value or "").lower().strip() for value in values or []})
    if any(not _TOKEN.fullmatch(row) or any(part in row for part in _PRIVATE) for row in rows):
        raise ValueError(reason)
    return rows


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "runtime_records_external": True,
        "project_scoped": True,
        "historical_records_immutable": True,
        "exact_lineage_required": True,
        "fresh_revalidation_required": True,
        "fresh_separate_resume_authority_required": True,
        "fresh_separate_provider_authority_required": True,
        "fresh_separate_tool_authority_required": True,
        "yesterdays_authority_never_reused": True,
        "progress_preserved": True,
        "uncertainty_preserved": True,
        "provider_contacted": False,
        "prompt_transmitted": False,
        "tool_invoked": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "resource_claim_renewed": False,
        "project_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "plan_revised": False,
        "session_resumed": False,
        "session_launched": False,
        "automatic_retry_created": False,
        "automatic_resume_created": False,
        "cognition_written": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_tool_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["session_continuity_result_digest"] = _digest(row)
    return row


def long_running_session_continuity_registry() -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "long_running_session_continuity_registry_ready",
        "session_states": sorted(SESSION_STATES),
        "stop_reasons": sorted(STOP_REASONS),
        "progress_states": sorted(PROGRESS_STATES),
        "assessment_states": sorted(ASSESSMENT_STATES),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        "freshness_scopes": list(FRESHNESS_SCOPES),
        "default_freshness_windows_days": dict(DEFAULT_FRESHNESS_WINDOWS),
        "inspection_only": True,
        **_base(),
    }
    row["registry_digest"] = _digest(row)
    return row


def record_session_progress_checkpoint(
    project_id: str,
    session_id: str,
    *,
    session_digest: str,
    checkpoint_index: int,
    logical_day: int,
    progress_state: str,
    stage_code: str,
    completed_evidence_digests: Iterable[str] = (),
    incomplete_work_codes: Iterable[str] = (),
    pending_review_codes: Iterable[str] = (),
    previous_progress_id: str = "",
    previous_progress_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        project = _token(project_id, "invalid_project_id", pattern=_PROJECT)
        session = _token(session_id, "invalid_session_id", pattern=_SESSION)
        sdigest = _hex(session_digest, "invalid_session_digest")
        index = int(checkpoint_index)
        day = int(logical_day)
        if index < 1 or day < 0:
            raise ValueError("invalid_checkpoint_index_or_day")
        state = _token(progress_state, "invalid_progress_state")
        if state not in PROGRESS_STATES:
            raise ValueError("invalid_progress_state")
        stage = _token(stage_code, "invalid_stage_code")
        completed = sorted({_hex(value, "invalid_completed_evidence_digest") for value in completed_evidence_digests or []})
        incomplete = _tokens(incomplete_work_codes, "invalid_incomplete_work_code")
        pending = _tokens(pending_review_codes, "invalid_pending_review_code")
        previous_id = str(previous_progress_id or "").lower().strip()
        previous_digest = str(previous_progress_digest or "").lower().strip()
        if bool(previous_id) != bool(previous_digest):
            raise ValueError("previous_progress_lineage_incomplete")
        if previous_id:
            if not _PROGRESS.fullmatch(previous_id):
                raise ValueError("invalid_previous_progress_id")
            previous = load_session_progress_checkpoint(previous_id, runtime_root=runtime_root)
            if not previous.get("ok") or previous.get("progress_record_digest") != _hex(previous_digest, "invalid_previous_progress_digest"):
                raise ValueError("stale_or_mismatched_previous_progress")
            if previous.get("project_id") != project or previous.get("session_id") != session:
                raise ValueError("cross_session_progress_lineage")
            if int(previous.get("checkpoint_index") or 0) + 1 != index:
                raise ValueError("nonsequential_progress_checkpoint")
        elif index != 1:
            raise ValueError("first_progress_checkpoint_must_be_one")
        identity = {
            "project_id": project, "session_id": session, "session_digest": sdigest,
            "checkpoint_index": index, "logical_day": day, "progress_state": state,
            "stage_code": stage, "completed_evidence_digests": completed,
            "incomplete_work_codes": incomplete, "pending_review_codes": pending,
            "previous_progress_id": previous_id, "previous_progress_digest": previous_digest,
        }
        record_id = "continuity_progress_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True, "status": "session_progress_checkpoint_recorded",
            "progress_id": record_id, **identity,
            "completed_evidence_count": len(completed),
            "incomplete_work_count": len(incomplete),
            "pending_review_count": len(pending),
            **_base(),
        }, "progress_record_digest")
        with _lock(runtime_root):
            path = _path("session_continuity_progress", record_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "progress_record_digest") else _failure("session_progress_checkpoint_tampered", "existing_progress_record_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("session_progress_checkpoint_blocked", str(exc))


def load_session_progress_checkpoint(progress_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(progress_id or "").lower().strip()
    if not _PROGRESS.fullmatch(token):
        return _failure("session_progress_checkpoint_not_found", "invalid_progress_id")
    row = _read_json(_path("session_continuity_progress", token, runtime_root))
    if not row:
        return _failure("session_progress_checkpoint_not_found", "progress_record_missing")
    return row if _valid(row, "progress_record_digest") else _failure("session_progress_checkpoint_tampered", "progress_record_digest_mismatch")


def _normalize_evidence(evidence: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(evidence, Mapping):
        raise ValueError("continuity_evidence_mapping_required")
    rows: dict[str, str] = {}
    for scope in FRESHNESS_SCOPES:
        value = evidence.get(scope, "")
        rows[scope] = _hex(value, f"invalid_{scope}_evidence_digest", allow_empty=(scope != "project"))
    return rows


def _normalize_windows(values: Mapping[str, Any] | None) -> dict[str, int]:
    source = dict(DEFAULT_FRESHNESS_WINDOWS)
    if values:
        for key, value in values.items():
            scope = str(key or "").lower().strip()
            if scope not in FRESHNESS_SCOPES:
                raise ValueError("unknown_freshness_scope")
            number = int(value)
            if number < 0 or number > 365:
                raise ValueError("invalid_freshness_window")
            source[scope] = number
    source["authorization"] = 0
    return {scope: source[scope] for scope in FRESHNESS_SCOPES}


def prepare_session_continuity_manifest(
    project_id: str,
    session_id: str,
    *,
    session_digest: str,
    session_state: str,
    stop_reason: str,
    logical_day: int,
    continuity_generation: int,
    latest_progress_id: str,
    expected_progress_digest: str,
    evidence_digests: Mapping[str, Any],
    freshness_windows_days: Mapping[str, Any] | None = None,
    completed_work_codes: Iterable[str] = (),
    remaining_work_codes: Iterable[str] = (),
    changed_assumption_codes: Iterable[str] = (),
    uncertainty_codes: Iterable[str] = (),
    previous_manifest_id: str = "",
    previous_manifest_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        project = _token(project_id, "invalid_project_id", pattern=_PROJECT)
        session = _token(session_id, "invalid_session_id", pattern=_SESSION)
        sdigest = _hex(session_digest, "invalid_session_digest")
        state = _token(session_state, "invalid_session_state")
        if state not in SESSION_STATES:
            raise ValueError("invalid_session_state")
        reason = _token(stop_reason, "invalid_stop_reason")
        if reason not in STOP_REASONS:
            raise ValueError("invalid_stop_reason")
        day = int(logical_day); generation = int(continuity_generation)
        if day < 0 or generation < 1:
            raise ValueError("invalid_logical_day_or_generation")
        previous_id = str(previous_manifest_id or "").lower().strip()
        previous_digest = str(previous_manifest_digest or "").lower().strip()
        if bool(previous_id) != bool(previous_digest):
            raise ValueError("previous_manifest_lineage_incomplete")
        if generation == 1 and previous_id:
            raise ValueError("first_manifest_cannot_have_previous_manifest")
        if generation > 1:
            if not previous_id or not _MANIFEST.fullmatch(previous_id):
                raise ValueError("previous_manifest_required")
            previous = load_session_continuity_manifest(previous_id, runtime_root=runtime_root)
            if not previous.get("ok") or previous.get("continuity_manifest_record_digest") != _hex(previous_digest, "invalid_previous_manifest_digest"):
                raise ValueError("stale_or_mismatched_previous_manifest")
            if previous.get("project_id") != project or previous.get("session_id") != session:
                raise ValueError("cross_session_manifest_lineage")
            if int(previous.get("continuity_generation") or 0) + 1 != generation:
                raise ValueError("nonsequential_continuity_generation")
            if int(previous.get("logical_day") or 0) > day:
                raise ValueError("manifest_generation_clock_reversal")
        progress_id = str(latest_progress_id or "").lower().strip()
        if not _PROGRESS.fullmatch(progress_id):
            raise ValueError("invalid_progress_id")
        progress = load_session_progress_checkpoint(progress_id, runtime_root=runtime_root)
        pdigest = _hex(expected_progress_digest, "invalid_progress_digest")
        if not progress.get("ok") or progress.get("progress_record_digest") != pdigest:
            raise ValueError("stale_or_mismatched_progress_digest")
        if progress.get("project_id") != project or progress.get("session_id") != session or progress.get("session_digest") != sdigest:
            raise ValueError("cross_session_progress_lineage")
        if int(progress.get("logical_day") or 0) > day:
            raise ValueError("manifest_before_progress_day")
        evidence = _normalize_evidence(evidence_digests)
        windows = _normalize_windows(freshness_windows_days)
        completed = _tokens(completed_work_codes, "invalid_completed_work_code")
        remaining = _tokens(remaining_work_codes, "invalid_remaining_work_code")
        changed = _tokens(changed_assumption_codes, "invalid_changed_assumption_code")
        uncertainty = _tokens(uncertainty_codes, "invalid_uncertainty_code")
        identity = {
            "project_id": project, "session_id": session, "session_digest": sdigest,
            "session_state": state, "stop_reason": reason, "logical_day": day,
            "continuity_generation": generation, "latest_progress_id": progress_id,
            "latest_progress_digest": pdigest, "evidence_digests": evidence,
            "freshness_windows_days": windows, "completed_work_codes": completed,
            "remaining_work_codes": remaining, "changed_assumption_codes": changed,
            "uncertainty_codes": uncertainty,
            "previous_manifest_id": previous_id, "previous_manifest_digest": previous_digest,
        }
        manifest_id = "continuity_manifest_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True, "status": "session_continuity_manifest_prepared",
            "manifest_id": manifest_id, **identity,
            "completed_work_count": len(completed), "remaining_work_count": len(remaining),
            "changed_assumption_count": len(changed), "uncertainty_count": len(uncertainty),
            "resume_eligibility_not_evaluated": True,
            **_base(),
        }, "continuity_manifest_record_digest")
        with _lock(runtime_root):
            path = _path("session_continuity_manifests", manifest_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "continuity_manifest_record_digest") else _failure("session_continuity_manifest_tampered", "existing_manifest_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("session_continuity_manifest_blocked", str(exc))


def load_session_continuity_manifest(manifest_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(manifest_id or "").lower().strip()
    if not _MANIFEST.fullmatch(token):
        return _failure("session_continuity_manifest_not_found", "invalid_manifest_id")
    row = _read_json(_path("session_continuity_manifests", token, runtime_root))
    if not row:
        return _failure("session_continuity_manifest_not_found", "manifest_missing")
    return row if _valid(row, "continuity_manifest_record_digest") else _failure("session_continuity_manifest_tampered", "manifest_digest_mismatch")


def prepare_session_continuity_reconciliation(
    manifest_id: str,
    *,
    expected_manifest_digest: str,
    current_logical_day: int,
    current_session_state: str,
    current_session_digest: str,
    current_evidence_digests: Mapping[str, Any],
    available_scope_codes: Iterable[str] = (),
    contradiction_codes: Iterable[str] = (),
    runtime_root=None,
) -> dict[str, Any]:
    try:
        token = str(manifest_id or "").lower().strip()
        if not _MANIFEST.fullmatch(token):
            raise ValueError("invalid_manifest_id")
        manifest = load_session_continuity_manifest(token, runtime_root=runtime_root)
        mdigest = _hex(expected_manifest_digest, "invalid_manifest_digest")
        if not manifest.get("ok") or manifest.get("continuity_manifest_record_digest") != mdigest:
            raise ValueError("stale_or_mismatched_manifest_digest")
        day = int(current_logical_day)
        if day < int(manifest.get("logical_day") or 0):
            raise ValueError("clock_moved_before_manifest")
        state = _token(current_session_state, "invalid_session_state")
        if state not in SESSION_STATES:
            raise ValueError("invalid_session_state")
        sdigest = _hex(current_session_digest, "invalid_session_digest")
        current = _normalize_evidence(current_evidence_digests)
        available = set(_tokens(available_scope_codes, "invalid_available_scope_code"))
        if not available:
            available = {scope for scope, value in current.items() if value}
        if not available.issubset(set(FRESHNESS_SCOPES)):
            raise ValueError("unknown_available_scope")
        contradictions = _tokens(contradiction_codes, "invalid_contradiction_code")
        prior = dict(manifest.get("evidence_digests") or {})
        windows = dict(manifest.get("freshness_windows_days") or DEFAULT_FRESHNESS_WINDOWS)
        age = day - int(manifest.get("logical_day") or 0)
        stale_scopes: list[str] = []
        changed_scopes: list[str] = []
        missing_scopes: list[str] = []
        revalidated_scopes: list[str] = []
        for scope in FRESHNESS_SCOPES:
            old = str(prior.get(scope) or "")
            new = str(current.get(scope) or "")
            if scope not in available or not new:
                missing_scopes.append(scope)
            elif old and new != old:
                changed_scopes.append(scope)
            elif age > int(windows.get(scope, 0)):
                stale_scopes.append(scope)
            else:
                revalidated_scopes.append(scope)
        # Authorizations are deliberately never reusable across continuity boundaries.
        if "authorization" not in stale_scopes:
            stale_scopes.append("authorization")
        if "authorization" in revalidated_scopes:
            revalidated_scopes.remove("authorization")
        session_digest_changed = sdigest != manifest.get("session_digest")
        if session_digest_changed and "session" not in changed_scopes:
            changed_scopes.append("session")
        terminal = state in {"cancelled", "completed", "failed"}
        workspace_missing = "workspace" in missing_scopes
        plan_changed = any(scope in changed_scopes for scope in ("project", "plan", "quality")) or bool(manifest.get("changed_assumption_codes"))
        revalidation_needed = bool(stale_scopes or changed_scopes or missing_scopes or contradictions or session_digest_changed)
        if terminal:
            assessment_state = "terminal"
        elif contradictions:
            assessment_state = "manual_reconciliation_required"
        elif workspace_missing:
            assessment_state = "workspace_recovery_required"
        elif plan_changed:
            assessment_state = "plan_revision_required"
        elif revalidation_needed:
            assessment_state = "revalidation_required"
        else:
            assessment_state = "eligible_for_resume_proposal"
        # Authorization staleness alone is expected and does not block proposal preparation.
        blocking_stale = [scope for scope in stale_scopes if scope != "authorization"]
        resume_proposal_eligible = (
            assessment_state in {"eligible_for_resume_proposal", "revalidation_required"}
            and not blocking_stale and not changed_scopes and not missing_scopes and not contradictions
            and state in {"paused", "recovery_required"}
        )
        if resume_proposal_eligible:
            assessment_state = "eligible_for_resume_proposal"
        identity = {
            "manifest_id": token, "manifest_digest": mdigest,
            "project_id": manifest.get("project_id"), "session_id": manifest.get("session_id"),
            "current_logical_day": day, "elapsed_logical_days": age,
            "current_session_state": state, "current_session_digest": sdigest,
            "current_evidence_digests": current, "available_scope_codes": sorted(available),
            "stale_scopes": sorted(set(stale_scopes)), "changed_scopes": sorted(set(changed_scopes)),
            "missing_scopes": sorted(set(missing_scopes)), "revalidated_scopes": sorted(set(revalidated_scopes)),
            "contradiction_codes": contradictions, "assessment_state": assessment_state,
            "resume_proposal_eligible": resume_proposal_eligible,
        }
        assessment_id = "continuity_assessment_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True, "status": "session_continuity_reconciliation_prepared",
            "assessment_id": assessment_id, **identity,
            "operator_review_required": True,
            "fresh_resume_authorization_required": True,
            "old_authorization_explicitly_nonreusable": True,
            "provider_revalidation_required": "provider" in stale_scopes + changed_scopes + missing_scopes,
            "tool_revalidation_required": "tools" in stale_scopes + changed_scopes + missing_scopes,
            "dependency_revalidation_required": "dependencies" in stale_scopes + changed_scopes + missing_scopes,
            "resource_revalidation_required": "resources" in stale_scopes + changed_scopes + missing_scopes,
            **_base(),
        }, "continuity_assessment_record_digest")
        with _lock(runtime_root):
            path = _path("session_continuity_assessments", assessment_id, runtime_root)
            current_row = _read_json(path)
            if current_row:
                return current_row if _valid(current_row, "continuity_assessment_record_digest") else _failure("session_continuity_assessment_tampered", "existing_assessment_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("session_continuity_reconciliation_blocked", str(exc))


def load_session_continuity_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(assessment_id or "").lower().strip()
    if not _ASSESSMENT.fullmatch(token):
        return _failure("session_continuity_assessment_not_found", "invalid_assessment_id")
    row = _read_json(_path("session_continuity_assessments", token, runtime_root))
    if not row:
        return _failure("session_continuity_assessment_not_found", "assessment_missing")
    return row if _valid(row, "continuity_assessment_record_digest") else _failure("session_continuity_assessment_tampered", "assessment_digest_mismatch")


def review_session_continuity_assessment(
    assessment_id: str,
    *,
    expected_assessment_digest: str,
    disposition: str,
    exact_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        token = str(assessment_id or "").lower().strip()
        if not _ASSESSMENT.fullmatch(token):
            raise ValueError("invalid_assessment_id")
        assessment = load_session_continuity_assessment(token, runtime_root=runtime_root)
        digest = _hex(expected_assessment_digest, "invalid_assessment_digest")
        if not assessment.get("ok") or assessment.get("continuity_assessment_record_digest") != digest:
            raise ValueError("stale_or_mismatched_assessment_digest")
        decision = _token(disposition, "invalid_review_disposition")
        if decision not in REVIEW_DISPOSITIONS:
            raise ValueError("invalid_review_disposition")
        match = _REVIEW_ASSESSMENT.fullmatch(str(exact_phrase or "").strip())
        if not match or match.group("decision").lower() != decision or match.group("assessment").lower() != token or match.group("digest").lower() != digest:
            raise ValueError("exact_review_phrase_required")
        accepted = decision == "accept_resume_proposal" and assessment.get("resume_proposal_eligible") is True
        if decision == "accept_resume_proposal" and not accepted:
            raise ValueError("assessment_not_eligible_for_resume_proposal")
        identity = {
            "assessment_id": token, "assessment_digest": digest,
            "project_id": assessment.get("project_id"), "session_id": assessment.get("session_id"),
            "disposition": decision, "assessment_state": assessment.get("assessment_state"),
            "resume_proposal_interpretation_accepted": accepted,
        }
        review_id = "continuity_review_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True, "status": "session_continuity_review_recorded",
            "review_id": review_id, **identity,
            "operator_follow_up_required": decision in {"hold", "request_changes"},
            "fresh_resume_authority_still_required": True,
            "resume_authority_created": False,
            "provider_authority_created": False,
            "tool_authority_created": False,
            "resource_claim_created": False,
            **_base(),
        }, "continuity_review_record_digest")
        with _lock(runtime_root):
            path = _path("session_continuity_reviews", review_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "continuity_review_record_digest") else _failure("session_continuity_review_tampered", "existing_review_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("session_continuity_review_blocked", str(exc))


def load_session_continuity_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(review_id or "").lower().strip()
    if not _REVIEW.fullmatch(token):
        return _failure("session_continuity_review_not_found", "invalid_review_id")
    row = _read_json(_path("session_continuity_reviews", token, runtime_root))
    if not row:
        return _failure("session_continuity_review_not_found", "review_missing")
    return row if _valid(row, "continuity_review_record_digest") else _failure("session_continuity_review_tampered", "review_digest_mismatch")


def _public_list(directory: str, seal_field: str, keys: Iterable[str], plural: str, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _dir(directory, runtime_root)
    for path in sorted(root.glob("*.json")) if root.exists() else []:
        row = _read_json(path)
        if row and _valid(row, seal_field):
            rows.append({key: row.get(key) for key in keys})
    rows = rows[-MAX_RECORDS:]
    result = {"ok": True, "status": f"{plural}_ready", plural: rows, "count": len(rows), "read_only": True, **_base()}
    result[f"{plural}_digest"] = _digest(rows)
    return result


def public_session_continuity_progress(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("session_continuity_progress", "progress_record_digest", ("progress_id", "project_id", "session_id", "checkpoint_index", "logical_day", "progress_state", "stage_code", "progress_record_digest"), "progress_checkpoints", runtime_root)


def public_session_continuity_manifests(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("session_continuity_manifests", "continuity_manifest_record_digest", ("manifest_id", "project_id", "session_id", "session_state", "stop_reason", "logical_day", "continuity_generation", "remaining_work_count", "continuity_manifest_record_digest"), "continuity_manifests", runtime_root)


def public_session_continuity_assessments(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("session_continuity_assessments", "continuity_assessment_record_digest", ("assessment_id", "manifest_id", "project_id", "session_id", "assessment_state", "resume_proposal_eligible", "stale_scopes", "changed_scopes", "missing_scopes", "continuity_assessment_record_digest"), "continuity_assessments", runtime_root)


def public_session_continuity_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("session_continuity_reviews", "continuity_review_record_digest", ("review_id", "assessment_id", "project_id", "session_id", "disposition", "resume_proposal_interpretation_accepted", "continuity_review_record_digest"), "continuity_reviews", runtime_root)


def session_continuity_dashboard_record(*, runtime_root=None) -> dict[str, Any]:
    progress = public_session_continuity_progress(runtime_root=runtime_root)
    manifests = public_session_continuity_manifests(runtime_root=runtime_root)
    assessments = public_session_continuity_assessments(runtime_root=runtime_root)
    reviews = public_session_continuity_reviews(runtime_root=runtime_root)
    row = {
        "ok": True, "status": "long_running_session_continuity_dashboard_ready",
        "read_only": True, "get_only": True,
        "progress_checkpoint_count": progress["count"],
        "manifest_count": manifests["count"],
        "assessment_count": assessments["count"],
        "review_count": reviews["count"],
        "progress_checkpoints": progress["progress_checkpoints"],
        "continuity_manifests": manifests["continuity_manifests"],
        "continuity_assessments": assessments["continuity_assessments"],
        "continuity_reviews": reviews["continuity_reviews"],
        **_base(),
    }
    row["dashboard_digest"] = _digest({k: v for k, v in row.items() if k != "dashboard_digest"})
    return row


def render_session_continuity_dashboard_html(*, runtime_root=None) -> str:
    row = session_continuity_dashboard_record(runtime_root=runtime_root)
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Long-Running and Multi-Day Session Continuity</title>"
        "<style>body{font-family:system-ui;background:#111827;color:#e5e7eb;margin:0;padding:28px}.card{background:#1f2937;border:1px solid #374151;border-radius:12px;padding:18px;max-width:980px;margin:auto}h1{margin-top:0}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric{background:#111827;padding:14px;border-radius:8px}.muted{color:#9ca3af}</style></head><body><div class='card'>"
        "<h1>Long-Running and Multi-Day Session Continuity</h1><p class='muted'>GET-only inspection. Continuity evidence cannot resume, retry, contact providers, invoke tools, renew resources, or reuse old authority.</p>"
        f"<div class='grid'><div class='metric'>Progress<br><b>{html.escape(str(row['progress_checkpoint_count']))}</b></div>"
        f"<div class='metric'>Manifests<br><b>{html.escape(str(row['manifest_count']))}</b></div>"
        f"<div class='metric'>Assessments<br><b>{html.escape(str(row['assessment_count']))}</b></div>"
        f"<div class='metric'>Reviews<br><b>{html.escape(str(row['review_count']))}</b></div></div>"
        "<p>Every resume requires current project, plan, dependency, resource, provider, tool, workspace, environment, quality, and fresh authorization evidence.</p>"
        "</div></body></html>"
    )


def session_continuity_response(row: Mapping[str, Any]) -> str:
    status = str(row.get("status") or "")
    if not row.get("ok"):
        return f"Session continuity control was blocked: {row.get('reason') or status}. No session resumed and no authority was created."
    if status.endswith("registry_ready"):
        return "The long-running session continuity registry is ready for read-only inspection."
    if status.endswith("review_recorded"):
        return f"Recorded continuity review {row.get('review_id')} as {row.get('disposition')}. No session resumed; fresh exact resume authority is still required."
    return "Session continuity evidence is ready for read-only inspection. No execution or resume authority was created."


def process_session_continuity_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    row: dict[str, Any] | None = None
    if _SHOW_REGISTRY.fullmatch(text):
        row = long_running_session_continuity_registry()
    elif _SHOW_PROGRESS.fullmatch(text):
        row = public_session_continuity_progress(runtime_root=runtime_root)
    elif _SHOW_MANIFESTS.fullmatch(text):
        row = public_session_continuity_manifests(runtime_root=runtime_root)
    elif _SHOW_ASSESSMENTS.fullmatch(text):
        row = public_session_continuity_assessments(runtime_root=runtime_root)
    elif _SHOW_REVIEWS.fullmatch(text):
        row = public_session_continuity_reviews(runtime_root=runtime_root)
    else:
        match = _REVIEW_ASSESSMENT.fullmatch(text)
        if match:
            row = review_session_continuity_assessment(
                match.group("assessment"), expected_assessment_digest=match.group("digest"),
                disposition=match.group("decision").lower(), exact_phrase=text, runtime_root=runtime_root,
            )
    if row is None:
        return {"active": False}
    return {"active": True, "session_continuity": row, "response": session_continuity_response(row), "action_taken": False, "execution_started": False}


def build_long_running_session_continuity_contract() -> dict[str, Any]:
    row = {
        "ok": True, "status": "long_running_multi_day_session_continuity_contract_ready",
        "milestone_name": MILESTONE_NAME, "roadmap_path": ROADMAP_PATH,
        "durable_session_epochs": True,
        "progress_checkpoint_lineage": True,
        "sequential_manifest_generations_required": True,
        "interruption_reasons_preserved": True,
        "freshness_windows_enforced": True,
        "project_plan_dependency_resource_provider_tool_workspace_environment_quality_revalidation": True,
        "clock_drift_fails_closed": True,
        "changed_project_or_plan_requires_revision_review": True,
        "lost_workspace_requires_recovery": True,
        "provider_and_tool_state_revalidated": True,
        "duplicate_restart_and_replay_deterministic": True,
        "cross_project_and_cross_session_confusion_rejected": True,
        "old_authority_never_reused": True,
        "resume_requires_fresh_exact_separate_authority": True,
        "operator_review_is_interpretation_only": True,
        "runtime_records_external": True,
        **_base(),
    }
    row["contract_digest"] = _digest(row)
    return row
