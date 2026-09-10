from __future__ import annotations
"""v1196.6-v1196.8 content-free adversarial reliability and integration evidence."""
import hashlib, json
from typing import Any, Mapping

CONTRACT_VERSION = "v1196.8"
EVENT_CLASSES = (
    "cross_surface_replay",
    "stale_authority_projection",
    "interruption_reordering",
    "cancellation_replay",
    "recovery_reentry",
    "privacy_boundary_drift",
    "authority_boundary_drift",
    "integration_digest_drift",
)
SURFACES = (
    "conversation", "cognition", "reasoning", "planning", "campaign",
    "approval", "action", "queue", "cancellation", "recovery",
    "evidence", "verification",
)
_PRIVATE = (
    "prompt", "conversation_text", "memory_text", "secret", "credential", "token",
    "provider_payload", "raw_source", "patch_text", "stdout", "stderr", "private_reasoning",
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _hex(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(ch in "0123456789abcdef" for ch in token)


def _private_fields(value: Mapping[str, Any]) -> list[str]:
    return sorted(str(key) for key in value if any(term in str(key).lower() for term in _PRIVATE))


def build_reliability_event(
    *, event_id: str, event_class: str, surface: str, sequence: int,
    snapshot_digest: str, context_digest: str, evidence_digest: str,
    authority_digest: str, prior_event_digest: str | None = None,
    foreground_latency_ms: int = 0, latency_budget_ms: int = 250,
) -> dict[str, Any]:
    row = {
        "contract_version": CONTRACT_VERSION,
        "event_id": event_id,
        "event_class": event_class,
        "surface": surface,
        "sequence": sequence,
        "snapshot_digest": snapshot_digest,
        "context_digest": context_digest,
        "evidence_digest": evidence_digest,
        "authority_digest": authority_digest,
        "prior_event_digest": prior_event_digest,
        "foreground_latency_ms": foreground_latency_ms,
        "latency_budget_ms": latency_budget_ms,
        "content_free": True,
        "original_evidence_preserved": True,
        "foreground_available": True,
        "automatic_recovery_requested": False,
        "automatic_retry_requested": False,
        "cancellation_executed": False,
        "execution_invoked": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "authority_requested": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
    }
    row["event_digest"] = _digest(row)
    return row


def inspect_reliability_event(
    *, event: Mapping[str, Any], expected_snapshot_digest: str,
    expected_context_digest: str, expected_evidence_digest: str,
    expected_authority_digest: str, expected_prior_event_digest: str | None = None,
) -> dict[str, Any]:
    row = dict(event)
    errors: list[str] = []
    errors.extend(f"private_field:{name}" for name in _private_fields(row))
    body = dict(row)
    supplied = body.pop("event_digest", None)
    if supplied != _digest(body):
        errors.append("event_tamper")
    if row.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported_contract")
    for field in ("snapshot_digest", "context_digest", "evidence_digest", "authority_digest"):
        if not _hex(row.get(field)):
            errors.append(f"malformed_{field}")
    if row.get("snapshot_digest") != expected_snapshot_digest:
        errors.append("stale_snapshot")
    if row.get("context_digest") != expected_context_digest:
        errors.append("stale_context")
    if row.get("evidence_digest") != expected_evidence_digest:
        errors.append("stale_evidence")
    if row.get("authority_digest") != expected_authority_digest:
        errors.append("stale_authority")
    if row.get("event_class") not in EVENT_CLASSES:
        errors.append("unsupported_event_class")
    if row.get("surface") not in SURFACES:
        errors.append("unsupported_surface")
    sequence = row.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= 10000:
        errors.append("invalid_sequence")
    prior = row.get("prior_event_digest")
    if expected_prior_event_digest is None:
        if prior not in (None, ""):
            errors.append("unexpected_prior_event")
    elif prior != expected_prior_event_digest:
        errors.append("broken_event_lineage")
    latency = row.get("foreground_latency_ms")
    budget = row.get("latency_budget_ms")
    if not isinstance(latency, int) or isinstance(latency, bool) or latency < 0:
        errors.append("invalid_foreground_latency")
    if not isinstance(budget, int) or isinstance(budget, bool) or not 1 <= budget <= 10000:
        errors.append("invalid_latency_budget")
    if isinstance(latency, int) and isinstance(budget, int) and latency > budget:
        errors.append("foreground_latency_budget_exceeded")
    for field in ("content_free", "original_evidence_preserved", "foreground_available"):
        if row.get(field) is not True:
            errors.append(f"invalid_{field}")
    for field in (
        "automatic_recovery_requested", "automatic_retry_requested", "cancellation_executed",
        "execution_invoked", "runtime_mutated", "provider_contacted", "model_contacted",
        "thread_started", "process_started", "approval_created", "approval_consumed",
        "authority_requested", "authority_granted", "global_profile_pass_claimed",
    ):
        if row.get(field) is not False:
            errors.append(f"invalid_{field}")
    out = {
        "ok": not errors,
        "contract_version": CONTRACT_VERSION,
        "status": "reliability_verified" if not errors else "blocked",
        "errors": sorted(set(errors)),
        "event_class": row.get("event_class"),
        "surface": row.get("surface"),
        "sequence": row.get("sequence"),
        "content_free": True,
        "exact_lineage_verified": not errors,
        "original_evidence_preserved": True,
        "foreground_available": True,
        "automatic_recovery_executed": False,
        "automatic_retry_executed": False,
        "cancellation_executed": False,
        "execution_invoked": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
        "global_profile_pass_claimed": False,
    }
    out["reliability_receipt_digest"] = _digest(out)
    return out
