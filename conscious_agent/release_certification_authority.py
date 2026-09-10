from __future__ import annotations

"""Bounded certification authority-history and policy coherence status."""

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from release_certification_coherence import certification_coherence_status
    from release_certification_evidence import certification_readiness_status
    from release_certification_freshness import evidence_freshness_status, recertification_readiness_status
    from release_certification_history import certification_history_status
    from release_certification_policy import certification_policy_status, policy_migration_status
    from release_certification_recovery import certification_recovery_status
    from release_certification_transaction import certification_status
except ImportError:
    from release_certification_coherence import certification_coherence_status
    from release_certification_evidence import certification_readiness_status
    from release_certification_freshness import evidence_freshness_status, recertification_readiness_status
    from release_certification_history import certification_history_status
    from release_certification_policy import certification_policy_status, policy_migration_status
    from release_certification_recovery import certification_recovery_status
    from release_certification_transaction import certification_status

CERTIFICATION_AUTHORITY_COHERENCE_CONTRACT_VERSION = "1"


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []: found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind":k,"count":found[k]} for k in sorted(found)]


def certification_authority_coherence_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    authority=certification_status(runtime_root=runtime_root)
    history=certification_history_status(runtime_root=runtime_root)
    policy=certification_policy_status(runtime_root=runtime_root)
    migration=policy_migration_status(runtime_root=runtime_root)
    freshness=evidence_freshness_status(runtime_root=runtime_root)
    recert=recertification_readiness_status(runtime_root=runtime_root)
    recovery=certification_recovery_status(runtime_root=runtime_root)
    daily=certification_coherence_status(runtime_root=runtime_root)
    readiness=certification_readiness_status(runtime_root=runtime_root)
    findings=[]
    for name,row in (("authority",authority),("history",history),("policy",policy),("migration",migration),("freshness",freshness),("recovery",recovery),("daily",daily)):
        if not row.get("ok") and str(row.get("status") or "") not in {"certification_policy_not_selected","policy_migration_not_previewed","certification_history_not_reconciled","certification_recovery_uncertain","certification_recovery_not_required"}:
            findings.append({"kind":f"{name}_status_contradictory"})
    certified_scopes=list(authority.get("certified_scopes") or [])
    general="general_release" in certified_scopes
    native="native_windows" in certified_scopes
    provider="provider_ollama" in certified_scopes
    model="model_specific" in certified_scopes
    status="certification_authority_coherent" if not findings else "certification_authority_contradictory_or_uncertain"
    counted=_counts(findings)
    return {
        "ok":not findings,"status":status,"contract_version":CERTIFICATION_AUTHORITY_COHERENCE_CONTRACT_VERSION,
        "authority_status":authority.get("status"),"certified_scopes":certified_scopes,"general_release_certified":general,
        "native_windows_certified":native,"provider_ollama_certified":provider,"model_specific_certified":model,
        "native_windows_inferred":False,"provider_ollama_inferred":False,"model_specific_inferred":False,
        "history_status":history.get("status"),"history_sha256":history.get("history_sha256"),"history_finding_count":history.get("finding_count",0),
        "policy_status":policy.get("status"),"policy_id":policy.get("policy_id"),"policy_sha256":policy.get("policy_sha256"),
        "policy_migration_status":migration.get("status"),"policy_scope_impacts":migration.get("scope_impacts",[]),
        "fresh_scopes":freshness.get("fresh_scopes",[]),"expired_scopes":freshness.get("expired_scopes",[]),"stale_scopes":freshness.get("stale_scopes",[]),
        "recertification_status":recert.get("status"),"recertification_required":bool(recert.get("recertification_required")),
        "recovery_status":recovery.get("status"),"recovery_available":bool(recovery.get("recovery_available")),
        "operation_owner_present":bool(daily.get("operation_owner_present")),"operation":daily.get("operation"),"operation_generation":daily.get("operation_generation",0),
        "readiness_status":readiness.get("status"),"finding_count":sum(int(x["count"]) for x in counted),"findings":counted,
        "installation_inferred":False,"promotion_inferred":False,"certification_inferred":False,
        "source_files_mutated":False,"installed_source_mutated":False,"provider_configuration_mutated":False,"models_mutated":False,
        "paths_suppressed":True,"records_external":True,"content_free":True,"ordinary_conversation_affected":False,
    }
