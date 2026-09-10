from __future__ import annotations

"""v2509 manifest-bound eligibility and action-intent projections.

This module answers whether the evidence required to *consider* an action is
present. It cannot grant approval, admit execution, or invoke an adapter.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from general_capability_manifest_v2509 import validate_capability_manifest

CONTRACT_VERSION = "v2509.4"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def evaluate_capability_eligibility(
    manifest: Mapping[str, Any],
    *,
    evidence_codes: Iterable[str] = (),
    evidence_digests: Iterable[str] = (),
    operator_selection_digest: str = "",
) -> dict[str, Any]:
    validation = validate_capability_manifest(manifest)
    cid = str(manifest.get("capability_id") or "") if validation.get("ok") else ""
    supplied_codes = {str(x or "").strip().lower() for x in evidence_codes or () if str(x or "").strip()}
    required = set(manifest.get("required_evidence_codes") or []) if validation.get("ok") else set()
    digests = sorted({str(x or "").lower() for x in evidence_digests or () if HEX64.fullmatch(str(x or "").lower())})[:32]
    selection = str(operator_selection_digest or "").lower()
    selection_valid = bool(HEX64.fullmatch(selection))
    missing = sorted(required - supplied_codes)
    approval_class = str(manifest.get("approval_class") or "")
    needs_selection = approval_class != "none"
    eligible = bool(validation.get("ok") and not missing and digests and (selection_valid or not needs_selection))
    record = {
        "contract_version": CONTRACT_VERSION,
        "capability_id": cid,
        "manifest_digest": str(manifest.get("manifest_digest") or "") if validation.get("ok") else "",
        "eligible_for_proposal": eligible,
        "missing_evidence_codes": missing,
        "evidence_digest_count": len(digests),
        "operator_selection_bound": selection_valid,
        "approval_class": approval_class if validation.get("ok") else "",
        "execution_admitted": False,
        "approval_granted": False,
        "adapter_invoked": False,
        "external_side_effect_performed": False,
        "authority_inferred": False,
    }
    record["eligibility_digest"] = _digest(record)
    return record


def prepare_general_action_intent(
    *,
    manifest: Mapping[str, Any],
    eligibility: Mapping[str, Any],
    operation_code: str,
    argument_shape_digest: str,
) -> dict[str, Any]:
    if not validate_capability_manifest(manifest).get("ok"):
        raise ValueError("valid_manifest_required")
    if eligibility.get("eligible_for_proposal") is not True:
        raise ValueError("eligible_capability_required")
    if str(eligibility.get("manifest_digest") or "") != str(manifest.get("manifest_digest") or ""):
        raise ValueError("manifest_binding_mismatch")
    op = str(operation_code or "").strip().lower()[:120]
    shape = str(argument_shape_digest or "").lower()
    if not op or not HEX64.fullmatch(shape):
        raise ValueError("bounded_operation_and_argument_shape_required")
    row = {
        "contract_version": CONTRACT_VERSION,
        "capability_id": manifest["capability_id"],
        "manifest_digest": manifest["manifest_digest"],
        "eligibility_digest": str(eligibility.get("eligibility_digest") or ""),
        "operation_code": op,
        "argument_shape_digest": shape,
        "proposal_ready": True,
        "approval_required": manifest.get("approval_class") != "none",
        "approval_class": manifest.get("approval_class"),
        "reversible": bool(manifest.get("reversible")),
        "cancellation_supported": bool(manifest.get("cancellation_supported")),
        "rollback_supported": bool(manifest.get("rollback_supported")),
        "execution_admitted": False,
        "execution_performed": False,
        "adapter_invoked": False,
        "raw_arguments_stored": False,
        "authority_inferred": False,
    }
    row["intent_digest"] = _digest(row)
    return row


__all__ = ["CONTRACT_VERSION", "evaluate_capability_eligibility", "prepare_general_action_intent"]
