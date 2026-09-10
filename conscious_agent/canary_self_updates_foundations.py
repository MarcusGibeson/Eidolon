from __future__ import annotations
"""v1296.0-v1296.2 canary self-update evidence foundations.

This contract describes separately observed baseline/candidate canaries. It does
not launch a process, apply a candidate, consume v1269 authorization, or mutate
an active installation.
"""
from hashlib import sha256
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1296.2"
MANDATORY_SIGNALS = (
    "startup",
    "conversation_smoke",
    "verification",
    "source_isolation",
    "runtime_isolation",
    "privacy_security",
    "process_health",
    "restart_health",
)
NATIVE_SIGNAL = "native_windows_canary"
VALID_STATES = frozenset({"passed", "failed", "blocked", "unavailable", "pending"})
DENIED_AUTHORITY = {
    "canary_execution_authorized": False,
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "source_application_authorized": False,
    "self_update_authorized": False,
    "update_authorization_consumed": False,
    "rollback_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "standing_authority_granted": False,
}
ARCHITECTURE_LINEAGE = {
    "governed_self_update": "v1269",
    "comprehensive_verification": "v1295",
    "candidate_identity": "v1253.9",
    "operator_review": "v1268",
}

def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()

def valid_digest(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return len(token) == 64 and all(ch in "0123456789abcdef" for ch in token)

def seal_canary_identity(*, update_id: str, baseline_source_digest: str, candidate_source_digest: str,
                         update_packet_digest: str, review_decision_digest: str,
                         baseline_workspace_digest: str, candidate_workspace_digest: str,
                         observation_budget: int = 32) -> dict[str, Any]:
    fields = (baseline_source_digest, candidate_source_digest, update_packet_digest, review_decision_digest,
              baseline_workspace_digest, candidate_workspace_digest)
    if not str(update_id).startswith("selfupdate_"):
        raise ValueError("v1269_update_id_required")
    if not all(valid_digest(x) for x in fields):
        raise ValueError("sealed_digest_lineage_required")
    if baseline_source_digest == candidate_source_digest:
        raise ValueError("changed_candidate_required")
    if baseline_workspace_digest == candidate_workspace_digest:
        raise ValueError("separate_canary_workspaces_required")
    budget = int(observation_budget)
    if budget < len(MANDATORY_SIGNALS) * 2 or budget > 128:
        raise ValueError("bounded_observation_budget_required")
    body = {
        "contract_version": CONTRACT_VERSION,
        "update_id": str(update_id),
        "baseline_source_digest": baseline_source_digest,
        "candidate_source_digest": candidate_source_digest,
        "update_packet_digest": update_packet_digest,
        "review_decision_digest": review_decision_digest,
        "baseline_workspace_digest": baseline_workspace_digest,
        "candidate_workspace_digest": candidate_workspace_digest,
        "mandatory_signals": list(MANDATORY_SIGNALS),
        "native_signal": NATIVE_SIGNAL,
        "observation_budget": budget,
        "separate_workspace_required": True,
        "shared_mutable_runtime_allowed": False,
        "content_free": True,
    }
    body["canary_id"] = "canary_" + digest(body)[:24]
    body["identity_digest"] = digest(body)
    return body | DENIED_AUTHORITY

def canary_observation(identity: Mapping[str, Any], *, role: str, signal: str, status: str,
                       evidence_digest: str, fresh: bool = True, quality_score: float = 1.0,
                       latency_ms: float = 0.0, private_finding_count: int = 0,
                       shared_mutable_runtime: bool = False, platform_name: str = "",
                       native_attested: bool = False) -> dict[str, Any]:
    role = str(role); signal = str(signal); status = str(status)
    if role not in {"baseline", "candidate"}: raise ValueError("canary_role_required")
    if signal not in set(MANDATORY_SIGNALS) | {NATIVE_SIGNAL}: raise ValueError("known_canary_signal_required")
    if status not in VALID_STATES: raise ValueError("valid_canary_state_required")
    if not valid_digest(identity.get("identity_digest")) or not valid_digest(evidence_digest): raise ValueError("sealed_evidence_required")
    if status == "passed" and not fresh: raise ValueError("stale_canary_evidence_cannot_pass")
    score = float(quality_score); latency = float(latency_ms)
    if not 0.0 <= score <= 1.0 or latency < 0.0: raise ValueError("bounded_health_metric_required")
    platform = str(platform_name or "").lower()
    if signal == NATIVE_SIGNAL and status == "passed" and (platform != "windows" or not native_attested):
        raise ValueError("native_canary_pass_requires_windows_attestation")
    row = {
        "contract_version": CONTRACT_VERSION,
        "canary_id": identity.get("canary_id"),
        "identity_digest": identity.get("identity_digest"),
        "role": role,
        "signal": signal,
        "status": status,
        "evidence_digest": evidence_digest,
        "fresh": bool(fresh),
        "quality_score": score,
        "latency_ms": latency,
        "private_finding_count": max(0, int(private_finding_count)),
        "shared_mutable_runtime": bool(shared_mutable_runtime),
        "platform_name": platform,
        "native_attested": bool(native_attested),
        "content_free": True,
    }
    row["observation_digest"] = digest(row)
    return row | DENIED_AUTHORITY
