from __future__ import annotations

"""Strictly read-only v1178.9 action and authoritative-result checkpoint.

This checkpoint consolidates the governed natural-language action lifecycle from
intent and clarification through proposal, approval, authorization, admission,
authoritative terminal result, bounded conversation presentation, and stale
attempt recovery. It uses temporary synthetic ledgers and in-memory executors
only. No registered tool, provider, production runtime, or source-changing
operation is invoked.
"""

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Mapping

from action_execution_admission import authorize_action_proposal_execution
from action_proposal_approval_decisions import decide_action_proposal
from action_proposal_handoff import build_action_proposal_handoff
from authoritative_action_results import CONTRACT_VERSION as RESULT_CONTRACT_VERSION, MAX_TERMINAL_RESULT_BYTES, execute_admitted_action, inspect_authoritative_action_results
from checkpoint_registry import inspect_checkpoint_registry
from natural_language_action_approval_governance_checkpoint import build_natural_language_action_approval_governance_checkpoint
from natural_language_action_routing import build_natural_language_action_projection
from package_integrity import package_privacy_summary_for_root
from persisted_action_proposals import persist_action_proposal, request_action_proposal_approval
from supervised_result_presentation import CONTRACT_VERSION as PRESENTATION_CONTRACT_VERSION, MAX_PRESENTATION_BYTES, build_supervised_result_presentation, supervised_result_prompt
from supervised_result_reliability import CONTRACT_VERSION as RELIABILITY_CONTRACT_VERSION, DEFAULT_STALE_AFTER_SECONDS, MAX_RECOVERY_RECEIPT_BYTES, inspect_result_reliability, recover_stale_execution_attempt

CONTRACT_VERSION = "v1178.9"
_CHECKPOINT_ID = "natural-language-action-authoritative-result:v1178.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_REPORT_TEXT = (
    "RESULT_PRIVATE_CANARY",
    "ACTION_PRIVATE_CANARY",
    "PROVIDER_PRIVATE_CANARY",
    "MEMORY_PRIVATE_CANARY",
    "raw_tool_arguments",
    "chain_of_thought",
    "private reasoning payload",
    "checkpoint-result-operation",
    "checkpoint-secret-output",
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


def _bounded_result(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(value.get("ok")),
        "state": str(value.get("state") or "")[:48],
        "terminal": bool(value.get("terminal")),
        "executed": bool(value.get("executed")),
        "executor_invoked": bool(value.get("executor_invoked")),
        "recovered": bool(value.get("recovered")),
        "execution_performed": bool(value.get("execution_performed")),
        "content_free": bool(value.get("content_free", True)),
        "raw_output_included": bool(value.get("raw_output_included")),
        "raw_arguments_included": bool(value.get("raw_arguments_included")),
        "authority_granted": bool(value.get("authority_granted")),
        "error_kind": str(value.get("error_kind") or "")[:80],
        "reason": str(value.get("reason") or "")[:80],
    }


def _admitted_lifecycle(path: Path, *, start: float, operation_id: str) -> dict[str, Any]:
    projection = build_natural_language_action_projection("Run diagnostics.")
    handoff = build_action_proposal_handoff(
        projection, operation_id=f"checkpoint-candidate-{int(start)}",
    )
    proposal = dict(handoff.get("proposal") or {})
    proposal_digest = str(proposal.get("proposal_digest") or "")
    saved = persist_action_proposal(
        path, handoff, expected_proposal_digest=proposal_digest, now=start,
    )
    proposal_id = str(saved.get("proposal_id") or "")
    requested = request_action_proposal_approval(
        path,
        proposal_id=proposal_id,
        proposal_digest=proposal_digest,
        explicit_control_text="Request approval for diagnostics.",
        now=start + 1,
    )
    decided = decide_action_proposal(
        path,
        proposal_id=proposal_id,
        proposal_digest=proposal_digest,
        approval_request_digest=str(requested.get("approval_request_digest") or ""),
        explicit_operator_text=f"Approve proposal {proposal_id}.",
        operator_authority="operator",
        now=start + 2,
    )
    admitted = authorize_action_proposal_execution(
        path,
        proposal_id=proposal_id,
        proposal_digest=proposal_digest,
        approval_decision_digest=str(decided.get("approval_decision_digest") or ""),
        explicit_operator_text=f"Authorize execution for proposal {proposal_id}.",
        operator_authority="operator",
        operation_id=operation_id,
        now=start + 3,
    )
    return {
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
        "saved": saved,
        "requested": requested,
        "decided": decided,
        "admitted": admitted,
    }


