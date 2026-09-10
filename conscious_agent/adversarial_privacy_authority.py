from __future__ import annotations

"""v1196.0-v1196.2 bounded adversarial privacy and authority evidence.

The contract validates caller-supplied, content-free attack observations. It does
not fetch private state, execute attacks, grant authority, or mutate runtime data.
"""

import hashlib
import json
from typing import Any, Mapping, Sequence
from adversarial_privacy_authority_digest import (
    SymbolDependencies as _AdversarialPrivacyAuthorityDigestSymbolDependencies,
    _digest as _digest_implementation,
    _hex_digest as _hex_digest_implementation,
)


CONTRACT_VERSION = "v1196.2"
ATTACK_CLASSES = (
    "private_field_injection", "secret_exfiltration", "prompt_exposure",
    "memory_exposure", "provider_payload_exposure", "raw_source_exposure",
    "authority_escalation", "approval_forgery", "execution_forgery",
    "cancellation_forgery", "release_authority_forgery", "replay_attack",
    "stale_state_attack", "lineage_tamper",
)
AUTHORITY_DOMAINS = (
    "conversation", "cognition", "reasoning", "planning", "campaign",
    "approval", "action", "result", "learning", "queue", "cancellation",
    "installation", "promotion", "certification", "publication", "release",
)
_PRIVATE_TOKENS = (
    "prompt", "conversation_text", "message_text", "memory_text", "secret",
    "credential", "token", "provider_payload", "raw_source", "patch_text",
    "stdout", "stderr", "private_reasoning",
)


def _build_adversarial_privacy_authority_digest_dependencies() -> _AdversarialPrivacyAuthorityDigestSymbolDependencies:
    return _AdversarialPrivacyAuthorityDigestSymbolDependencies(
        hashlib=hashlib,
    )

def _digest(value: object) -> str:
    return _digest_implementation(value, _deps=_build_adversarial_privacy_authority_digest_dependencies())



def _hex_digest(value: object) -> bool:
    return _hex_digest_implementation(value, _deps=_build_adversarial_privacy_authority_digest_dependencies())



def _private_fields(value: Mapping[str, Any]) -> list[str]:
    return sorted(str(key) for key in value if any(token in str(key).lower() for token in _PRIVATE_TOKENS))


def validate_adversarial_privacy_authority_evidence(
    evidence: Mapping[str, Any], *,
    expected_snapshot_digest: str,
    expected_context_digest: str,
    expected_prior_receipt_digest: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    errors.extend(f"private_field:{field}" for field in _private_fields(evidence))
    required_digests = ("snapshot_digest", "context_digest", "artifact_digest", "receipt_digest")
    for field in required_digests:
        if not _hex_digest(evidence.get(field)):
            errors.append(f"malformed_{field}")
    if evidence.get("snapshot_digest") != expected_snapshot_digest:
        errors.append("stale_snapshot")
    if evidence.get("context_digest") != expected_context_digest:
        errors.append("stale_context")
    if evidence.get("attack_class") not in ATTACK_CLASSES:
        errors.append("unsupported_attack_class")
    if evidence.get("target_domain") not in AUTHORITY_DOMAINS:
        errors.append("unsupported_target_domain")
    sequence = evidence.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1 or sequence > 10000:
        errors.append("invalid_sequence")
    prior = evidence.get("prior_receipt_digest")
    if expected_prior_receipt_digest is None:
        if prior not in (None, ""):
            errors.append("unexpected_prior_receipt")
    elif prior != expected_prior_receipt_digest:
        errors.append("broken_lineage")
    expected_true = (
        "content_free", "attack_blocked", "privacy_preserved", "authority_separate",
        "approval_state_preserved", "original_evidence_preserved", "historical_truth_preserved",
    )
    for field in expected_true:
        if evidence.get(field) is not True:
            errors.append(f"invalid_{field}")
    expected_false = (
        "private_data_exposed", "authority_granted", "approval_created", "approval_consumed",
        "execution_invoked", "cancellation_executed", "runtime_mutated", "source_modified",
        "provider_contacted", "model_contacted", "thread_started", "process_started",
        "installation_performed", "promotion_performed", "certification_performed",
        "publication_performed", "release_performed", "automatic_continuation",
    )
    for field in expected_false:
        if evidence.get(field) is not False:
            errors.append(f"invalid_{field}")
    if evidence.get("authority_state") != "separate_not_granted":
        errors.append("authority_expansion")
    supplied_digest = evidence.get("evidence_digest")
    body = {key: value for key, value in evidence.items() if key != "evidence_digest"}
    if supplied_digest != _digest(body):
        errors.append("evidence_tamper")
    return {
        "ok": not errors,
        "contract_version": CONTRACT_VERSION,
        "errors": sorted(set(errors)),
        "summary": public_adversarial_privacy_authority_summary(evidence, errors=errors),
    }


def public_adversarial_privacy_authority_summary(evidence: Mapping[str, Any], *, errors: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "attack_class": str(evidence.get("attack_class") or "unknown"),
        "target_domain": str(evidence.get("target_domain") or "unknown"),
        "sequence": evidence.get("sequence"),
        "attack_blocked": evidence.get("attack_blocked") is True,
        "privacy_preserved": evidence.get("privacy_preserved") is True,
        "authority_state": str(evidence.get("authority_state") or "unknown"),
        "content_free": evidence.get("content_free") is True,
        "error_count": len(set(errors)),
        "errors": sorted(set(str(item) for item in errors)),
        "execution_invoked": evidence.get("execution_invoked") is True,
        "runtime_mutated": evidence.get("runtime_mutated") is True,
        "authority_granted": evidence.get("authority_granted") is True,
    }


def build_evidence(*, attack_class: str, target_domain: str, sequence: int, snapshot_digest: str, context_digest: str, artifact_digest: str, receipt_digest: str, prior_receipt_digest: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "attack_class": attack_class,
        "target_domain": target_domain,
        "sequence": sequence,
        "snapshot_digest": snapshot_digest,
        "context_digest": context_digest,
        "artifact_digest": artifact_digest,
        "receipt_digest": receipt_digest,
        "prior_receipt_digest": prior_receipt_digest,
        "content_free": True,
        "attack_blocked": True,
        "privacy_preserved": True,
        "authority_separate": True,
        "approval_state_preserved": True,
        "original_evidence_preserved": True,
        "historical_truth_preserved": True,
        "private_data_exposed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
        "approval_created": False,
        "approval_consumed": False,
        "execution_invoked": False,
        "cancellation_executed": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "publication_performed": False,
        "release_performed": False,
        "automatic_continuation": False,
    }
    row["evidence_digest"] = _digest(row)
    return row
