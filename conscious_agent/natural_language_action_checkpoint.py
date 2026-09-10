from __future__ import annotations

"""Strictly read-only v1179.9 natural-language action checkpoint.

Consolidates the retained v1175-v1179 action lifecycle through bounded action
history review, exact status references, content-free follow-up continuity, and
complete-loop reliability. The checkpoint accepts only synthetic caller-owned
records and temporary continuity state. It does not discover private ledgers,
invoke execution, retry work, grant authority, contact providers, or mutate the
source or production runtime.
"""

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from action_follow_up_continuity import CONTRACT_VERSION as FOLLOW_UP_CONTRACT_VERSION, MAX_AGE_SECONDS, MAX_RECORDS as MAX_FOLLOW_UP_RECORDS, inspect_action_follow_up_continuity, register_action_follow_up, resume_action_follow_up, transition_action_follow_up
from action_history_review import CONTRACT_VERSION as HISTORY_CONTRACT_VERSION, MAX_HISTORY_RECORDS, MAX_REVIEW_BYTES, action_history_review_prompt, build_action_history_review
from action_loop_reliability import CONTRACT_VERSION as RELIABILITY_CONTRACT_VERSION, MAX_INPUT_RECORDS, MAX_PUBLIC_RECORDS, MAX_REPORT_BYTES, STALE_IN_PROGRESS_SECONDS, build_action_loop_reliability
from checkpoint_registry import inspect_checkpoint_registry
from natural_language_action_authoritative_result_checkpoint import build_natural_language_action_authoritative_result_checkpoint
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1179.9"
_CHECKPOINT_ID = "natural-language-action:v1179.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_REPORT_TEXT = (
    "ACTION_CHECKPOINT_PRIVATE_REQUEST",
    "ACTION_CHECKPOINT_PRIVATE_OUTPUT",
    "ACTION_CHECKPOINT_PRIVATE_MEMORY",
    "raw_tool_arguments",
    "chain_of_thought",
    "private reasoning payload",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        h.update(relative.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def _record(
    proposal_id: str,
    state: str,
    *,
    updated_at: float,
    proposal_digest: str = "a" * 64,
    capability_id: str = "diagnostics",
    terminal_digest: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "proposal_id": proposal_id,
        "capability_id": capability_id,
        "state": state,
        "proposal_digest": proposal_digest,
        "updated_at": updated_at,
        "content_free": True,
    }
    if state in {
        "approved", "execution_admitted", "execution_in_progress", "execution_succeeded",
        "execution_failed", "execution_cancelled", "execution_timed_out",
    }:
        row["approval_decision_digest"] = "b" * 64
    if state in {
        "execution_admitted", "execution_in_progress", "execution_succeeded",
        "execution_failed", "execution_cancelled", "execution_timed_out",
    }:
        row["authorization_digest"] = "c" * 64
        row["execution_admission_digest"] = "d" * 64
    if state == "execution_in_progress":
        row["execution_attempt_digest"] = "9" * 64
    if state in {
        "execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out",
    }:
        row["terminal_result_digest"] = terminal_digest or "e" * 64
    return row


def _source_contract(source: Path) -> dict[str, Any]:
    files = {
        "history": source / "conscious_agent" / "action_history_review.py",
        "follow_up": source / "conscious_agent" / "action_follow_up_continuity.py",
        "reliability": source / "conscious_agent" / "action_loop_reliability.py",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    return {
        "history_contract": HISTORY_CONTRACT_VERSION,
        "follow_up_contract": FOLLOW_UP_CONTRACT_VERSION,
        "reliability_contract": RELIABILITY_CONTRACT_VERSION,
        "maximum_history_records": MAX_HISTORY_RECORDS,
        "maximum_follow_up_records": MAX_FOLLOW_UP_RECORDS,
        "maximum_input_records": MAX_INPUT_RECORDS,
        "maximum_public_records": MAX_PUBLIC_RECORDS,
        "maximum_review_bytes": MAX_REVIEW_BYTES,
        "maximum_report_bytes": MAX_REPORT_BYTES,
        "follow_up_max_age_seconds": MAX_AGE_SECONDS,
        "stale_in_progress_seconds": STALE_IN_PROGRESS_SECONDS,
        "history_ledger_access_present": any(token in texts["history"] for token in ("Path(", "open(", "read_text(")),
        "reliability_ledger_access_present": any(token in texts["reliability"] for token in ("Path(", "open(", "read_text(")),
        "history_execution_import_present": "execute_admitted_action" in texts["history"],
        "follow_up_execution_import_present": "execute_admitted_action" in texts["follow_up"],
        "reliability_execution_import_present": "execute_admitted_action" in texts["reliability"],
    }


def build_natural_language_action_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    prior = build_natural_language_action_authoritative_result_checkpoint(
        source_root=source, runtime_root=runtime,
    )
    for key in (
        "ok", "read_only", "content_free", "authority_preserved",
        "natural_language_action_authoritative_result_checkpoint_completed",
        "intent_through_authoritative_result_consolidated",
        "synthetic_terminal_lifecycle_exercised",
        "stale_attempt_recovery_exercised_without_reexecution",
        "conversation_result_presentation_parity_preserved",
    ):
        require(prior.get(key))
    for key in (
        "source_modified", "runtime_mutated", "registered_tool_invoked",
        "provider_contacted", "conversation_action_executed", "source_edit_performed",
        "installation_performed", "promotion_performed", "certification_performed",
    ):
        require(prior.get(key) is False)

    states = (
        "proposed", "awaiting_approval", "approved", "rejected", "cancelled", "expired",
        "superseded", "execution_admitted", "execution_in_progress", "execution_succeeded",
        "execution_failed", "execution_cancelled", "execution_timed_out",
    )
    records = [_record(f"action_{index:02d}", state, updated_at=float(index + 1)) for index, state in enumerate(states)]
    history = build_action_history_review(records)
    require(history.get("review_status") == "history")
    require(history.get("record_count") == len(states))
    require(history.get("content_free"))
    require(history.get("ledger_discovered") is False)
    require(history.get("execution_invoked") is False)
    require(history.get("authority_granted") is False)
    require(len(str(history.get("review_digest") or "")) == 64)
    require(len(json.dumps(history, sort_keys=True, separators=(",", ":")).encode()) <= MAX_REVIEW_BYTES)

    state_reviews: dict[str, dict[str, Any]] = {}
    for index, state in enumerate(states):
        proposal_id = f"action_{index:02d}"
        review = build_action_history_review(records, status_reference=f"status action {proposal_id}")
        state_reviews[state] = review
        require(review.get("exact_status_reference"))
        require((review.get("selected_status") or {}).get("state") == state)
        require((review.get("selected_status") or {}).get("proposal_id") == proposal_id)
        require((review.get("follow_through") or {}).get("automatic_retry") is False)
        require((review.get("follow_through") or {}).get("automatic_approval") is False)
        require((review.get("follow_through") or {}).get("automatic_authorization") is False)
        require((review.get("follow_through") or {}).get("execution_invoked") is False)

    invalid_reference = build_action_history_review(records, status_reference="status action missing")
    require(invalid_reference.get("review_status") == "invalid_reference")
    require(invalid_reference.get("selected_status") is None)
    require(build_action_history_review([{"bad": "row"}]).get("record_count") == 0)
    require(build_action_history_review([dict(records[0], content_free=False)]).get("record_count") == 0)
    require("Do not claim retry" in action_history_review_prompt(state_reviews["execution_failed"]))

    continuity_evidence: dict[str, Any] = {}
    with TemporaryDirectory() as directory:
        continuity_path = Path(directory) / "followups.json"
        failure_review = state_reviews["execution_failed"]
        failure_selected = dict(failure_review.get("selected_status") or {})
        registered = register_action_follow_up(continuity_path, failure_review, now=100.0)
        require(registered.get("ok"))
        require(registered.get("persisted"))
        require(registered.get("state") == "pending")
        require(registered.get("authority_granted") is False)
        require(registered.get("execution_invoked") is False)
        raw_state = continuity_path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_REPORT_TEXT:
            require(forbidden not in raw_state)
        duplicate = register_action_follow_up(continuity_path, failure_review, now=101.0)
        require(duplicate.get("state") == "duplicate_pending")
        require(duplicate.get("persisted") is False)
        resumed = resume_action_follow_up(
            continuity_path,
            proposal_id=str(failure_selected.get("proposal_id") or ""),
            review_digest=str(failure_review.get("review_digest") or ""),
            proposal_digest=str(failure_selected.get("proposal_digest") or ""),
            now=102.0,
        )
        require(resumed.get("ok"))
        require(resumed.get("resumable"))
        require(resumed.get("exact_digest_binding"))
        require(resumed.get("next_governed_step") == "review_failure_before_new_governed_operation")
        require(resumed.get("authority_granted") is False)
        require(resumed.get("execution_invoked") is False)
        wrong_review = resume_action_follow_up(
            continuity_path,
            proposal_id=str(failure_selected.get("proposal_id") or ""),
            review_digest="f" * 64,
            proposal_digest=str(failure_selected.get("proposal_digest") or ""),
            now=102.0,
        )
        require(wrong_review.get("resumable") is False)
        closed = transition_action_follow_up(
            continuity_path,
            proposal_id=str(failure_selected.get("proposal_id") or ""),
            transition="closed",
            now=103.0,
        )
        require(closed.get("ok"))
        require(closed.get("state") == "closed")
        require(transition_action_follow_up(
            continuity_path,
            proposal_id=str(failure_selected.get("proposal_id") or ""),
            transition="closed",
            now=104.0,
        ).get("duplicate_terminal_transition"))
        inspection = inspect_action_follow_up_continuity(continuity_path, now=104.0)
        require(inspection.get("record_count") == 1)
        require((inspection.get("state_counts") or {}).get("closed") == 1)
        require(inspection.get("raw_content_exposed") is False)
        require(inspection.get("ledger_discovered") is False)
        require(inspection.get("authority_granted") is False)
        require(inspection.get("execution_invoked") is False)
        continuity_evidence = {
            "registered_state": registered.get("state"),
            "duplicate_state": duplicate.get("state"),
            "resume_state": resumed.get("state"),
            "closed_state": closed.get("state"),
            "inspection_digest": inspection.get("inspection_digest"),
        }

    reliable = build_action_loop_reliability([_record("reliable", "execution_succeeded", updated_at=100.0)], now=101.0)
    require(reliable.get("reliability_posture") == "reliable")
    require(reliable.get("proposal_count") == 1)
    require(reliable.get("raw_content_exposed") is False)
    require(reliable.get("ledger_discovered") is False)
    require(reliable.get("automatic_retry") is False)
    require(reliable.get("automatic_approval") is False)
    require(reliable.get("automatic_authorization") is False)
    require(reliable.get("execution_invoked") is False)

    replay_row = _record("replay", "execution_succeeded", updated_at=100.0)
    replay = build_action_loop_reliability([replay_row, dict(replay_row, updated_at=101.0)], now=102.0)
    require(replay.get("replay_duplicate_count") == 1)
    require(replay.get("reliability_posture") == "review_required")
    contradiction = build_action_loop_reliability([
        _record("conflict", "execution_succeeded", updated_at=100.0, terminal_digest="e" * 64),
        _record("conflict", "execution_failed", updated_at=101.0, terminal_digest="f" * 64),
    ], now=102.0)
    require(contradiction.get("contradictory_proposal_count") == 1)
    require(contradiction.get("reliability_posture") == "blocked")
    incoherent_row = _record("incoherent", "execution_succeeded", updated_at=100.0)
    incoherent_row["authorization_digest"] = ""
    incoherent = build_action_loop_reliability([incoherent_row], now=101.0)
    require(incoherent.get("incoherent_proposal_count") == 1)
    require(incoherent.get("reliability_posture") == "blocked")
    stale = build_action_loop_reliability([
        _record("stale", "execution_in_progress", updated_at=0.0),
    ], now=float(STALE_IN_PROGRESS_SECONDS + 1))
    require(stale.get("stale_in_progress_count") == 1)
    require(stale.get("reliability_posture") == "review_required")
    stale_follow_up = build_action_loop_reliability(
        [_record("followup", "execution_failed", updated_at=10.0)],
        follow_up_records=[{
            "proposal_id": "followup", "review_digest": "7" * 64,
            "state": "pending", "expires_at": 10.0,
        }],
        now=11.0,
    )
    require(stale_follow_up.get("pending_follow_up_count") == 1)
    require(stale_follow_up.get("stale_follow_up_count") == 1)
    require(stale_follow_up.get("reliability_posture") == "review_required")
    malformed = build_action_loop_reliability([{"bad": "row"}, dict(records[0], content_free=False)], now=1.0)
    require(malformed.get("malformed_record_count") == 2)
    require(malformed.get("accepted_record_count") == 0)
    many = [_record(f"long_{index}", "execution_succeeded", updated_at=float(index)) for index in range(MAX_INPUT_RECORDS + 100)]
    bounded = build_action_loop_reliability(many, now=1000.0)
    require(bounded.get("input_record_count") == MAX_INPUT_RECORDS)
    require(bounded.get("public_record_count") == MAX_PUBLIC_RECORDS)
    require(bounded.get("input_truncated"))
    require(len(json.dumps(bounded, sort_keys=True, separators=(",", ":")).encode()) <= MAX_REPORT_BYTES)

    source_contract = _source_contract(source)
    require(source_contract["history_contract"] == "v1179.2")
    require(source_contract["follow_up_contract"] == "v1179.5")
    require(source_contract["reliability_contract"] == "v1179.8")
    require(source_contract["maximum_history_records"] == 32)
    require(source_contract["maximum_follow_up_records"] == 32)
    require(source_contract["maximum_input_records"] == 512)
    require(source_contract["maximum_public_records"] == 64)
    require(source_contract["follow_up_max_age_seconds"] == 7 * 86400)
    require(source_contract["stale_in_progress_seconds"] == 300)
    require(source_contract["history_ledger_access_present"] is False)
    require(source_contract["reliability_ledger_access_present"] is False)
    require(source_contract["history_execution_import_present"] is False)
    require(source_contract["follow_up_execution_import_present"] is False)
    require(source_contract["reliability_execution_import_present"] is False)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next((
        row for row in registry.get("checkpoints", [])
        if row.get("checkpoint_id") == "natural-language-action-checkpoint"
    ), None)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_natural_language_action_checkpoint")
    require((checkpoint_row or {}).get("contract_version") == CONTRACT_VERSION)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok"))
    require(privacy.get("source_only"))
    require(int(privacy.get("forbidden_count", privacy.get("forbidden_entry_count", 0)) or 0) == 0)
    require(int(privacy.get("private_content_finding_count", 0) or 0) == 0)

    evidence = {
        "retained_authoritative_result_checkpoint": {
            "contract_version": prior.get("contract_version"),
            "passed": prior.get("passed"),
            "total": prior.get("total"),
            "structural_digest": prior.get("structural_digest"),
        },
        "history": {
            "record_count": history.get("record_count"),
            "review_digest": history.get("review_digest"),
            "state_count": len(states),
        },
        "continuity": continuity_evidence,
        "reliability": {
            "reliable_digest": reliable.get("reliability_digest"),
            "replay_digest": replay.get("reliability_digest"),
            "contradiction_digest": contradiction.get("reliability_digest"),
            "stale_digest": stale.get("reliability_digest"),
            "bounded_digest": bounded.get("reliability_digest"),
        },
        "source_contract": source_contract,
        "privacy": {
            "entry_count": privacy.get("entry_count"),
            "forbidden_entry_count": privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)),
            "private_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
    }
    forbidden_count = sum(
        1 for value in _FORBIDDEN_REPORT_TEXT
        if value in json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    )
    require(forbidden_count == 0)

    source_modified = source_before != _tree_signature(source)
    runtime_mutated = runtime_before != _tree_signature(runtime)
    require(source_modified is False)
    require(runtime_mutated is False)

    report: dict[str, Any] = {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "status": "ready" if all(checks) else "review_required",
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "natural_language_action_checkpoint_completed": True,
        "intent_through_follow_through_consolidated": True,
        "action_history_review_exercised": True,
        "exact_status_reference_exercised": True,
        "follow_up_restart_continuity_exercised": True,
        "complete_action_loop_reliability_exercised": True,
        "long_session_bounding_exercised": True,
        "raw_request_persisted": False,
        "raw_argument_values_persisted": False,
        "raw_operation_identity_persisted": False,
        "raw_output_persisted": False,
        "private_ledger_discovered": False,
        "automatic_retry_performed": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "execution_admitted": False,
        "execution_invoked": False,
        "registered_tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "source_edit_performed": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "source_modified": source_modified,
        "runtime_mutated": runtime_mutated,
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "retained_checkpoint_count": 1,
            "lifecycle_state_case_count": len(states),
            "exact_status_case_count": len(states),
            "follow_up_continuity_case_count": 9,
            "reliability_case_count": 8,
            "long_session_input_limit": MAX_INPUT_RECORDS,
            "long_session_public_limit": MAX_PUBLIC_RECORDS,
            "history_record_limit": MAX_HISTORY_RECORDS,
            "follow_up_record_limit": MAX_FOLLOW_UP_RECORDS,
            "follow_up_max_age_seconds": MAX_AGE_SECONDS,
            "stale_in_progress_seconds": STALE_IN_PROGRESS_SECONDS,
            "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0),
            "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0) or 0),
            "open_limitation_count": 4,
        },
        "evidence": evidence,
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
