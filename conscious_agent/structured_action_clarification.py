from __future__ import annotations

"""Structured clarification and exact proposal-binding integration.

Clarification requests and answers are content-free, allowlisted, digest-bound,
and authority-free. This module never persists a proposal, creates approval, or
executes a capability.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from bounded_action_arguments import ARGUMENT_SCHEMAS, bind_bounded_action_arguments
from action_proposal_handoff import build_action_proposal_handoff

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1176.5"
MAX_FIELDS = 4
MAX_RECEIPT_BYTES = 4096
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _bounded_digest(value: Any) -> str:
    text = str(value or "")
    return text if _DIGEST.fullmatch(text) else ""


def build_structured_clarification_request(action_projection: Mapping[str, Any]) -> dict[str, Any]:
    grounding = dict(action_projection.get("grounding") or {})
    binding = dict(action_projection.get("argument_binding") or {})
    capability_id = str(grounding.get("capability_id") or "")
    schema = ARGUMENT_SCHEMAS.get(capability_id, {})
    allowed = dict(schema.get("allowed") or {})
    requested = list(dict.fromkeys(
        list(binding.get("missing_required") or []) + list(binding.get("invalid_argument_names") or [])
    ))[:MAX_FIELDS]
    requested = [name for name in requested if name in allowed]
    eligible = bool(
        grounding.get("grounding_status") == "matched"
        and binding.get("requires_clarification") is True
        and requested
    )
    request = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "state": "awaiting_structured_answer" if eligible else "not_required",
        "capability_id": capability_id if eligible else "",
        "requested_fields": requested if eligible else [],
        "allowed_value_hints": {
            name: list(allowed[name].get("values") or ())[:8]
            for name in requested if allowed[name].get("values")
        },
        "source_projection_digest": _bounded_digest(action_projection.get("projection_digest")),
        "source_binding_digest": _bounded_digest(binding.get("binding_digest")),
        "answer_state": "not_received",
        "persisted": False,
        "authority_state": "not_granted",
        "approval_state": "not_created",
        "execution_state": "not_executed",
        "content_free": True,
        "raw_request_included": False,
        "raw_answer_included": False,
    }
    request["request_digest"] = _digest({k: v for k, v in request.items() if k != "request_digest"})
    return request


def apply_structured_clarification_answer(
    action_projection: Mapping[str, Any],
    clarification_request: Mapping[str, Any],
    answer: Mapping[str, Any] | None,
    *,
    consumed_request_digests: Iterable[str] = (),
) -> dict[str, Any]:
    request = dict(clarification_request or {})
    grounding = dict(action_projection.get("grounding") or {})
    original_binding = dict(action_projection.get("argument_binding") or {})
    capability_id = str(grounding.get("capability_id") or "")
    request_digest = _bounded_digest(request.get("request_digest"))
    expected = build_structured_clarification_request(action_projection)
    expected_digest = str(expected.get("request_digest") or "")
    replayed = bool(request_digest and request_digest in {str(v) for v in consumed_request_digests})
    exact_request = bool(
        request_digest
        and request_digest == expected_digest
        and request.get("state") == "awaiting_structured_answer"
        and request.get("capability_id") == capability_id
        and request.get("source_projection_digest") == action_projection.get("projection_digest")
        and request.get("source_binding_digest") == original_binding.get("binding_digest")
    )
    supplied = dict(answer or {})
    requested_fields = list(request.get("requested_fields") or [])[:MAX_FIELDS]
    unknown = sorted(str(k)[:80] for k in supplied if k not in requested_fields)[:MAX_FIELDS]
    missing = [name for name in requested_fields if name not in supplied]
    answer_eligible = bool(exact_request and not replayed and supplied and not unknown and not missing)
    rebound = bind_bounded_action_arguments("", grounding, supplied_arguments=supplied if answer_eligible else {})
    exact_binding = bool(answer_eligible and rebound.get("exact_capability_argument_binding"))
    state = "bound" if exact_binding else (
        "replayed" if replayed else
        "stale_or_mismatched" if not exact_request else
        "clarification_required"
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "state": state,
        "capability_id": capability_id if exact_request else "",
        "request_digest": request_digest,
        "request_verified": exact_request,
        "request_replayed": replayed,
        "answer_field_names": sorted(supplied)[:MAX_FIELDS] if answer_eligible else [],
        "unknown_answer_fields": unknown,
        "missing_answer_fields": missing,
        "binding": rebound,
        "exact_clarified_binding": exact_binding,
        "proposal_binding_eligible": exact_binding,
        "request_consumed": exact_binding,
        "persisted": False,
        "authorization_inferred": False,
        "approval_created": False,
        "execution_admitted": False,
        "execution_performed": False,
        "raw_answer_included": False,
        "content_free": True,
    }
    result["clarification_digest"] = _digest({k: v for k, v in result.items() if k != "clarification_digest"})
    return result


def build_clarified_proposal_binding(
    action_projection: Mapping[str, Any],
    clarification_result: Mapping[str, Any],
    *,
    operation_id: str = "",
) -> dict[str, Any]:
    clarification = dict(clarification_result or {})
    binding = dict(clarification.get("binding") or {})
    eligible = bool(
        clarification.get("exact_clarified_binding") is True
        and clarification.get("request_verified") is True
        and clarification.get("request_replayed") is False
        and binding.get("exact_capability_argument_binding") is True
        and binding.get("capability_id") == (action_projection.get("grounding") or {}).get("capability_id")
    )
    handoff = build_action_proposal_handoff(action_projection, operation_id=operation_id) if eligible else {}
    proposal = dict(handoff.get("proposal") or {})
    proposal_binding = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "state": "ready_for_separate_persistence" if eligible and proposal.get("proposal_state") == "ready_for_operator_review" else "not_ready",
        "capability_id": str(binding.get("capability_id") or "") if eligible else "",
        "clarification_digest": _bounded_digest(clarification.get("clarification_digest")),
        "argument_binding_digest": _bounded_digest(binding.get("binding_digest")),
        "proposal_digest": _bounded_digest(proposal.get("proposal_digest")),
        "bound_argument_names": list(binding.get("bound_argument_names") or [])[:MAX_FIELDS] if eligible else [],
        "proposal_candidate_created": bool(eligible),
        "proposal_persisted": False,
        "approval_created": False,
        "authorization_granted": False,
        "execution_admitted": False,
        "execution_performed": False,
        "exact_digest_binding": bool(eligible),
        "content_free": True,
        "raw_arguments_included": False,
    }
    proposal_binding["proposal_binding_digest"] = _digest({k: v for k, v in proposal_binding.items() if k != "proposal_binding_digest"})
    result = {
        "proposal_binding": proposal_binding,
        "proposal_handoff": handoff if eligible else {},
        "diagnostics": {
            "existing_proposal_handoff_reused": eligible,
            "new_tool_registry_created": False,
            "proposal_persisted": False,
            "approval_created": False,
            "execution_performed": False,
            "content_free": True,
        },
    }
    result["integration_digest"] = _digest(result)
    size = len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode())
    if size > MAX_RECEIPT_BYTES:
        raise ValueError("Structured clarification proposal binding exceeded size contract")
    result["diagnostics"]["integration_bytes"] = size
    return result
