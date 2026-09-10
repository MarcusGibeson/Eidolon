from __future__ import annotations

"""Bounded content-free release-authority handoff consolidation."""

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from release_authority_readiness import release_authority_readiness_status
    from release_authority_readiness_recovery import readiness_refresh_status
    from release_authority_handoff_plan import release_authority_handoff_plan_status, release_authority_handoff_acknowledgment_status
    from release_authority_handoff_ack_recovery import handoff_acknowledgment_recovery_status
    from release_authority_consumer import release_authority_consumer_receipt_status
    from release_certification_coherence import certification_coherence_status
    from release_certification_history import certification_history_status
    from release_certification_policy import certification_policy_status, policy_migration_status
    from release_certification_freshness import evidence_freshness_status, recertification_readiness_status
except ImportError:
    from release_authority_readiness import release_authority_readiness_status
    from release_authority_readiness_recovery import readiness_refresh_status
    from release_authority_handoff_plan import release_authority_handoff_plan_status, release_authority_handoff_acknowledgment_status
    from release_authority_handoff_ack_recovery import handoff_acknowledgment_recovery_status
    from release_authority_consumer import release_authority_consumer_receipt_status
    from release_certification_coherence import certification_coherence_status
    from release_certification_history import certification_history_status
    from release_certification_policy import certification_policy_status, policy_migration_status
    from release_certification_freshness import evidence_freshness_status, recertification_readiness_status

RELEASE_AUTHORITY_DAILY_USE_CONTRACT_VERSION = "2"


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": str(row.get("status") or "release_authority_daily_use_unavailable"),
        "contract_version": RELEASE_AUTHORITY_DAILY_USE_CONTRACT_VERSION,
        "readiness_status": str(row.get("readiness_status") or ""),
        "readiness_generation": int(row.get("readiness_generation") or 0),
        "readiness_binding_sha256": str(row.get("readiness_binding_sha256") or ""),
        "refresh_status": str(row.get("refresh_status") or ""),
        "refresh_generation": int(row.get("refresh_generation") or 0),
        "refresh_recovery_available": bool(row.get("refresh_recovery_available")),
        "handoff_plan_status": str(row.get("handoff_plan_status") or ""),
        "handoff_plan_id": str(row.get("handoff_plan_id") or ""),
        "handoff_plan_binding_sha256": str(row.get("handoff_plan_binding_sha256") or ""),
        "handoff_acknowledgment_status": str(row.get("handoff_acknowledgment_status") or ""),
        "handoff_acknowledged": bool(row.get("handoff_acknowledged")),
        "handoff_acknowledgment_id": str(row.get("handoff_acknowledgment_id") or ""),
        "handoff_acknowledgment_receipt_sha256": str(row.get("handoff_acknowledgment_receipt_sha256") or ""),
        "handoff_acknowledgment_expires_at": str(row.get("handoff_acknowledgment_expires_at") or ""),
        "handoff_acknowledgment_expired": bool(row.get("handoff_acknowledgment_expired")),
        "handoff_acknowledgment_recovery_status": str(row.get("handoff_acknowledgment_recovery_status") or ""),
        "handoff_acknowledgment_recovery_available": bool(row.get("handoff_acknowledgment_recovery_available")),
        "handoff_acknowledgment_replacement_available": bool(row.get("handoff_acknowledgment_replacement_available")),
        "handoff_acknowledgment_cleanup_available": bool(row.get("handoff_acknowledgment_cleanup_available")),
        "consumer_status": str(row.get("consumer_status") or "release_authority_consumer_not_selected"),
        "consumer_id": str(row.get("consumer_id") or ""),
        "consumer_schema": str(row.get("consumer_schema") or ""),
        "consumer_version": str(row.get("consumer_version") or ""),
        "consumer_expected_use": str(row.get("consumer_expected_use") or ""),
        "consumer_receipt_present": bool(row.get("consumer_receipt_present")),
        "consumer_receipt_stale": bool(row.get("consumer_receipt_stale")),
        "consumer_receipt_sha256": str(row.get("consumer_receipt_sha256") or ""),
        "consumer_receipt_operation_status": str(row.get("consumer_receipt_operation_status") or ""),
        "authority_status": str(row.get("authority_status") or ""),
        "history_status": str(row.get("history_status") or ""),
        "policy_status": str(row.get("policy_status") or ""),
        "migration_status": str(row.get("migration_status") or ""),
        "freshness_status": str(row.get("freshness_status") or ""),
        "recertification_status": str(row.get("recertification_status") or ""),
        "certified_scopes": list(row.get("certified_scopes") or []),
        "unresolved_blockers": _counts(row.get("unresolved_blockers") if isinstance(row.get("unresolved_blockers"), list) else []),
        "unresolved_blocker_count": int(row.get("unresolved_blocker_count") or 0),
        "operation_owner_present": bool(row.get("operation_owner_present")),
        "operation": str(row.get("operation") or ""),
        "operation_generation": int(row.get("operation_generation") or 0),
        "operation_revision": int(row.get("operation_revision") or 0),
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "duplicate_execution_allowed": False,
        "consumer_discovery_performed": False,
        "newest_consumer_inferred": False,
        "consumer_receipt_grants_authority": False,
        "authority_transfer_on_refresh": False,
        "authority_transfer_on_restart": False,
        "installation_inferred": False,
        "promotion_inferred": False,
        "general_release_certification_inferred": False,
        "native_windows_inferred": False,
        "provider_ollama_inferred": False,
        "model_specific_inferred": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "ordinary_conversation_affected": False,
        "provider_contacted": False,
        "native_checks_run": False,
        "models_mutated": False,
        "source_files_mutated": False,
        "installed_source_mutated": False,
        "installation_changed": False,
        "promotion_changed": False,
        "certification_changed": False,
        "policy_migrated": False,
    }


