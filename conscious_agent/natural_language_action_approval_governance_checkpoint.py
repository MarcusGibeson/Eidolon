from __future__ import annotations

"""Strictly read-only v1177.9 action and approval-governance checkpoint.

The checkpoint consolidates natural-language action understanding, bounded
argument clarification, content-free proposal persistence, explicit approval
requests, exact operator decisions, and approval-to-execution admission.  It
uses only temporary synthetic ledgers and never invokes an executor or real
registered capability.
"""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from action_execution_admission import CONTRACT_VERSION as ADMISSION_CONTRACT_VERSION, MAX_RECEIPT_BYTES as ADMISSION_MAX_RECEIPT_BYTES, authorize_action_proposal_execution
from action_proposal_approval_decisions import CONTRACT_VERSION as DECISION_CONTRACT_VERSION, MAX_DECISION_BYTES, decide_action_proposal
from action_proposal_handoff import build_action_proposal_handoff
from checkpoint_registry import inspect_checkpoint_registry
from clarification_argument_routing_checkpoint import build_clarification_argument_routing_checkpoint
from natural_language_action_execution_checkpoint import build_natural_language_action_execution_checkpoint
from natural_language_action_routing import build_natural_language_action_projection
from package_integrity import package_privacy_summary_for_root
from persisted_action_proposals import CONTRACT_VERSION as PROPOSAL_CONTRACT_VERSION, MAX_AGE_SECONDS, MAX_RECORD_BYTES, MAX_RECORDS, inspect_persisted_action_proposals, persist_action_proposal, request_action_proposal_approval

CONTRACT_VERSION = "v1177.9"
_CHECKPOINT_ID = "natural-language-action-approval-governance:v1177.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_REPORT_TEXT = (
    "ACTION_PRIVATE_CANARY",
    "PROVIDER_PRIVATE_CANARY",
    "MEMORY_PRIVATE_CANARY",
    "raw_tool_arguments",
    "chain_of_thought",
    "private reasoning payload",
    "checkpoint-operation-identity",
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