def _execute(path: Path, lifecycle: Mapping[str, Any], executor: Callable[[], Mapping[str, Any]], **kwargs: Any) -> dict[str, Any]:
    admitted = dict(lifecycle.get("admitted") or {})
    return execute_admitted_action(
        path,
        proposal_id=str(lifecycle.get("proposal_id") or ""),
        proposal_digest=str(lifecycle.get("proposal_digest") or ""),
        authorization_digest=str(admitted.get("authorization_digest") or ""),
        execution_admission_digest=str(admitted.get("execution_admission_digest") or ""),
        operation_digest=str(admitted.get("operation_digest") or ""),
        admission_receipt_digest=str(admitted.get("receipt_digest") or ""),
        executor=executor,
        **kwargs,
    )


def build_natural_language_action_authoritative_result_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    prior = build_natural_language_action_approval_governance_checkpoint(
        source_root=source, runtime_root=runtime,
    )
    require(prior.get("ok"))
    require(prior.get("read_only"))
    require(prior.get("post_available") is False)
    require(prior.get("authority_preserved"))
    require(prior.get("content_free"))
    require(prior.get("source_modified") is False)
    require(prior.get("runtime_mutated") is False)
    require(prior.get("executor_invoked") is False)

    terminal_evidence: dict[str, Any] = {}
    presentation_evidence: dict[str, Any] = {}
    recovery_evidence: dict[str, Any] = {}

    with TemporaryDirectory() as directory:
        temp = Path(directory)

        # Exact success and terminal replay.
        success_path = temp / "success.json"
        success_lifecycle = _admitted_lifecycle(
            success_path, start=100, operation_id="checkpoint-result-operation-success",
        )
        require(success_lifecycle["saved"].get("ok"))
        require(success_lifecycle["requested"].get("approval_requested"))
        require(success_lifecycle["decided"].get("approval_granted"))
        require(success_lifecycle["admitted"].get("execution_admitted"))
        calls: list[int] = []
        success = _execute(
            success_path,
            success_lifecycle,
            lambda: calls.append(1) or {
                "ok": True,
                "status": "completed",
                "result_kind": "diagnostics",
                "item_count": 4,
                "raw_output": "checkpoint-secret-output",
            },
            now=104,
        )
        require(success.get("ok"))
        require(success.get("state") == "execution_succeeded")
        require(success.get("terminal"))
        require(success.get("executed"))
        require(success.get("executor_invoked"))
        require(len(calls) == 1)
        require(len(str(success.get("terminal_result_digest") or "")) == 64)
        require(len(str(success.get("supervised_result_digest") or "")) == 64)
        require(len(str(success.get("outcome_digest") or "")) == 64)
        require(len(str(success.get("execution_attempt_digest") or "")) == 64)
        require(success.get("content_free"))
        require(success.get("raw_output_included") is False)
        require(success.get("raw_arguments_included") is False)
        require(success.get("authority_granted") is False)
        require(success.get("source_modified") is False)
        success_text = success_path.read_text(encoding="utf-8")
        require("checkpoint-result-operation-success" not in success_text)
        require("checkpoint-secret-output" not in success_text)
        require("Run diagnostics" not in success_text)
        require(len(success_text.encode("utf-8")) < 20000)
        replay = _execute(
            success_path, success_lifecycle,
            lambda: calls.append(2) or {"ok": True},
            now=105,
        )
        require(replay.get("ok") is False)
        require(replay.get("state") == "replayed")
        require(replay.get("terminal"))
        require(len(calls) == 1)
        inspection = inspect_authoritative_action_results(success_path)
        require(inspection.get("terminal_result_count") == 1)
        require((inspection.get("state_counts") or {}).get("execution_succeeded") == 1)
        require(inspection.get("raw_output_exposed") is False)
        require(inspection.get("raw_arguments_exposed") is False)
        require(inspection.get("conversation_can_execute") is False)
        require(inspection.get("authority_granted") is False)

        # Exact mismatch blocks before executor invocation.
        blocked_path = temp / "blocked.json"
        blocked_lifecycle = _admitted_lifecycle(
            blocked_path, start=200, operation_id="checkpoint-result-operation-blocked",
        )
        blocked_admission = dict(blocked_lifecycle["admitted"])
        blocked_calls: list[int] = []
        blocked = execute_admitted_action(
            blocked_path,
            proposal_id=str(blocked_lifecycle["proposal_id"]),
            proposal_digest=str(blocked_lifecycle["proposal_digest"]),
            authorization_digest="0" * 64,
            execution_admission_digest=str(blocked_admission.get("execution_admission_digest") or ""),
            operation_digest=str(blocked_admission.get("operation_digest") or ""),
            admission_receipt_digest=str(blocked_admission.get("receipt_digest") or ""),
            executor=lambda: blocked_calls.append(1) or {"ok": True},
            now=204,
        )
        require(blocked.get("ok") is False)
        require(blocked.get("state") == "blocked")
        require(blocked.get("executor_invoked") is False)
        require(blocked.get("executed") is False)
        require(not blocked_calls)

        # Bounded terminal variants.
        variants: dict[str, dict[str, Any]] = {}
        variant_specs: tuple[tuple[str, Callable[[], Mapping[str, Any]], dict[str, Any]], ...] = (
            ("failure", lambda: {"ok": False, "status": "failed", "result_kind": "diagnostics", "item_count": 1}, {}),
            ("malformed", lambda: "checkpoint-secret-output", {}),  # type: ignore[return-value]
            ("exception", lambda: (_ for _ in ()).throw(RuntimeError("checkpoint-secret-output")), {}),
        )
        for index, (name, executor, options) in enumerate(variant_specs, start=3):
            path = temp / f"{name}.json"
            lifecycle = _admitted_lifecycle(
                path, start=index * 100, operation_id=f"checkpoint-result-operation-{name}",
            )
            result = _execute(path, lifecycle, executor, now=index * 100 + 4, **options)
            variants[name] = result
            require(result.get("state") == "execution_failed")
            require(result.get("terminal"))
            require(result.get("executor_invoked"))
            require(result.get("raw_output_included") is False)
            require(result.get("raw_arguments_included") is False)
            require("checkpoint-secret-output" not in path.read_text(encoding="utf-8"))

        cancel_path = temp / "cancel.json"
        cancel_lifecycle = _admitted_lifecycle(
            cancel_path, start=600, operation_id="checkpoint-result-operation-cancel",
        )
        event = threading.Event()
        event.set()
        cancelled = _execute(
            cancel_path, cancel_lifecycle, lambda: {"ok": True}, cancel_event=event, now=604,
        )
        variants["cancelled"] = cancelled
        require(cancelled.get("state") == "execution_cancelled")
        require(cancelled.get("terminal"))
        require(cancelled.get("executed") is False)
        require(cancelled.get("executor_invoked"))

        timeout_path = temp / "timeout.json"
        timeout_lifecycle = _admitted_lifecycle(
            timeout_path, start=700, operation_id="checkpoint-result-operation-timeout",
        )
        timed_out = _execute(
            timeout_path,
            timeout_lifecycle,
            lambda: (time.sleep(0.05) or {"ok": True}),
            timeout_seconds=0.01,
            now=704,
        )
        variants["timed_out"] = timed_out
        require(timed_out.get("state") == "execution_timed_out")
        require(timed_out.get("terminal"))
        require(timed_out.get("executed"))
        require(timed_out.get("executor_invoked"))

        # Unique terminal presentation, identical deduplication, and conflict ambiguity.
        presentation = build_supervised_result_presentation("diagnostics", [success])
        require(presentation.get("authoritative_receipt_present"))
        require(presentation.get("presentation_status") == "authoritative_terminal_result")
        require(presentation.get("state") == "execution_succeeded")
        require(presentation.get("status_label") == "completed successfully")
        require(presentation.get("receipt_count") == 1)
        require(presentation.get("execution_invoked") is False)
        require(presentation.get("authority_granted") is False)
        require(presentation.get("raw_output_included") is False)
        require(presentation.get("raw_arguments_included") is False)
        prompt = supervised_result_prompt(presentation)
        require("Do not invent raw output" in prompt)
        require("current conversation did not execute" in prompt)
        require("checkpoint-secret-output" not in prompt)
        duplicate_presentation = build_supervised_result_presentation("diagnostics", [success, dict(success)])
        require(duplicate_presentation.get("authoritative_receipt_present"))
        require(duplicate_presentation.get("receipt_count") == 1)
        conflict = dict(success)
        conflict["terminal_result_digest"] = "f" * 64
        ambiguous = build_supervised_result_presentation("diagnostics", [success, conflict])
        require(ambiguous.get("presentation_status") == "ambiguous")
        require(ambiguous.get("authoritative_receipt_present") is False)
        require(ambiguous.get("receipt_count") == 2)
        mismatch = build_supervised_result_presentation("maintenance", [success])
        require(mismatch.get("presentation_status") == "unavailable")
        require(mismatch.get("authoritative_receipt_present") is False)
        malformed_presentation = build_supervised_result_presentation(
            "diagnostics", [dict(success, terminal_result_digest="bad")],
        )
        require(malformed_presentation.get("presentation_status") == "unavailable")

        # Stale exact attempt recovery without re-execution.
        stale_path = temp / "stale.json"
        stale_lifecycle = _admitted_lifecycle(
            stale_path, start=800, operation_id="checkpoint-result-operation-stale",
        )
        state = json.loads(stale_path.read_text(encoding="utf-8"))
        row = state["records"][-1]
        row.update(
            state="execution_in_progress",
            execution_in_progress=True,
            execution_started_at=804.0,
            execution_attempt_digest="e" * 64,
        )
        stale_path.write_text(
            json.dumps(state, sort_keys=True, separators=(",", ":")), encoding="utf-8",
        )
        reliability_before = inspect_result_reliability(stale_path, now=1200)
        require(reliability_before.get("in_progress") == 1)
        require(reliability_before.get("stale_in_progress") == 1)
        require(reliability_before.get("terminal") == 0)
        require(reliability_before.get("executor_invoked") is False)
        require(reliability_before.get("authority_granted") is False)
        fresh = recover_stale_execution_attempt(
            stale_path,
            proposal_id=str(stale_lifecycle["proposal_id"]),
            attempt_digest="e" * 64,
            now=900,
            stale_after_seconds=300,
        )
        require(fresh.get("state") == "not_stale")
        require(fresh.get("executor_invoked") is False)
        wrong_attempt = recover_stale_execution_attempt(
            stale_path,
            proposal_id=str(stale_lifecycle["proposal_id"]),
            attempt_digest="d" * 64,
            now=1200,
            stale_after_seconds=300,
        )
        require(wrong_attempt.get("state") == "blocked")
        require(wrong_attempt.get("executor_invoked") is False)
        recovered = recover_stale_execution_attempt(
            stale_path,
            proposal_id=str(stale_lifecycle["proposal_id"]),
            attempt_digest="e" * 64,
            now=1200,
            stale_after_seconds=300,
        )
        require(recovered.get("ok"))
        require(recovered.get("state") == "execution_failed")
        require(recovered.get("terminal"))
        require(recovered.get("recovered"))
        require(recovered.get("executor_invoked") is False)
        require(recovered.get("execution_performed") is False)
        require(recovered.get("error_kind") == "interrupted_before_terminal_result")
        require(len(str(recovered.get("terminal_result_digest") or "")) == 64)
        require(len(str(recovered.get("supervised_result_digest") or "")) == 64)
        require(len(str(recovered.get("outcome_digest") or "")) == 64)
        require("checkpoint-result-operation-stale" not in stale_path.read_text(encoding="utf-8"))
        recovery_replay = recover_stale_execution_attempt(
            stale_path,
            proposal_id=str(stale_lifecycle["proposal_id"]),
            attempt_digest="e" * 64,
            now=1300,
        )
        require(recovery_replay.get("state") == "terminal")
        require(recovery_replay.get("executor_invoked") is False)
        reliability_after = inspect_result_reliability(stale_path, now=1300)
        require(reliability_after.get("in_progress") == 0)
        require(reliability_after.get("terminal") == 1)
        require(reliability_after.get("malformed_terminal") == 0)
        malformed_inspection = inspect_result_reliability(temp / "malformed-ledger.json")
        require(malformed_inspection.get("record_count") == 0)
        require(malformed_inspection.get("content_free"))

        terminal_evidence = {
            "success": _bounded_result(success),
            "replay": _bounded_result(replay),
            "blocked": _bounded_result(blocked),
            **{name: _bounded_result(result) for name, result in variants.items()},
            "inspection_terminal_count": int(inspection.get("terminal_result_count") or 0),
        }
        presentation_evidence = {
            "unique_status": str(presentation.get("presentation_status") or ""),
            "unique_state": str(presentation.get("state") or ""),
            "duplicate_receipt_count": int(duplicate_presentation.get("receipt_count") or 0),
            "conflict_status": str(ambiguous.get("presentation_status") or ""),
            "mismatch_status": str(mismatch.get("presentation_status") or ""),
        }
        recovery_evidence = {
            "before": {
                "in_progress": int(reliability_before.get("in_progress") or 0),
                "stale_in_progress": int(reliability_before.get("stale_in_progress") or 0),
            },
            "fresh": _bounded_result(fresh),
            "wrong_attempt": _bounded_result(wrong_attempt),
            "recovered": _bounded_result(recovered),
            "replay": _bounded_result(recovery_replay),
            "after": {
                "in_progress": int(reliability_after.get("in_progress") or 0),
                "terminal": int(reliability_after.get("terminal") or 0),
            },
        }

    runtime_source = (source / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    parity_counts = {
        "presentation_build_count": runtime_source.count("build_supervised_result_presentation("),
        "presentation_prompt_count": runtime_source.count("supervised_result_prompt(result_presentation)"),
        "presentation_context_count": runtime_source.count(
            'result.cognitive_context["supervised_result_presentation"] = result_presentation'
        ),
        "authoritative_result_parameter_count": runtime_source.count(
            "authoritative_action_results: tuple[dict[str, Any], ...] = ()"
        ),
        "execute_admitted_call_count": runtime_source.count("execute_admitted_action("),
        "recover_stale_call_count": runtime_source.count("recover_stale_execution_attempt("),
        "ledger_read_call_count": runtime_source.count("inspect_authoritative_action_results("),
    }
    require(parity_counts["presentation_build_count"] == 2)
    require(parity_counts["presentation_prompt_count"] == 2)
    require(parity_counts["presentation_context_count"] == 2)
    require(parity_counts["authoritative_result_parameter_count"] == 2)
    require(parity_counts["execute_admitted_call_count"] == 0)
    require(parity_counts["recover_stale_call_count"] == 0)
    require(parity_counts["ledger_read_call_count"] == 0)

    source_contract = {
        "result_contract": RESULT_CONTRACT_VERSION,
        "presentation_contract": PRESENTATION_CONTRACT_VERSION,
        "reliability_contract": RELIABILITY_CONTRACT_VERSION,
        "maximum_terminal_result_bytes": MAX_TERMINAL_RESULT_BYTES,
        "maximum_presentation_bytes": MAX_PRESENTATION_BYTES,
        "maximum_recovery_receipt_bytes": MAX_RECOVERY_RECEIPT_BYTES,
        "default_stale_after_seconds": DEFAULT_STALE_AFTER_SECONDS,
    }
    require(source_contract["result_contract"] == "v1178.8")
    require(source_contract["presentation_contract"] == "v1178.8")
    require(source_contract["reliability_contract"] == "v1178.8")
    require(source_contract["maximum_terminal_result_bytes"] <= 4096)
    require(source_contract["maximum_presentation_bytes"] <= 4096)
    require(source_contract["maximum_recovery_receipt_bytes"] <= 4096)
    require(source_contract["default_stale_after_seconds"] == 300.0)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next(
        (
            row for row in registry.get("checkpoints", [])
            if row.get("checkpoint_id") == "natural-language-action-authoritative-result-checkpoint"
        ),
        None,
    )
    privacy = package_privacy_summary_for_root(source)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_natural_language_action_authoritative_result_checkpoint")
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))
    require(privacy.get("forbidden_entry_count", 0) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)
    require(source_before == _tree_signature(source))
    require(runtime_before == _tree_signature(runtime))

    evidence = {
        "prior_checkpoint": {
            "ok": bool(prior.get("ok")),
            "passed": int(prior.get("passed") or 0),
            "total": int(prior.get("total") or 0),
        },
        "terminal_results": terminal_evidence,
        "presentation": presentation_evidence,
        "recovery": recovery_evidence,
        "conversation_parity": parity_counts,
        "source_contract": source_contract,
    }
    evidence_text = json.dumps(evidence, sort_keys=True, default=str)
    forbidden_count = sum(evidence_text.count(token) for token in _FORBIDDEN_REPORT_TEXT)
    require(forbidden_count == 0)

    report = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": forbidden_count == 0,
        "authority_preserved": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "natural_language_action_authoritative_result_checkpoint_completed": True,
        "intent_through_authoritative_result_consolidated": True,
        "synthetic_terminal_lifecycle_exercised": True,
        "stale_attempt_recovery_exercised_without_reexecution": True,
        "conversation_result_presentation_parity_preserved": True,
        "raw_request_persisted": False,
        "raw_argument_values_persisted": False,
        "raw_operation_identity_persisted": False,
        "raw_output_persisted": False,
        "automatic_proposal_persistence": False,
        "automatic_approval_requested": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "conversation_execution_admitted": False,
        "conversation_action_executed": False,
        "registered_tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "source_edit_performed": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "source_modified": source_before != _tree_signature(source),
        "runtime_mutated": runtime_before != _tree_signature(runtime),
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "retained_checkpoint_count": 1,
            "terminal_result_case_count": 7,
            "negative_boundary_case_count": 11,
            "presentation_case_count": 5,
            "recovery_case_count": 6,
            "conversation_execution_call_count": (
                parity_counts["execute_admitted_call_count"]
                + parity_counts["recover_stale_call_count"]
                + parity_counts["ledger_read_call_count"]
            ),
            "maximum_terminal_result_bytes": MAX_TERMINAL_RESULT_BYTES,
            "maximum_presentation_bytes": MAX_PRESENTATION_BYTES,
            "maximum_recovery_receipt_bytes": MAX_RECOVERY_RECEIPT_BYTES,
            "default_stale_after_seconds": DEFAULT_STALE_AFTER_SECONDS,
            "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", 0)),
            "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0)),
            "open_limitation_count": 4,
        },
        "evidence": evidence,
    }
    report["structural_digest"] = _digest(
        {key: value for key, value in report.items() if key != "structural_digest"}
    )
    return report