def release_authority_daily_use_status(
    *,
    consumer_id: str = "",
    consumer_schema: str = "",
    consumer_version: str = "",
    consumer_expected_use: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    readiness = release_authority_readiness_status(runtime_root=runtime_root)
    refresh = readiness_refresh_status(runtime_root=runtime_root)
    plan = release_authority_handoff_plan_status(runtime_root=runtime_root)
    acknowledgment = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
    acknowledgment_recovery = handoff_acknowledgment_recovery_status(runtime_root=runtime_root)
    certification = certification_coherence_status(runtime_root=runtime_root)
    history = certification_history_status(runtime_root=runtime_root)
    policy = certification_policy_status(runtime_root=runtime_root)
    migration = policy_migration_status(runtime_root=runtime_root)
    freshness = evidence_freshness_status(runtime_root=runtime_root)
    recertification = recertification_readiness_status(runtime_root=runtime_root)
    consumer_fields = [str(consumer_id or "").strip(), str(consumer_schema or "").strip(), str(consumer_version or "").strip(), str(consumer_expected_use or "").strip()]
    consumer_requested = any(consumer_fields)
    if consumer_requested and all(consumer_fields):
        consumer = release_authority_consumer_receipt_status(*consumer_fields, runtime_root=runtime_root)
    elif consumer_requested:
        consumer = {"ok": False, "status": "exact_consumer_identity_schema_version_and_use_required", "receipt_present": False, "receipt_stale": True}
    else:
        consumer = {"ok": True, "status": "release_authority_consumer_not_selected", "receipt_present": False, "receipt_stale": False}

    contradictions: list[dict[str, Any]] = []
    if not readiness.get("ok"):
        contradictions.append({"kind": "release_authority_readiness_not_current"})
    if refresh.get("recovery_available"):
        contradictions.append({"kind": "release_authority_refresh_recovery_pending"})
    if plan.get("plan_id") and not plan.get("ok"):
        contradictions.append({"kind": "release_authority_handoff_plan_stale"})
    if acknowledgment.get("acknowledgment_present") and not acknowledgment.get("ok"):
        contradictions.append({"kind": "release_authority_handoff_acknowledgment_stale"})
    if acknowledgment.get("acknowledgment_expired"):
        contradictions.append({"kind": "release_authority_handoff_acknowledgment_expired"})
    if acknowledgment_recovery.get("recovery_available"):
        contradictions.append({"kind": "release_authority_handoff_acknowledgment_recovery_pending"})
    if consumer_requested and not consumer.get("ok"):
        contradictions.append({"kind": "release_authority_consumer_receipt_not_current"})
    if not certification.get("ok"):
        contradictions.append({"kind": "certification_daily_use_not_coherent"})
    if not history.get("ok"):
        contradictions.append({"kind": "certification_history_not_coherent"})
    if not policy.get("ok"):
        contradictions.append({"kind": "certification_policy_not_selected"})
    if not migration.get("ok"):
        contradictions.append({"kind": "certification_policy_migration_not_current"})
    if readiness.get("general_release_certified") and "general_release" not in list(certification.get("certified_scopes") or []):
        contradictions.append({"kind": "general_release_scope_authority_mismatch"})
    if readiness.get("native_windows_certified") and "native_windows" not in list(certification.get("certified_scopes") or []):
        contradictions.append({"kind": "native_windows_scope_authority_mismatch"})
    if readiness.get("provider_ollama_certified") and "provider_ollama" not in list(certification.get("certified_scopes") or []):
        contradictions.append({"kind": "provider_ollama_scope_authority_mismatch"})
    if readiness.get("model_specific_certified") and "model_specific" not in list(certification.get("certified_scopes") or []):
        contradictions.append({"kind": "model_specific_scope_authority_mismatch"})
    blockers = list(readiness.get("findings") or []) + list(plan.get("unresolved_blockers") or [])
    counted_blockers = _counts(blockers)
    return _public({
        "ok": not contradictions,
        "status": "release_authority_daily_use_coherent" if not contradictions else "release_authority_daily_use_attention_required",
        "readiness_status": readiness.get("status"),
        "readiness_generation": readiness.get("generation"),
        "readiness_binding_sha256": readiness.get("readiness_binding_sha256"),
        "refresh_status": refresh.get("status"),
        "refresh_generation": refresh.get("refresh_generation"),
        "refresh_recovery_available": refresh.get("recovery_available"),
        "handoff_plan_status": plan.get("status"),
        "handoff_plan_id": plan.get("plan_id"),
        "handoff_plan_binding_sha256": plan.get("plan_binding_sha256"),
        "handoff_acknowledgment_status": acknowledgment.get("status"),
        "handoff_acknowledged": acknowledgment.get("acknowledgment_present") and acknowledgment.get("ok"),
        "handoff_acknowledgment_id": acknowledgment.get("acknowledgment_id"),
        "handoff_acknowledgment_receipt_sha256": acknowledgment.get("acknowledgment_receipt_sha256"),
        "handoff_acknowledgment_expires_at": acknowledgment.get("acknowledgment_expires_at"),
        "handoff_acknowledgment_expired": acknowledgment.get("acknowledgment_expired"),
        "handoff_acknowledgment_recovery_status": acknowledgment_recovery.get("status"),
        "handoff_acknowledgment_recovery_available": acknowledgment_recovery.get("recovery_available"),
        "handoff_acknowledgment_replacement_available": acknowledgment_recovery.get("replacement_available"),
        "handoff_acknowledgment_cleanup_available": acknowledgment_recovery.get("cleanup_available"),
        "consumer_status": consumer.get("status"),
        "consumer_id": consumer_fields[0] if consumer_requested else "",
        "consumer_schema": consumer_fields[1] if consumer_requested else "",
        "consumer_version": consumer_fields[2] if consumer_requested else "",
        "consumer_expected_use": consumer_fields[3] if consumer_requested else "",
        "consumer_receipt_present": consumer.get("receipt_present"),
        "consumer_receipt_stale": consumer.get("receipt_stale"),
        "consumer_receipt_sha256": consumer.get("consumer_receipt_sha256"),
        "consumer_receipt_operation_status": consumer.get("consumer_receipt_operation_status"),
        "authority_status": certification.get("status"),
        "history_status": history.get("status"),
        "policy_status": policy.get("status"),
        "migration_status": migration.get("status"),
        "freshness_status": freshness.get("status"),
        "recertification_status": recertification.get("status"),
        "certified_scopes": certification.get("certified_scopes") or [],
        "unresolved_blockers": counted_blockers,
        "unresolved_blocker_count": sum(int(item["count"]) for item in counted_blockers),
        "operation_owner_present": certification.get("operation_owner_present"),
        "operation": certification.get("operation"),
        "operation_generation": certification.get("operation_generation"),
        "operation_revision": certification.get("operation_revision"),
        "contradictions": contradictions,
    })
