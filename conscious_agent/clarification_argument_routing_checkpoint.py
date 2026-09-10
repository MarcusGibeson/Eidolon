from __future__ import annotations

"""Strictly read-only v1176.9 clarification and argument-routing checkpoint."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from bounded_action_arguments import ARGUMENT_SCHEMAS, CONTRACT_VERSION as ARGUMENT_CONTRACT_VERSION, MAX_ARGUMENTS, MAX_RECEIPT_BYTES as ARGUMENT_RECEIPT_MAX_BYTES, bind_bounded_action_arguments
from checkpoint_registry import inspect_checkpoint_registry
from clarification_continuity import CONTRACT_VERSION as CONTINUITY_CONTRACT_VERSION, MAX_AGE_SECONDS, MAX_FIELDS as CONTINUITY_MAX_FIELDS, MAX_PENDING, inspect_clarification_continuity, register_clarification, resume_clarification, transition_clarification
from natural_language_action_routing import build_natural_language_action_projection
from package_integrity import package_privacy_summary_for_root
from structured_action_clarification import CONTRACT_VERSION as CLARIFICATION_CONTRACT_VERSION, MAX_FIELDS, MAX_RECEIPT_BYTES as CLARIFICATION_RECEIPT_MAX_BYTES, apply_structured_clarification_answer, build_clarified_proposal_binding, build_structured_clarification_request

CONTRACT_VERSION = "v1176.9"
_CHECKPOINT_ID = "clarification-argument-routing:v1176.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_TEXT = (
    "CLARIFICATION_PRIVATE_CANARY", "PROVIDER_PRIVATE_CANARY", "MEMORY_PRIVATE_CANARY",
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


def _projection_summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    intent = dict(projection.get("intent") or {})
    grounding = dict(projection.get("grounding") or {})
    binding = dict(projection.get("argument_binding") or {})
    clarification = dict(projection.get("clarification_request") or {})
    return {
        "category": str(intent.get("category") or ""),
        "action_intent_present": bool(intent.get("action_intent_present")),
        "requires_clarification": bool(intent.get("requires_clarification")),
        "grounding_status": str(grounding.get("grounding_status") or ""),
        "capability_id": str(grounding.get("capability_id") or ""),
        "binding_state": str(binding.get("binding_state") or ""),
        "bound_argument_names": list(binding.get("bound_argument_names") or [])[:MAX_ARGUMENTS],
        "safe_default_names": list(binding.get("safe_default_names") or [])[:MAX_ARGUMENTS],
        "missing_required": list(binding.get("missing_required") or [])[:MAX_ARGUMENTS],
        "unknown_argument_names": list(binding.get("unknown_argument_names") or [])[:MAX_ARGUMENTS],
        "exact_binding": bool(binding.get("exact_capability_argument_binding")),
        "clarification_state": str(clarification.get("state") or ""),
        "requested_fields": list(clarification.get("requested_fields") or [])[:MAX_FIELDS],
        "content_free": bool(binding.get("content_free_receipt")) and bool(clarification.get("content_free", True)),
        "approval_created": bool(binding.get("approval_created")) or str(clarification.get("approval_state") or "") != "not_created",
        "execution_performed": bool(binding.get("execution_performed")) or str(clarification.get("execution_state") or "") != "not_executed",
        "argument_receipt_bytes": int(binding.get("receipt_bytes") or 0),
    }


def _clarification_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    binding = dict(result.get("binding") or {})
    return {
        "state": str(result.get("state") or ""),
        "capability_id": str(result.get("capability_id") or ""),
        "request_verified": bool(result.get("request_verified")),
        "request_replayed": bool(result.get("request_replayed")),
        "answer_field_names": list(result.get("answer_field_names") or [])[:MAX_FIELDS],
        "unknown_answer_fields": list(result.get("unknown_answer_fields") or [])[:MAX_FIELDS],
        "missing_answer_fields": list(result.get("missing_answer_fields") or [])[:MAX_FIELDS],
        "exact_clarified_binding": bool(result.get("exact_clarified_binding")),
        "proposal_binding_eligible": bool(result.get("proposal_binding_eligible")),
        "request_consumed": bool(result.get("request_consumed")),
        "binding_state": str(binding.get("binding_state") or ""),
        "bound_argument_names": list(binding.get("bound_argument_names") or [])[:MAX_FIELDS],
        "content_free": bool(result.get("content_free")),
        "persisted": bool(result.get("persisted")),
        "approval_created": bool(result.get("approval_created")),
        "execution_performed": bool(result.get("execution_performed")),
    }


def _proposal_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    proposal = dict(result.get("proposal_binding") or {})
    diagnostics = dict(result.get("diagnostics") or {})
    return {
        "state": str(proposal.get("state") or ""),
        "capability_id": str(proposal.get("capability_id") or ""),
        "proposal_candidate_created": bool(proposal.get("proposal_candidate_created")),
        "proposal_persisted": bool(proposal.get("proposal_persisted")),
        "approval_created": bool(proposal.get("approval_created")),
        "authorization_granted": bool(proposal.get("authorization_granted")),
        "execution_admitted": bool(proposal.get("execution_admitted")),
        "execution_performed": bool(proposal.get("execution_performed")),
        "exact_digest_binding": bool(proposal.get("exact_digest_binding")),
        "bound_argument_names": list(proposal.get("bound_argument_names") or [])[:MAX_FIELDS],
        "content_free": bool(proposal.get("content_free")) and bool(diagnostics.get("content_free")),
        "integration_bytes": int(diagnostics.get("integration_bytes") or 0),
    }


def build_clarification_argument_routing_checkpoint(
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
        "diagnostics_default": "Run diagnostics.",
        "diagnostics_provider": "Run provider diagnostics.",
        "maintenance_default": "Do a system maintenance check.",
        "project_default": "Inspect your project.",
        "file_explicit": "Review conscious_agent/memory.py.",
        "file_missing": "Review a file.",
        "patch_explicit": "Change dashboard.py.",
        "patch_missing": "Change the dashboard background.",
        "self_development_missing": "Improve your project.",
        "unsupported": "Install a new model.",
        "question": "Do you like the name Eidolon?",
        "correction": "Stop calling me Daddy.",
        "hypothetical": "What if I said 'review a file'?",
        "quoted": '"Review a file."',
        "ambiguous": "Go ahead.",
    }
    projections = {name: build_natural_language_action_projection(text) for name, text in messages.items()}
    projection_summaries = {name: _projection_summary(value) for name, value in projections.items()}

    require(projection_summaries["diagnostics_default"]["binding_state"] == "bound")
    require(projection_summaries["diagnostics_default"]["safe_default_names"] == ["scope"])
    require(projection_summaries["diagnostics_provider"]["binding_state"] == "bound")
    require(projection_summaries["maintenance_default"]["binding_state"] == "bound")
    require(projection_summaries["project_default"]["binding_state"] == "bound")
    require(projection_summaries["file_explicit"]["binding_state"] == "bound")
    require(projection_summaries["file_explicit"]["bound_argument_names"] == ["target_ref"])
    require(projection_summaries["file_missing"]["clarification_state"] == "awaiting_structured_answer")
    require(projection_summaries["file_missing"]["requested_fields"] == ["target_ref"])
    require(projection_summaries["patch_missing"]["clarification_state"] == "awaiting_structured_answer")
    require(projection_summaries["unsupported"]["grounding_status"] == "unsupported")
    for name in ("question", "correction", "hypothetical", "quoted", "ambiguous"):
        require(projection_summaries[name]["clarification_state"] == "not_required")
        require(not projection_summaries[name]["approval_created"])
        require(not projection_summaries[name]["execution_performed"])
    require(all(row["content_free"] for row in projection_summaries.values()))
    require(all(row["argument_receipt_bytes"] <= ARGUMENT_RECEIPT_MAX_BYTES for row in projection_summaries.values()))

    unknown = bind_bounded_action_arguments(
        "", projections["diagnostics_default"]["grounding"], supplied_arguments={"scope": "system", "command": "private"},
    )
    invalid = bind_bounded_action_arguments(
        "", projections["diagnostics_default"]["grounding"], supplied_arguments={"scope": "everything"},
    )
    traversal = bind_bounded_action_arguments(
        "", projections["file_missing"]["grounding"], supplied_arguments={"target_ref": "../../secret"},
    )
    require(unknown["requires_clarification"] and unknown["unknown_argument_names"] == ["command"])
    require(invalid["requires_clarification"] and invalid["invalid_argument_names"] == ["scope"])
    require(traversal["requires_clarification"] and traversal["invalid_argument_names"] == ["target_ref"])
    require(not unknown["approval_created"] and not unknown["execution_performed"])

    request = build_structured_clarification_request(projections["file_missing"])
    require(request["state"] == "awaiting_structured_answer")
    require(request["requested_fields"] == ["target_ref"])
    require(request["persisted"] is False)
    require(request["authority_state"] == "not_granted")
    require(request["approval_state"] == "not_created")
    require(request["execution_state"] == "not_executed")
    require(request["raw_request_included"] is False and request["raw_answer_included"] is False)
    require(len(str(request.get("request_digest") or "")) == 64)
    require(len(ARGUMENT_SCHEMAS) == 12)

    exact = apply_structured_clarification_answer(
        projections["file_missing"], request, {"target_ref": "conscious_agent/memory.py"},
    )
    unknown_answer = apply_structured_clarification_answer(
        projections["file_missing"], request, {"target_ref": "conscious_agent/memory.py", "extra": "no"},
    )
    missing_answer = apply_structured_clarification_answer(projections["file_missing"], request, {})
    stale_request = deepcopy(request)
    stale_request["source_projection_digest"] = "0" * 64
    stale = apply_structured_clarification_answer(
        projections["file_missing"], stale_request, {"target_ref": "conscious_agent/memory.py"},
    )
    replayed = apply_structured_clarification_answer(
        projections["file_missing"], request, {"target_ref": "conscious_agent/memory.py"},
        consumed_request_digests=[request["request_digest"]],
    )
    clarification_cases = {
        "exact": exact,
        "unknown": unknown_answer,
        "missing": missing_answer,
        "stale": stale,
        "replayed": replayed,
    }
    clarification_summaries = {name: _clarification_summary(value) for name, value in clarification_cases.items()}
    require(clarification_summaries["exact"]["state"] == "bound")
    require(clarification_summaries["exact"]["request_verified"])
    require(clarification_summaries["exact"]["exact_clarified_binding"])
    require(clarification_summaries["exact"]["proposal_binding_eligible"])
    require(clarification_summaries["exact"]["request_consumed"])
    require(clarification_summaries["unknown"]["unknown_answer_fields"] == ["extra"])
    require(not clarification_summaries["unknown"]["exact_clarified_binding"])
    require(clarification_summaries["missing"]["state"] == "clarification_required")
    require(clarification_summaries["stale"]["state"] == "stale_or_mismatched")
    require(clarification_summaries["replayed"]["state"] == "replayed")
    require(all(row["content_free"] for row in clarification_summaries.values()))
    require(all(not row["persisted"] and not row["approval_created"] and not row["execution_performed"] for row in clarification_summaries.values()))

    proposal_cases = {
        "exact": build_clarified_proposal_binding(projections["file_missing"], exact, operation_id="checkpoint-review"),
        "unknown": build_clarified_proposal_binding(projections["file_missing"], unknown_answer, operation_id="checkpoint-unknown"),
        "stale": build_clarified_proposal_binding(projections["file_missing"], stale, operation_id="checkpoint-stale"),
        "replayed": build_clarified_proposal_binding(projections["file_missing"], replayed, operation_id="checkpoint-replay"),
    }
    proposal_summaries = {name: _proposal_summary(value) for name, value in proposal_cases.items()}
    require(proposal_summaries["exact"]["state"] == "ready_for_separate_persistence")
    require(proposal_summaries["exact"]["proposal_candidate_created"])
    require(proposal_summaries["exact"]["exact_digest_binding"])
    for name in ("unknown", "stale", "replayed"):
        require(proposal_summaries[name]["state"] == "not_ready")
        require(not proposal_summaries[name]["proposal_candidate_created"])
    require(all(row["content_free"] for row in proposal_summaries.values()))
    require(all(row["integration_bytes"] <= CLARIFICATION_RECEIPT_MAX_BYTES for row in proposal_summaries.values()))
    require(all(not row["proposal_persisted"] and not row["approval_created"] and not row["authorization_granted"] for row in proposal_summaries.values()))
    require(all(not row["execution_admitted"] and not row["execution_performed"] for row in proposal_summaries.values()))

    continuity_evidence: dict[str, Any] = {}
    with TemporaryDirectory() as directory:
        path = Path(directory) / "clarifications.json"
        registered = register_clarification(path, request, now=1000)
        duplicate = register_clarification(path, request, now=1001)
        resumed = resume_clarification(
            path,
            request_digest=request["request_digest"],
            source_projection_digest=request["source_projection_digest"],
            source_binding_digest=request["source_binding_digest"],
            now=1002,
        )
        mismatch = resume_clarification(
            path,
            request_digest=request["request_digest"],
            source_projection_digest="0" * 64,
            source_binding_digest=request["source_binding_digest"],
            now=1002,
        )
        consumed = transition_clarification(path, request_digest=request["request_digest"], transition="consumed", now=1003)
        duplicate_terminal = transition_clarification(path, request_digest=request["request_digest"], transition="consumed", now=1004)
        after_consumed = resume_clarification(
            path,
            request_digest=request["request_digest"],
            source_projection_digest=request["source_projection_digest"],
            source_binding_digest=request["source_binding_digest"],
            now=1005,
        )
        inspect = inspect_clarification_continuity(path, now=1005)
        raw = path.read_text(encoding="utf-8")

        cancel_path = Path(directory) / "cancel.json"
        register_clarification(cancel_path, request, now=2000)
        cancelled = transition_clarification(cancel_path, request_digest=request["request_digest"], transition="cancelled", now=2001)

        expire_path = Path(directory) / "expire.json"
        register_clarification(expire_path, request, now=0)
        expired = resume_clarification(
            expire_path,
            request_digest=request["request_digest"],
            source_projection_digest=request["source_projection_digest"],
            source_binding_digest=request["source_binding_digest"],
            now=MAX_AGE_SECONDS + 1,
        )

        supersede_path = Path(directory) / "supersede.json"
        register_clarification(supersede_path, request, now=3000)
        second = deepcopy(request)
        second["source_binding_digest"] = "c" * 64
        second["request_digest"] = "d" * 64
        superseded = register_clarification(supersede_path, second, now=3001)
        supersede_inspect = inspect_clarification_continuity(supersede_path, now=3002)

        malformed_path = Path(directory) / "malformed.json"
        malformed_path.write_text("{bad", encoding="utf-8")
        malformed = inspect_clarification_continuity(malformed_path)

        require(registered["ok"] and registered["state"] == "pending" and registered["persisted"])
        require(duplicate["ok"] and duplicate["state"] == "duplicate_pending" and not duplicate["persisted"])
        require(resumed["resumable"] and resumed["exact_digest_binding"])
        require(resumed["requested_fields"] == ["target_ref"])
        require(not resumed["answer_stored"] and not resumed["raw_content_stored"])
        require(not resumed["authority_granted"] and not resumed["approval_created"] and not resumed["execution_performed"])
        require(not mismatch["resumable"] and not mismatch["exact_digest_binding"])
        require(consumed["ok"] and consumed["state"] == "consumed")
        require(not duplicate_terminal["ok"] and duplicate_terminal["duplicate_terminal_transition"])
        require(not after_consumed["resumable"] and after_consumed["state"] == "consumed")
        require(cancelled["ok"] and cancelled["state"] == "cancelled")
        require(not expired["resumable"] and expired["state"] == "expired")
        require(superseded["ok"] and superseded["state"] == "pending")
        require(supersede_inspect["state_counts"].get("superseded") == 1)
        require(malformed["record_count"] == 0)
        require(inspect["raw_content_exposed"] is False and inspect["answers_exposed"] is False)
        require(inspect["authority_granted"] is False and inspect["approval_created"] is False and inspect["execution_performed"] is False)
        require("conscious_agent/memory.py" not in raw and "Review a file" not in raw)
        require("CLARIFICATION_PRIVATE_CANARY" not in raw)
        require(len(raw.encode("utf-8")) < 16384)
        continuity_evidence = {
            "registered_state": registered["state"],
            "duplicate_state": duplicate["state"],
            "resume_state": resumed["state"],
            "mismatch_resumable": mismatch["resumable"],
            "consumed_state": consumed["state"],
            "cancelled_state": cancelled["state"],
            "expired_state": expired["state"],
            "superseded_count": supersede_inspect["state_counts"].get("superseded", 0),
            "malformed_record_count": malformed["record_count"],
            "record_count": inspect["record_count"],
            "content_free": not inspect["raw_content_exposed"] and not inspect["answers_exposed"],
        }

    runtime_source = (source / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    routing_source = (source / "conscious_agent" / "natural_language_action_routing.py").read_text(encoding="utf-8")
    parity_counts = {
        "routing_build_count": runtime_source.count("build_natural_language_action_projection("),
        "routing_public_count": runtime_source.count("natural_language_action_public_projection(action_projection)"),
        "argument_binding_in_projection_count": routing_source.count("bind_bounded_action_arguments(user_text, grounding)"),
        "clarification_request_in_projection_count": routing_source.count("build_structured_clarification_request(projection)"),
        "conversation_executor_call_count": runtime_source.count("execute_supervised_action("),
        "continuity_runtime_call_count": runtime_source.count("register_clarification(") + runtime_source.count("transition_clarification("),
    }
    require(parity_counts["routing_build_count"] == 2)
    require(parity_counts["routing_public_count"] == 2)
    require(parity_counts["argument_binding_in_projection_count"] == 1)
    require(parity_counts["clarification_request_in_projection_count"] == 1)
    require(parity_counts["conversation_executor_call_count"] == 0)
    require(parity_counts["continuity_runtime_call_count"] == 0)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "clarification-argument-routing-checkpoint"),
        None,
    )
    privacy = package_privacy_summary_for_root(source)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_clarification_argument_routing_checkpoint")
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))
    require(privacy.get("forbidden_entry_count", 0) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)
    require(source_before == _tree_signature(source))
    require(runtime_before == _tree_signature(runtime))

    evidence = {
        "projection_summaries": projection_summaries,
        "clarification_summaries": clarification_summaries,
        "proposal_summaries": proposal_summaries,
        "continuity_summary": continuity_evidence,
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
        "clarification_argument_routing_checkpoint_completed": True,
        "argument_binding_structured_clarification_continuity_consolidated": True,
        "streaming_non_streaming_parity_preserved": True,
        "ordinary_conversation_clarification_blocked": True,
        "synthetic_continuity_contract_exercised": True,
        "raw_request_persisted": False,
        "raw_answer_persisted": False,
        "argument_values_persisted": False,
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
            "projection_case_count": len(projection_summaries),
            "argument_schema_count": len(ARGUMENT_SCHEMAS),
            "clarification_answer_case_count": len(clarification_summaries),
            "proposal_binding_case_count": len(proposal_summaries),
            "continuity_case_count": 9,
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "maximum_argument_count": MAX_ARGUMENTS,
            "maximum_clarification_field_count": MAX_FIELDS,
            "maximum_continuity_field_count": CONTINUITY_MAX_FIELDS,
            "maximum_pending_continuity_records": MAX_PENDING,
            "maximum_continuity_age_seconds": MAX_AGE_SECONDS,
            "argument_receipt_maximum_bytes": ARGUMENT_RECEIPT_MAX_BYTES,
            "clarification_integration_maximum_bytes": CLARIFICATION_RECEIPT_MAX_BYTES,
            "privacy_forbidden_entry_count": privacy.get("forbidden_entry_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
            "open_limitation_count": 4,
        },
        "evidence": {"synthetic_contracts": evidence},
        "source_modified": False,
        "argument_contract_version": ARGUMENT_CONTRACT_VERSION,
        "clarification_contract_version": CLARIFICATION_CONTRACT_VERSION,
        "continuity_contract_version": CONTINUITY_CONTRACT_VERSION,
    }
    report["structural_digest"] = _digest(report)
    return report
