from __future__ import annotations

"""Strictly read-only v1175.9 natural-language action execution checkpoint."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Mapping

from action_proposal_handoff import CONTRACT_VERSION as PROPOSAL_CONTRACT_VERSION, MAX_HANDOFF_BYTES, action_proposal_handoff_public, build_action_proposal_handoff
from checkpoint_registry import inspect_checkpoint_registry
from natural_language_action_routing import ACTION_INTENT_CONTRACT_VERSION, MAX_ACTION_INPUT_CHARS, MAX_RECEIPT_BYTES, action_projection_contains_private_fields, bound_unverified_action_claim, build_natural_language_action_projection, natural_language_action_public_projection
from package_integrity import package_privacy_summary_for_root
from supervised_action_execution import CONTRACT_VERSION as EXECUTION_CONTRACT_VERSION, EXECUTION_ELIGIBLE_CAPABILITIES, MAX_RESULT_BYTES, build_supervised_execution_projection, execute_supervised_action, supervised_execution_public

CONTRACT_VERSION = "v1175.9"
_CHECKPOINT_ID = "natural-language-action-execution:v1175.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_TEXT = (
    "ACTION_PRIVATE_CANARY", "PROVIDER_PRIVATE_CANARY", "MEMORY_PRIVATE_CANARY",
    "raw_tool_arguments", "chain_of_thought", "private reasoning payload",
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


def _summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    intent = dict(projection.get("intent") or {})
    grounding = dict(projection.get("grounding") or {})
    receipt = dict(projection.get("receipt") or {})
    diagnostics = dict(projection.get("diagnostics") or {})
    return {
        "category": str(intent.get("category") or ""),
        "action_intent_present": bool(intent.get("action_intent_present")),
        "correction_present": bool(intent.get("correction_present")),
        "planning_present": bool(intent.get("planning_present")),
        "requires_clarification": bool(intent.get("requires_clarification")),
        "hypothetical_language_present": bool(intent.get("hypothetical_language_present")),
        "quoted_command_present": bool(intent.get("quoted_command_present")),
        "multi_turn_reference_present": bool(intent.get("multi_turn_reference_present")),
        "grounding_status": str(grounding.get("grounding_status") or ""),
        "capability_id": str(grounding.get("capability_id") or ""),
        "capability_registered": bool(grounding.get("capability_registered")),
        "authority_required": bool(grounding.get("authority_required")),
        "authorization_state": str(grounding.get("authorization_state") or ""),
        "approval_state": str(grounding.get("approval_state") or ""),
        "execution_state": str(grounding.get("execution_state") or ""),
        "receipt_execution_state": str(receipt.get("execution_state") or ""),
        "authoritative_receipt_present": bool(grounding.get("authoritative_execution_receipt_present")),
        "receipt_bounded": bool(diagnostics.get("receipt_bounded")),
        "receipt_bytes": int(diagnostics.get("receipt_bytes") or 0),
        "content_free": bool(receipt.get("content_free")) and bool(diagnostics.get("content_free")),
    }


def _proposal_summary(handoff: Mapping[str, Any]) -> dict[str, Any]:
    proposal = dict(handoff.get("proposal") or {})
    approval = dict(handoff.get("approval_handoff") or {})
    execution = dict(handoff.get("execution_admission") or {})
    diagnostics = dict(handoff.get("diagnostics") or {})
    return {
        "proposal_state": str(proposal.get("proposal_state") or ""),
        "capability_id": str(proposal.get("capability_id") or ""),
        "capability_registered": bool(proposal.get("capability_registered")),
        "persisted": bool(proposal.get("persisted")),
        "approval_created": bool(approval.get("approval_created")),
        "approval_granted": bool(approval.get("approval_granted")),
        "persisted_proposal_verified": bool(approval.get("persisted_proposal_verified")),
        "go_ahead_is_approval": bool(approval.get("go_ahead_is_approval")),
        "admitted": bool(execution.get("admitted")),
        "executed": bool(execution.get("executed")),
        "authoritative_receipt_created": bool(execution.get("authoritative_receipt_created")),
        "content_free": bool(diagnostics.get("content_free")),
        "handoff_bounded": bool(diagnostics.get("handoff_bounded")),
        "handoff_bytes": int(diagnostics.get("handoff_bytes") or 0),
    }


def _execution_summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "capability_id": str(projection.get("capability_id") or ""),
        "registered_capability": bool(projection.get("registered_capability")),
        "execution_eligible": bool(projection.get("execution_eligible")),
        "approval_verified": bool(projection.get("approval_verified")),
        "replay_detected": bool(projection.get("replay_detected")),
        "admitted": bool(projection.get("admitted")),
        "executed": bool(projection.get("executed")),
        "state": str(projection.get("state") or ""),
        "conversation_can_execute": bool(projection.get("conversation_can_execute")),
        "automatic_approval_allowed": bool(projection.get("automatic_approval_allowed")),
        "content_free": bool(projection.get("content_free")),
        "authority_free_projection": bool(projection.get("authority_free_projection")),
    }


def _result_summary(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "capability_id": str(receipt.get("capability_id") or ""),
        "state": str(receipt.get("state") or ""),
        "ok": bool(receipt.get("ok")),
        "executed": bool(receipt.get("executed")),
        "terminal": bool(receipt.get("terminal")),
        "error_kind": str(receipt.get("error_kind") or ""),
        "replay_safe": bool(receipt.get("replay_safe")),
        "content_free": bool(receipt.get("content_free")),
        "raw_output_included": bool(receipt.get("raw_output_included")),
        "raw_arguments_included": bool(receipt.get("raw_arguments_included")),
        "authority_granted": bool(receipt.get("authority_granted")),
        "source_modified": bool(receipt.get("source_modified")),
        "receipt_bytes": int(receipt.get("receipt_bytes") or 0),
    }


def _approval(handoff: Mapping[str, Any]) -> dict[str, Any]:
    proposal = dict(handoff.get("proposal") or {})
    return {
        "authoritative": True,
        "status": "approved",
        "authority": "operator",
        "capability_id": proposal.get("capability_id"),
        "proposal_digest": proposal.get("proposal_digest"),
        "approval_digest": "a" * 64,
        "revoked": False,
        "expired": False,
    }


def build_natural_language_action_execution_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    messages = {
        "conversation": "I like the name Eidolon.",
        "question": "Do you like the name Eidolon?",
        "correction": "Stop calling me Daddy.",
        "planning": "Help me plan a maintenance review.",
        "diagnostics": "Run diagnostics.",
        "maintenance": "Do a system maintenance check.",
        "project": "Inspect your project.",
        "file_review": "Review conscious_agent/memory.py.",
        "patch": "Change the dashboard background.",
        "uncertain": "Could you maybe run diagnostics?",
        "hypothetical": "What if I said 'run diagnostics'?",
        "quoted": '"Run diagnostics."',
        "unsupported": "Install a new model.",
        "ambiguous": "Go ahead.",
        "oversized": "Run diagnostics. " + ("x" * (MAX_ACTION_INPUT_CHARS + 200)),
    }
    projections = {name: build_natural_language_action_projection(text) for name, text in messages.items()}
    persisted_history = [{
        "user_message": "Run diagnostics.",
        "action_status_summary": "diagnostics is proposed. persisted evidence exists",
    }]
    projections["resolved_follow_up"] = build_natural_language_action_projection(
        "Go ahead.", conversation_history=persisted_history,
    )
    authoritative_receipt = {
        "authoritative": True,
        "status": "completed",
        "capability_id": "diagnostics",
        "receipt_digest": "b" * 64,
        "approval_granted": False,
    }
    projections["authoritative_result"] = build_natural_language_action_projection(
        "Run diagnostics.", authoritative_receipts=[authoritative_receipt, authoritative_receipt],
    )
    projection_summaries = {name: _summary(value) for name, value in projections.items()}

    require(projection_summaries["conversation"]["category"] == "conversation")
    require(projection_summaries["question"]["category"] == "question")
    require(not projection_summaries["question"]["action_intent_present"])
    require(projection_summaries["correction"]["category"] == "correction")
    require(projection_summaries["correction"]["correction_present"])
    require(projection_summaries["planning"]["category"] == "planning_request")
    require(projection_summaries["planning"]["planning_present"])
    for name, capability in (
        ("diagnostics", "diagnostics"), ("maintenance", "maintenance"),
        ("project", "task_project"), ("file_review", "file_review"),
        ("patch", "patch_proposal"),
    ):
        require(projection_summaries[name]["category"] == "action_request")
        require(projection_summaries[name]["grounding_status"] == "matched")
        require(projection_summaries[name]["capability_id"] == capability)
        require(projection_summaries[name]["capability_registered"])
        require(projection_summaries[name]["authorization_state"] == "not_granted")
        require(projection_summaries[name]["approval_state"] == "not_created")
        require(projection_summaries[name]["execution_state"] == "not_executed")
    require(projection_summaries["uncertain"]["requires_clarification"])
    require(projection_summaries["hypothetical"]["hypothetical_language_present"])
    require(not projection_summaries["hypothetical"]["action_intent_present"])
    require(projection_summaries["quoted"]["quoted_command_present"])
    require(not projection_summaries["quoted"]["action_intent_present"])
    require(projection_summaries["unsupported"]["grounding_status"] in {"unsupported", "unmatched", "unavailable"})
    require(projection_summaries["ambiguous"]["grounding_status"] in {"ambiguous", "unmatched"})
    require(projection_summaries["oversized"]["requires_clarification"])
    require(projection_summaries["resolved_follow_up"]["capability_id"] == "diagnostics")
    require(projection_summaries["resolved_follow_up"]["authorization_state"] == "not_granted")
    require(projection_summaries["authoritative_result"]["authoritative_receipt_present"])
    require(projection_summaries["authoritative_result"]["receipt_execution_state"] == "completed")
    require(all(row["receipt_bounded"] and row["receipt_bytes"] <= MAX_RECEIPT_BYTES for row in projection_summaries.values()))
    require(all(row["content_free"] for row in projection_summaries.values()))
    require(all(not action_projection_contains_private_fields(natural_language_action_public_projection(value)) for value in projections.values()))

    handoffs = {
        name: build_action_proposal_handoff(value, operation_id=f"checkpoint-{name}")
        for name, value in projections.items()
    }
    handoff_summaries = {name: _proposal_summary(value) for name, value in handoffs.items()}
    for name in ("diagnostics", "maintenance", "project", "file_review", "patch", "resolved_follow_up"):
        require(handoff_summaries[name]["proposal_state"] == "ready_for_operator_review")
        require(not handoff_summaries[name]["persisted"])
        require(not handoff_summaries[name]["approval_created"])
        require(not handoff_summaries[name]["approval_granted"])
        require(not handoff_summaries[name]["admitted"])
        require(not handoff_summaries[name]["executed"])
    for name in ("conversation", "question", "correction", "planning", "uncertain", "hypothetical", "quoted", "unsupported", "ambiguous"):
        require(handoff_summaries[name]["proposal_state"] == "not_ready")
    require(all(row["content_free"] and row["handoff_bounded"] and row["handoff_bytes"] <= MAX_HANDOFF_BYTES for row in handoff_summaries.values()))
    require(all(not row["go_ahead_is_approval"] for row in handoff_summaries.values()))

    eligible_handoff = handoffs["diagnostics"]
    approval = _approval(eligible_handoff)
    execution_cases: dict[str, Mapping[str, Any]] = {
        "admitted": build_supervised_execution_projection(
            eligible_handoff, approval_receipt=approval, operation_id="checkpoint-exec",
        ),
        "no_approval": build_supervised_execution_projection(
            eligible_handoff, operation_id="checkpoint-no-approval",
        ),
        "blocked_patch": build_supervised_execution_projection(
            handoffs["patch"], approval_receipt=_approval(handoffs["patch"]), operation_id="checkpoint-patch",
        ),
    }
    replay_seed = execution_cases["admitted"]
    execution_cases["replay"] = build_supervised_execution_projection(
        eligible_handoff,
        approval_receipt=approval,
        operation_id="checkpoint-exec",
        prior_result_receipts=[{
            "operation_digest": replay_seed.get("operation_digest"),
            "terminal": True,
        }],
    )
    bad_approval = deepcopy(approval)
    bad_approval["proposal_digest"] = "c" * 64
    execution_cases["digest_mismatch"] = build_supervised_execution_projection(
        eligible_handoff, approval_receipt=bad_approval, operation_id="checkpoint-bad",
    )
    execution_summaries = {name: _execution_summary(value) for name, value in execution_cases.items()}
    require(execution_summaries["admitted"]["execution_eligible"])
    require(execution_summaries["admitted"]["approval_verified"])
    require(execution_summaries["admitted"]["admitted"])
    require(not execution_summaries["admitted"]["executed"])
    require(not execution_summaries["admitted"]["conversation_can_execute"])
    require(not execution_summaries["admitted"]["automatic_approval_allowed"])
    require(not execution_summaries["no_approval"]["admitted"])
    require(not execution_summaries["blocked_patch"]["admitted"])
    require(execution_summaries["replay"]["replay_detected"])
    require(not execution_summaries["replay"]["admitted"])
    require(not execution_summaries["digest_mismatch"]["approval_verified"])
    require(all(row["content_free"] and row["authority_free_projection"] for row in execution_summaries.values()))
    require(set(EXECUTION_ELIGIBLE_CAPABILITIES) == {"diagnostics", "maintenance", "settings_health"})

    admitted = execution_cases["admitted"]
    cancel_event = threading.Event()
    cancel_event.set()
    result_cases = {
        "success": execute_supervised_action(
            admitted,
            executor=lambda: {"ok": True, "status": "completed", "result_kind": "diagnostics", "item_count": 3},
        ),
        "reported_failure": execute_supervised_action(
            admitted,
            executor=lambda: {"ok": False, "status": "failed", "result_kind": "diagnostics", "item_count": 1},
        ),
        "malformed": execute_supervised_action(admitted, executor=lambda: "not-a-mapping"),
        "exception": execute_supervised_action(
            admitted, executor=lambda: (_ for _ in ()).throw(RuntimeError("ACTION_PRIVATE_CANARY")),
        ),
        "timeout": execute_supervised_action(
            admitted, executor=lambda: (time.sleep(0.05) or {"ok": True}), timeout_seconds=0.01,
        ),
        "cancelled": execute_supervised_action(
            admitted, executor=lambda: {"ok": True}, cancel_event=cancel_event,
        ),
        "blocked": execute_supervised_action(
            execution_cases["no_approval"], executor=lambda: {"ok": True},
        ),
    }
    result_summaries = {name: _result_summary(value) for name, value in result_cases.items()}
    require(result_summaries["success"]["state"] == "succeeded" and result_summaries["success"]["ok"])
    require(result_summaries["reported_failure"]["state"] == "failed")
    require(result_summaries["malformed"]["error_kind"] == "malformed_executor_result")
    require(result_summaries["exception"]["error_kind"] == "executor_exception")
    require(result_summaries["timeout"]["state"] == "timed_out")
    require(result_summaries["cancelled"]["state"] == "cancelled")
    require(result_summaries["blocked"]["state"] == "blocked")
    require(all(row["terminal"] and row["replay_safe"] for row in result_summaries.values()))
    require(all(row["content_free"] and not row["raw_output_included"] and not row["raw_arguments_included"] for row in result_summaries.values()))
    require(all(not row["authority_granted"] and not row["source_modified"] for row in result_summaries.values()))
    require(all(row["receipt_bytes"] <= MAX_RESULT_BYTES for row in result_summaries.values()))

    unverified_claim = bound_unverified_action_claim(
        "I ran diagnostics and everything succeeded.", projections["diagnostics"],
    )
    verified_claim = bound_unverified_action_claim(
        "The bounded receipt reports completion.", projections["authoritative_result"],
    )
    require("Nothing ran" in unverified_claim)
    require(verified_claim == "The bounded receipt reports completion.")

    runtime_source = (source / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    parity_counts = {
        "routing_build_count": runtime_source.count("build_natural_language_action_projection("),
        "proposal_build_count": runtime_source.count("build_action_proposal_handoff(action_projection, operation_id=operation_id)"),
        "execution_build_count": runtime_source.count("build_supervised_execution_projection(action_handoff, operation_id=operation_id)"),
        "routing_public_count": runtime_source.count("natural_language_action_public_projection(action_projection)"),
        "proposal_public_count": runtime_source.count("action_proposal_handoff_public(action_handoff)"),
        "execution_public_count": runtime_source.count("supervised_execution_public(execution_projection)"),
        "conversation_executor_call_count": runtime_source.count("execute_supervised_action("),
    }
    require(parity_counts["routing_build_count"] == 2)
    require(parity_counts["proposal_build_count"] == 2)
    require(parity_counts["execution_build_count"] == 2)
    require(parity_counts["routing_public_count"] == 2)
    require(parity_counts["proposal_public_count"] == 2)
    require(parity_counts["execution_public_count"] == 2)
    require(parity_counts["conversation_executor_call_count"] == 0)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "natural-language-action-execution-checkpoint"),
        None,
    )
    privacy = package_privacy_summary_for_root(source)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_natural_language_action_execution_checkpoint")
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))
    require(privacy.get("forbidden_entry_count", 0) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)
    require(source_before == _tree_signature(source))
    require(runtime_before == _tree_signature(runtime))

    evidence = {
        "projection_summaries": projection_summaries,
        "handoff_summaries": handoff_summaries,
        "execution_summaries": execution_summaries,
        "result_summaries": result_summaries,
        "conversation_parity": parity_counts,
    }
    evidence_text = json.dumps(evidence, sort_keys=True, default=str)
    forbidden_count = sum(evidence_text.count(token) for token in _FORBIDDEN_TEXT)
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
        "natural_language_action_execution_checkpoint_completed": True,
        "intent_grounding_proposal_approval_execution_results_consolidated": True,
        "streaming_non_streaming_parity_preserved": True,
        "ordinary_conversation_execution_blocked": True,
        "synthetic_executor_contract_exercised": True,
        "real_tool_execution_performed": False,
        "proposal_persisted": False,
        "automatic_approval_created": False,
        "approval_granted_by_conversation": False,
        "conversation_execution_admitted": False,
        "conversation_action_executed": False,
        "source_edit_performed": False,
        "runtime_mutated": False,
        "memory_mutated": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "synthetic_contract_check_count": len(checks),
            "intent_projection_case_count": len(projection_summaries),
            "proposal_handoff_case_count": len(handoff_summaries),
            "execution_admission_case_count": len(execution_summaries),
            "synthetic_result_case_count": len(result_summaries),
            "execution_eligible_capability_count": len(EXECUTION_ELIGIBLE_CAPABILITIES),
            "authoritative_conversation_path_count": 2,
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "action_input_maximum_chars": MAX_ACTION_INPUT_CHARS,
            "action_receipt_maximum_bytes": MAX_RECEIPT_BYTES,
            "proposal_handoff_maximum_bytes": MAX_HANDOFF_BYTES,
            "terminal_result_maximum_bytes": MAX_RESULT_BYTES,
            "privacy_forbidden_entry_count": privacy.get("forbidden_entry_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
            "open_limitation_count": 5,
        },
        "evidence": {"synthetic_contracts": evidence},
        "source_modified": False,
        "action_intent_contract_version": ACTION_INTENT_CONTRACT_VERSION,
        "proposal_contract_version": PROPOSAL_CONTRACT_VERSION,
        "execution_contract_version": EXECUTION_CONTRACT_VERSION,
    }
    report["structural_digest"] = _digest(report)
    return report
