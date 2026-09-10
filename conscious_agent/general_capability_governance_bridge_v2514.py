from __future__ import annotations

"""v2514 governance bridge for general capability actions.

Produces a digest-bound admission *candidate*. It composes existing general
intent evidence, an enabled adapter descriptor, a fine-grained policy ceiling,
and an explicit external authority receipt. It never calls an adapter.
"""
import hashlib, json, re
from typing import Any, Mapping

from general_capability_adapter_registry_v2513 import validate_adapter_descriptor

CONTRACT_VERSION = "v2514.0"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",",":"), ensure_ascii=True).encode()).hexdigest()

def build_governed_action_admission(*, intent: Mapping[str, Any], adapter: Mapping[str, Any],
                                    policy_decision: Mapping[str, Any], authority_receipt: Mapping[str, Any]) -> dict[str, Any]:
    reasons=[]
    if not HEX64.fullmatch(str(intent.get("intent_digest") or "")): reasons.append("intent_invalid")
    if not validate_adapter_descriptor(adapter).get("ok"): reasons.append("adapter_invalid")
    if adapter.get("enabled") is not True: reasons.append("adapter_disabled")
    if str(adapter.get("capability_id") or "") != str(intent.get("capability_id") or ""): reasons.append("capability_mismatch")
    if str(adapter.get("manifest_digest") or "") != str(intent.get("manifest_digest") or ""): reasons.append("manifest_mismatch")
    if policy_decision.get("allowed_by_policy_ceiling") is not True: reasons.append("policy_ceiling_denies")
    if policy_decision.get("external_authority_receipt_still_required") is not True: reasons.append("policy_contract_invalid")
    if authority_receipt.get("authorization_granted") is not True or authority_receipt.get("execution_admitted") is not True: reasons.append("exact_authority_required")
    if authority_receipt.get("execution_performed") is True or authority_receipt.get("executor_invoked") is True: reasons.append("authority_receipt_already_executed")
    for key in ("authorization_digest","operation_digest","execution_admission_digest"):
        if not HEX64.fullmatch(str(authority_receipt.get(key) or "")): reasons.append(f"{key}_required")
    admitted = not reasons
    row={
        "contract_version": CONTRACT_VERSION,
        "capability_id": str(intent.get("capability_id") or "")[:80],
        "manifest_digest": str(intent.get("manifest_digest") or "")[:64],
        "intent_digest": str(intent.get("intent_digest") or "")[:64],
        "adapter_id": str(adapter.get("adapter_id") or "")[:96],
        "adapter_digest": str(adapter.get("adapter_digest") or "")[:64],
        "policy_decision_digest": str(policy_decision.get("decision_digest") or "")[:64],
        "authorization_digest": str(authority_receipt.get("authorization_digest") or "")[:64],
        "operation_digest": str(authority_receipt.get("operation_digest") or "")[:64],
        "admitted": admitted,
        "reason_codes": sorted(set(reasons)),
        "adapter_invocation_allowed": admitted,
        "adapter_invoked": False,
        "execution_performed": False,
        "side_effect_performed": False,
        "raw_arguments_stored": False,
        "raw_output_stored": False,
        "authority_inferred": False,
    }
    row["admission_digest"]=_digest(row)
    return row

__all__=["CONTRACT_VERSION","build_governed_action_admission"]