def _bounded_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return only lifecycle state and authority booleans, never IDs or payloads."""

    return {
        "ok": bool(result.get("ok")),
        "state": str(result.get("state") or "")[:40],
        "persisted": bool(result.get("persisted")),
        "approval_requested": bool(result.get("approval_requested")),
        "approval_decided": bool(result.get("approval_decided")),
        "approval_granted": bool(result.get("approval_granted")),
        "authorization_granted": bool(result.get("authorization_granted")),
        "execution_admitted": bool(result.get("execution_admitted")),
        "execution_performed": bool(result.get("execution_performed")),
        "executor_invoked": bool(result.get("executor_invoked")),
        "content_free": bool(result.get("content_free", True)),
        "raw_content_stored": bool(result.get("raw_content_stored")),
        "argument_values_stored": bool(result.get("argument_values_stored")),
        "reason": str(result.get("reason") or "")[:80],
        "reason_codes": list(result.get("reason_codes") or [])[:8],
    }


def build_natural_language_action_approval_governance_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    # Retain the two preceding read-only consolidation surfaces.
    prior_action = build_natural_language_action_execution_checkpoint(
        source_root=source, runtime_root=runtime,
    )
    prior_clarification = build_clarification_argument_routing_checkpoint(
        source_root=source, runtime_root=runtime,
    )
    for prior in (prior_action, prior_clarification):
        require(prior.get("ok"))
        require(prior.get("read_only"))
        require(prior.get("post_available") is False)
        require(prior.get("authority_preserved"))
        require(prior.get("content_free"))
        require(prior.get("source_modified") is False)
        require(prior.get("runtime_mutated") is False)

    lifecycle_evidence: dict[str, Any] = {}
    with TemporaryDirectory() as directory:
        temp = Path(directory)
        ledger = temp / "proposal-ledger.json"

        projection = build_natural_language_action_projection("Run diagnostics.")
        handoff = build_action_proposal_handoff(
            projection, operation_id="checkpoint-proposal-candidate",
        )
        proposal = dict(handoff.get("proposal") or {})
        proposal_digest = str(proposal.get("proposal_digest") or "")
        require(proposal.get("proposal_state") == "ready_for_operator_review")
        require(proposal.get("capability_id") == "diagnostics")
        require(proposal.get("content_free") and proposal.get("authority_free"))
        require(len(proposal_digest) == 64)

        saved = persist_action_proposal(
            ledger, handoff, expected_proposal_digest=proposal_digest, now=100,
        )
        duplicate = persist_action_proposal(
            ledger, handoff, expected_proposal_digest=proposal_digest, now=101,
        )
        proposal_id = str(saved.get("proposal_id") or "")
        require(saved.get("ok") and saved.get("state") == "proposed" and saved.get("persisted"))
        require(not saved.get("approval_requested") and not saved.get("approval_created"))
        require(not saved.get("authorization_granted") and not saved.get("execution_performed"))
        require(duplicate.get("ok") and duplicate.get("state") == "duplicate")
        require(not duplicate.get("persisted"))

        vague_request = request_action_proposal_approval(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            explicit_control_text="Go ahead.",
            now=102,
        )
        wrong_capability_request = request_action_proposal_approval(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            explicit_control_text="Request approval for maintenance.",
            now=103,
        )
        approval_request = request_action_proposal_approval(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            explicit_control_text="Request approval for diagnostics.",
            now=104,
        )
        approval_request_digest = str(approval_request.get("approval_request_digest") or "")
        require(not vague_request.get("ok") and not vague_request.get("approval_requested"))
        require(not wrong_capability_request.get("ok"))
        require(approval_request.get("ok") and approval_request.get("state") == "awaiting_approval")
        require(approval_request.get("approval_requested"))
        require(not approval_request.get("approval_created") and not approval_request.get("approval_granted"))
        require(not approval_request.get("authorization_granted") and not approval_request.get("execution_admitted"))
        require(approval_request.get("go_ahead_is_approval") is False)
        require(len(approval_request_digest) == 64)

        wrong_actor_decision = decide_action_proposal(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_request_digest=approval_request_digest,
            explicit_operator_text=f"Approve proposal {proposal_id}.",
            operator_authority="assistant",
            now=105,
        )
        wrong_request_digest_decision = decide_action_proposal(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_request_digest="0" * 64,
            explicit_operator_text=f"Approve proposal {proposal_id}.",
            operator_authority="operator",
            now=106,
        )
        approved = decide_action_proposal(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_request_digest=approval_request_digest,
            explicit_operator_text=f"Approve proposal {proposal_id}.",
            operator_authority="operator",
            now=107,
        )
        approval_decision_digest = str(approved.get("approval_decision_digest") or "")
        require(not wrong_actor_decision.get("ok") and not wrong_actor_decision.get("approval_decided"))
        require(not wrong_request_digest_decision.get("ok"))
        require(approved.get("ok") and approved.get("state") == "approved")
        require(approved.get("approval_decided") and approved.get("approval_granted"))
        require(not approved.get("authorization_granted"))
        require(not approved.get("execution_admitted") and not approved.get("execution_performed"))
        require(len(approval_decision_digest) == 64)
        require(len(json.dumps(approved, sort_keys=True, separators=(",", ":")).encode()) <= MAX_DECISION_BYTES)

        vague_authorization = authorize_action_proposal_execution(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_decision_digest=approval_decision_digest,
            explicit_operator_text="Go ahead.",
            operator_authority="operator",
            operation_id="checkpoint-operation-identity",
            now=108,
        )
        wrong_actor_authorization = authorize_action_proposal_execution(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_decision_digest=approval_decision_digest,
            explicit_operator_text=f"Authorize execution for proposal {proposal_id}.",
            operator_authority="assistant",
            operation_id="checkpoint-operation-identity",
            now=109,
        )
        missing_operation = authorize_action_proposal_execution(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_decision_digest=approval_decision_digest,
            explicit_operator_text=f"Authorize execution for proposal {proposal_id}.",
            operator_authority="operator",
            operation_id="",
            now=110,
        )
        wrong_decision_digest_authorization = authorize_action_proposal_execution(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_decision_digest="0" * 64,
            explicit_operator_text=f"Authorize execution for proposal {proposal_id}.",
            operator_authority="operator",
            operation_id="checkpoint-operation-identity",
            now=111,
        )
        admitted = authorize_action_proposal_execution(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_decision_digest=approval_decision_digest,
            explicit_operator_text=f"Authorize execution for proposal {proposal_id}.",
            operator_authority="operator",
            operation_id="checkpoint-operation-identity",
            now=112,
        )
        replayed_admission = authorize_action_proposal_execution(
            ledger,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            approval_decision_digest=approval_decision_digest,
            explicit_operator_text=f"Authorize execution for proposal {proposal_id}.",
            operator_authority="operator",
            operation_id="checkpoint-operation-identity",
            now=113,
        )
        require(not vague_authorization.get("ok") and not vague_authorization.get("authorization_granted"))
        require(not wrong_actor_authorization.get("ok"))
        require(not missing_operation.get("ok"))
        require("operation_identity_required" in list(missing_operation.get("reason_codes") or []))
        require(not wrong_decision_digest_authorization.get("ok"))
        require(admitted.get("ok") and admitted.get("state") == "execution_admitted")
        require(admitted.get("authorization_granted") and admitted.get("execution_admitted"))
        require(not admitted.get("execution_performed") and not admitted.get("executor_invoked"))
        require(admitted.get("conversation_can_authorize") is False)
        require(admitted.get("conversation_can_execute") is False)
        require(admitted.get("automatic_authorization_allowed") is False)
        require(admitted.get("content_free"))
        require(len(str(admitted.get("authorization_digest") or "")) == 64)
        require(len(str(admitted.get("operation_digest") or "")) == 64)
        require(len(str(admitted.get("execution_admission_digest") or "")) == 64)
        require(len(json.dumps(admitted, sort_keys=True, separators=(",", ":")).encode()) <= ADMISSION_MAX_RECEIPT_BYTES)
        require(not replayed_admission.get("ok") and replayed_admission.get("state") == "replayed")

        inspection = inspect_persisted_action_proposals(ledger, now=114)
        raw = ledger.read_text(encoding="utf-8")
        require(inspection.get("record_count") == 1)
        require((inspection.get("state_counts") or {}).get("execution_admitted") == 1)
        require(inspection.get("raw_content_exposed") is False)
        require(inspection.get("argument_values_exposed") is False)
        require(len(raw.encode("utf-8")) < 16384)
        require("Run diagnostics" not in raw)
        require("Go ahead" not in raw)
        require("checkpoint-operation-identity" not in raw)
        require("Request approval for diagnostics" not in raw)
        require(f"Approve proposal {proposal_id}" not in raw)
        require(f"Authorize execution for proposal {proposal_id}" not in raw)
        require('"execution_performed":false' in raw)
        require('"raw_content_stored":false' in raw)
        require('"argument_values_stored":false' in raw)

        # Rejection remains terminal and cannot become execution admission.
        reject_ledger = temp / "reject-ledger.json"
        reject_saved = persist_action_proposal(
            reject_ledger, handoff, expected_proposal_digest=proposal_digest, now=200,
        )
        reject_request = request_action_proposal_approval(
            reject_ledger,
            proposal_id=str(reject_saved.get("proposal_id") or ""),
            proposal_digest=proposal_digest,
            explicit_control_text="Request approval for diagnostics.",
            now=201,
        )
        rejected = decide_action_proposal(
            reject_ledger,
            proposal_id=str(reject_saved.get("proposal_id") or ""),
            proposal_digest=proposal_digest,
            approval_request_digest=str(reject_request.get("approval_request_digest") or ""),
            explicit_operator_text=f"Reject proposal {reject_saved.get('proposal_id')}.",
            operator_authority="operator",
            now=202,
        )
        rejected_admission = authorize_action_proposal_execution(
            reject_ledger,
            proposal_id=str(reject_saved.get("proposal_id") or ""),
            proposal_digest=proposal_digest,
            approval_decision_digest=str(rejected.get("approval_decision_digest") or ""),
            explicit_operator_text=f"Authorize execution for proposal {reject_saved.get('proposal_id')}.",
            operator_authority="operator",
            operation_id="rejected-operation",
            now=203,
        )
        require(rejected.get("ok") and rejected.get("state") == "rejected")
        require(not rejected.get("approval_granted"))
        require(not rejected_admission.get("ok") and rejected_admission.get("state") == "rejected")
        require(not rejected_admission.get("execution_admitted"))

        # Expired proposals and malformed state fail closed.
        expired_ledger = temp / "expired-ledger.json"
        expired_saved = persist_action_proposal(
            expired_ledger, handoff, expected_proposal_digest=proposal_digest, now=0,
        )
        expired_request = request_action_proposal_approval(
            expired_ledger,
            proposal_id=str(expired_saved.get("proposal_id") or ""),
            proposal_digest=proposal_digest,
            explicit_control_text="Request approval for diagnostics.",
            now=MAX_AGE_SECONDS + 1,
        )
        require(not expired_request.get("ok") and expired_request.get("state") == "expired")

        malformed_ledger = temp / "malformed-ledger.json"
        malformed_ledger.write_text("{not-json", encoding="utf-8")
        malformed_inspection = inspect_persisted_action_proposals(malformed_ledger)
        require(malformed_inspection.get("record_count") == 0)

        # Registered but non-execution-eligible source changes remain blocked.
        patch_projection = build_natural_language_action_projection("Change dashboard.py.")
        patch_handoff = build_action_proposal_handoff(
            patch_projection, operation_id="checkpoint-patch-candidate",
        )
        patch_proposal = dict(patch_handoff.get("proposal") or {})
        patch_digest = str(patch_proposal.get("proposal_digest") or "")
        patch_ledger = temp / "patch-ledger.json"
        patch_saved = persist_action_proposal(
            patch_ledger, patch_handoff, expected_proposal_digest=patch_digest, now=300,
        )
        patch_request = request_action_proposal_approval(
            patch_ledger,
            proposal_id=str(patch_saved.get("proposal_id") or ""),
            proposal_digest=patch_digest,
            explicit_control_text="Request approval for patch_proposal.",
            now=301,
        )
        patch_approved = decide_action_proposal(
            patch_ledger,
            proposal_id=str(patch_saved.get("proposal_id") or ""),
            proposal_digest=patch_digest,
            approval_request_digest=str(patch_request.get("approval_request_digest") or ""),
            explicit_operator_text=f"Approve proposal {patch_saved.get('proposal_id')}.",
            operator_authority="operator",
            now=302,
        )
        patch_admission = authorize_action_proposal_execution(
            patch_ledger,
            proposal_id=str(patch_saved.get("proposal_id") or ""),
            proposal_digest=patch_digest,
            approval_decision_digest=str(patch_approved.get("approval_decision_digest") or ""),
            explicit_operator_text=f"Authorize execution for proposal {patch_saved.get('proposal_id')}.",
            operator_authority="operator",
            operation_id="checkpoint-patch-operation",
            now=303,
        )
        require(patch_proposal.get("capability_id") == "patch_proposal")
        require(patch_saved.get("ok") and patch_approved.get("approval_granted"))
        require(not patch_admission.get("ok"))
        require("capability_not_execution_eligible" in list(patch_admission.get("reason_codes") or []))
        require(not patch_admission.get("execution_admitted") and not patch_admission.get("execution_performed"))

        lifecycle_evidence = {
            "proposal": _bounded_result(saved),
            "duplicate": _bounded_result(duplicate),
            "approval_request": _bounded_result(approval_request),
            "approval_decision": _bounded_result(approved),
            "execution_admission": _bounded_result(admitted),
            "replay": _bounded_result(replayed_admission),
            "rejection": _bounded_result(rejected),
            "rejected_admission": _bounded_result(rejected_admission),
            "expired": _bounded_result(expired_request),
            "malformed_record_count": int(malformed_inspection.get("record_count") or 0),
            "patch_admission": _bounded_result(patch_admission),
            "state_counts": dict(inspection.get("state_counts") or {}),
            "ledger_record_count": int(inspection.get("record_count") or 0),
        }

    # Ordinary conversation may project understanding but cannot touch governance state.
    runtime_source = (source / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    parity_counts = {
        "routing_build_count": runtime_source.count("build_natural_language_action_projection("),
        "routing_public_count": runtime_source.count("natural_language_action_public_projection(action_projection)"),
        "proposal_persist_call_count": runtime_source.count("persist_action_proposal("),
        "approval_request_call_count": runtime_source.count("request_action_proposal_approval("),
        "approval_decision_call_count": runtime_source.count("decide_action_proposal("),
        "authorization_call_count": runtime_source.count("authorize_action_proposal_execution("),
        "executor_call_count": runtime_source.count("execute_supervised_action("),
    }
    require(parity_counts["routing_build_count"] == 2)
    require(parity_counts["routing_public_count"] == 2)
    require(parity_counts["proposal_persist_call_count"] == 0)
    require(parity_counts["approval_request_call_count"] == 0)
    require(parity_counts["approval_decision_call_count"] == 0)
    require(parity_counts["authorization_call_count"] == 0)
    require(parity_counts["executor_call_count"] == 0)

    proposal_source = (source / "conscious_agent" / "persisted_action_proposals.py").read_text(encoding="utf-8")
    decision_source = (source / "conscious_agent" / "action_proposal_approval_decisions.py").read_text(encoding="utf-8")
    admission_source = (source / "conscious_agent" / "action_execution_admission.py").read_text(encoding="utf-8")
    source_contract = {
        "proposal_contract": PROPOSAL_CONTRACT_VERSION,
        "decision_contract": DECISION_CONTRACT_VERSION,
        "admission_contract": ADMISSION_CONTRACT_VERSION,
        "approval_manager_call_count": (
            proposal_source.count("approval_manager(")
            + decision_source.count("approval_manager(")
            + admission_source.count("approval_manager(")
        ),
        "executor_call_count": admission_source.count("execute_supervised_action("),
        "maximum_records": MAX_RECORDS,
        "maximum_record_bytes": MAX_RECORD_BYTES,
        "maximum_age_seconds": MAX_AGE_SECONDS,
    }
    require(source_contract["proposal_contract"] == "v1177.8")
    require(source_contract["decision_contract"] == "v1177.5")
    require(source_contract["admission_contract"] == "v1177.8")
    require(source_contract["approval_manager_call_count"] == 0)
    require(source_contract["executor_call_count"] == 0)
    require(source_contract["maximum_records"] == 64)
    require(source_contract["maximum_record_bytes"] == 3072)
    require(source_contract["maximum_age_seconds"] == 7 * 86400)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next(
        (
            row for row in registry.get("checkpoints", [])
            if row.get("checkpoint_id") == "natural-language-action-approval-governance-checkpoint"
        ),
        None,
    )
    privacy = package_privacy_summary_for_root(source)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_natural_language_action_approval_governance_checkpoint")
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))
    require(privacy.get("forbidden_entry_count", 0) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)
    require(source_before == _tree_signature(source))
    require(runtime_before == _tree_signature(runtime))

    evidence = {
        "prior_checkpoints": {
            "action": {
                "ok": bool(prior_action.get("ok")),
                "passed": int(prior_action.get("passed") or 0),
                "total": int(prior_action.get("total") or 0),
            },
            "clarification": {
                "ok": bool(prior_clarification.get("ok")),
                "passed": int(prior_clarification.get("passed") or 0),
                "total": int(prior_clarification.get("total") or 0),
            },
        },
        "lifecycle": lifecycle_evidence,
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
        "natural_language_action_approval_governance_checkpoint_completed": True,
        "intent_clarification_proposal_approval_authorization_admission_consolidated": True,
        "synthetic_proposal_lifecycle_exercised": True,
        "conversation_governance_mutation_blocked": True,
        "raw_request_persisted": False,
        "raw_argument_values_persisted": False,
        "raw_operation_identity_persisted": False,
        "automatic_proposal_persistence": False,
        "automatic_approval_requested": False,
        "automatic_approval_created": False,
        "approval_implies_authorization": False,
        "conversation_authorization_granted": False,
        "conversation_execution_admitted": False,
        "conversation_action_executed": False,
        "executor_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "source_edit_performed": False,
        "runtime_mutated": False,
        "memory_mutated": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "source_modified": source_before != _tree_signature(source),
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "retained_checkpoint_count": 2,
            "lifecycle_case_count": 11,
            "governed_transition_count": 4,
            "negative_boundary_case_count": 12,
            "terminal_state_case_count": 4,
            "conversation_governance_call_count": sum(
                parity_counts[key]
                for key in (
                    "proposal_persist_call_count",
                    "approval_request_call_count",
                    "approval_decision_call_count",
                    "authorization_call_count",
                    "executor_call_count",
                )
            ),
            "maximum_proposal_records": MAX_RECORDS,
            "maximum_proposal_record_bytes": MAX_RECORD_BYTES,
            "maximum_proposal_age_seconds": MAX_AGE_SECONDS,
            "maximum_decision_receipt_bytes": MAX_DECISION_BYTES,
            "maximum_admission_receipt_bytes": ADMISSION_MAX_RECEIPT_BYTES,
            "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", 0)),
            "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0)),
            "open_limitation_count": 4,
        },
        "evidence": evidence,
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
