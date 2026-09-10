from __future__ import annotations

"""Read-only certification-to-release authority readiness checkpoint.

The checkpoint binds existing release records. It grants no installation,
promotion, certification, policy-migration, provider, model, or native-platform
authority.
"""

from collections import Counter
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_handoff_inspection import operator_selected_handoff_status
    from release_installation_transaction import installation_transaction_status
    from release_installation_recovery import inspect_installation_transaction
    from release_installed_state import installed_state_status
    from release_promotion_transaction import promotion_transaction_status
    from release_certification_transaction import certification_status
    from release_certification_recovery import certification_recovery_status
    from release_certification_freshness import evidence_freshness_status, recertification_readiness_status
    from release_certification_history import certification_history_status
    from release_certification_policy import certification_policy_status, policy_migration_status
    from release_certification_authority import certification_authority_coherence_status
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_handoff_inspection import operator_selected_handoff_status
    from release_installation_transaction import installation_transaction_status
    from release_installation_recovery import inspect_installation_transaction
    from release_installed_state import installed_state_status
    from release_promotion_transaction import promotion_transaction_status
    from release_certification_transaction import certification_status
    from release_certification_recovery import certification_recovery_status
    from release_certification_freshness import evidence_freshness_status, recertification_readiness_status
    from release_certification_history import certification_history_status
    from release_certification_policy import certification_policy_status, policy_migration_status
    from release_certification_authority import certification_authority_coherence_status

RELEASE_AUTHORITY_READINESS_CONTRACT_VERSION = "1"
RELEASE_AUTHORITY_READINESS_DIRECTORY = "release_authority_readiness"
READINESS_SCHEMA = "eidolon-release-authority-readiness-v1"
SCOPES = ("general_release", "native_windows", "provider_ollama", "model_specific")


def release_authority_readiness_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / RELEASE_AUTHORITY_READINESS_DIRECTORY


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _record_digest(record: Mapping[str, Any]) -> str:
    material = dict(record)
    material.pop("record_sha256", None)
    return digest_payload(material)


def _runtime_identity(runtime_root: str | Path | None) -> str:
    return digest_payload({"contract": "eidolon-runtime-root-identity-v1", "path": str(runtime_data_root(runtime_root))})


def _scope_rows(authority: Mapping[str, Any], migration: Mapping[str, Any], freshness: Mapping[str, Any]) -> list[dict[str, Any]]:
    certified = set(str(x) for x in authority.get("certified_scopes") or [])
    expired = set(str(x) for x in freshness.get("expired_scopes") or [])
    stale = set(str(x) for x in freshness.get("stale_scopes") or [])
    impact_by_scope = {str(row.get("scope") or ""): str(row.get("classification") or "") for row in migration.get("scope_impacts") or []}
    return [
        {
            "scope": scope,
            "certified": scope in certified,
            "evidence_expired": scope in expired,
            "evidence_stale": scope in stale,
            "migration_classification": impact_by_scope.get(scope, "not_assessed"),
            "authority_inferred": False,
            "content_free": True,
        }
        for scope in SCOPES
    ]


def _current_components(runtime_root: str | Path | None) -> dict[str, dict[str, Any]]:
    return {
        "handoff": operator_selected_handoff_status(runtime_root=runtime_root),
        "installation": installation_transaction_status(runtime_root=runtime_root),
        "installation_recovery": inspect_installation_transaction(runtime_root=runtime_root),
        "installed": installed_state_status(runtime_root=runtime_root),
        "promotion": promotion_transaction_status(runtime_root=runtime_root),
        "certification": certification_status(runtime_root=runtime_root),
        "certification_recovery": certification_recovery_status(runtime_root=runtime_root),
        "freshness": evidence_freshness_status(runtime_root=runtime_root),
        "recertification": recertification_readiness_status(runtime_root=runtime_root),
        "history": certification_history_status(runtime_root=runtime_root),
        "policy": certification_policy_status(runtime_root=runtime_root),
        "migration": policy_migration_status(runtime_root=runtime_root),
        "authority": certification_authority_coherence_status(runtime_root=runtime_root),
    }


def _binding(components: Mapping[str, Mapping[str, Any]], runtime_root: str | Path | None) -> dict[str, Any]:
    h = components["handoff"]
    i = components["installation"]
    installed = components["installed"]
    p = components["promotion"]
    c = components["certification"]
    history = components["history"]
    policy = components["policy"]
    migration = components["migration"]
    authority = components["authority"]
    return {
        "runtime_root_identity_sha256": _runtime_identity(runtime_root),
        "candidate_id": str(h.get("candidate_id") or i.get("candidate_id") or installed.get("candidate_id") or ""),
        "packaged_version": str(h.get("packaged_version") or i.get("packaged_version") or installed.get("packaged_version") or ""),
        "source_manifest_sha256": str(h.get("source_manifest_sha256") or i.get("source_manifest_sha256") or installed.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(h.get("archive_manifest_sha256") or i.get("archive_manifest_sha256") or installed.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(h.get("archive_sha256") or i.get("archive_sha256") or installed.get("archive_sha256") or ""),
        "installation_transaction_id": str(i.get("transaction_id") or ""),
        "installation_transaction_identity_sha256": str(i.get("transaction_identity_sha256") or ""),
        "installed_receipt_sha256": str(installed.get("installed_receipt_sha256") or p.get("installed_receipt_sha256") or ""),
        "target_project_id": str(installed.get("target_project_id") or p.get("target_project_id") or ""),
        "target_inventory_sha256": str(installed.get("target_inventory_sha256") or p.get("target_inventory_sha256") or ""),
        "promotion_transaction_id": str(p.get("promotion_transaction_id") or ""),
        "promotion_transaction_identity_sha256": str(p.get("promotion_transaction_identity_sha256") or ""),
        "promotion_receipt_sha256": str(p.get("promotion_receipt_sha256") or c.get("promotion_receipt_sha256") or ""),
        "promotion_state_sha256": str(p.get("promotion_state_sha256") or installed.get("promotion_state_sha256") or ""),
        "certification_transaction_id": str(c.get("certification_transaction_id") or ""),
        "certification_receipt_sha256": str(c.get("certification_receipt_sha256") or ""),
        "certification_state_sha256": str(c.get("certification_state_sha256") or ""),
        "certification_generation": int(c.get("generation") or 0),
        "certified_scopes_sha256": digest_payload(sorted(str(x) for x in authority.get("certified_scopes") or [])),
        "history_sha256": str(history.get("history_sha256") or authority.get("history_sha256") or ""),
        "history_generation": int(history.get("generation") or 0),
        "authority_generation": int(history.get("authority_generation") or c.get("generation") or 0),
        "authority_state_sha256": str(history.get("authority_state_sha256") or c.get("certification_state_sha256") or ""),
        "policy_id": str(policy.get("policy_id") or ""),
        "policy_sha256": str(policy.get("policy_sha256") or ""),
        "policy_generation": int(policy.get("generation") or 0),
        "migration_preview_id": str(migration.get("preview_id") or ""),
        "migration_preview_sha256": digest_payload({
            "preview_id": str(migration.get("preview_id") or ""),
            "history_sha256": str(migration.get("history_sha256") or ""),
            "policy_sha256": str(migration.get("policy_sha256") or ""),
            "scope_impacts": migration.get("scope_impacts") or [],
        }),
    }


def _findings(components: Mapping[str, Mapping[str, Any]], binding: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expected = {
        "handoff": {"coherent_preview"},
        "installation": {"installed_unpromoted"},
        "installation_recovery": {"installed_unpromoted"},
        "installed": {"promoted", "partially_certified", "certified"},
        "promotion": {"promoted_uncertified"},
        "certification": {"scope_certified", "partially_certified", "certified"},
        "certification_recovery": {"certification_decision_complete"},
        "history": {"certification_history_coherent"},
        "policy": {"certification_policy_selected"},
        "migration": {"policy_migration_preview_current"},
        "authority": {"certification_authority_coherent"},
    }
    for name, statuses in expected.items():
        row = components[name]
        if not row.get("ok") or str(row.get("status") or "") not in statuses:
            findings.append({"kind": f"{name}_not_release_ready"})
    recovery = components["certification_recovery"]
    if recovery.get("recovery_available"):
        findings.append({"kind": "certification_recovery_pending"})
    install_recovery = components["installation_recovery"]
    if install_recovery.get("resume_available") or str(install_recovery.get("status") or "") in {"resume_ready", "rollback_ready", "uncertain", "live_owner"}:
        findings.append({"kind": "installation_recovery_pending"})
    freshness = components["freshness"]
    for scope in freshness.get("expired_scopes") or []:
        findings.append({"kind": f"expired_evidence_{scope}"})
    for scope in freshness.get("stale_scopes") or []:
        findings.append({"kind": f"stale_evidence_{scope}"})
    migration = components["migration"]
    for row in migration.get("scope_impacts") or []:
        if str(row.get("scope") or "") == "general_release" and str(row.get("classification") or "") not in {"compatible", "no_change"}:
            findings.append({"kind": "general_release_policy_migration_required"})
    authority = components["authority"]
    if not authority.get("general_release_certified"):
        findings.append({"kind": "general_release_not_certified"})
    # Scope separation is explicit. One certified scope never supplies another.
    for scope, field in (("native_windows", "native_windows_certified"), ("provider_ollama", "provider_ollama_certified"), ("model_specific", "model_specific_certified")):
        if bool(authority.get(f"{scope}_inferred")):
            findings.append({"kind": f"{scope}_authority_inferred"})
    # Exact cross-layer identity checks.
    comparisons = {
        "candidate_id": ("handoff", "installation", "installed", "promotion", "certification", "history"),
        "archive_sha256": ("handoff", "installation", "installed", "promotion", "certification", "history"),
        "installed_receipt_sha256": ("installed", "promotion", "certification", "history"),
        "promotion_receipt_sha256": ("promotion", "certification", "history"),
        "target_project_id": ("installation", "installed", "promotion", "certification", "history"),
        "target_inventory_sha256": ("installed", "promotion", "certification"),
    }
    aliases = {"handoff": {"target_inventory_sha256": ""}, "installation": {"target_inventory_sha256": "target_current_inventory_sha256"}}
    for field, names in comparisons.items():
        values: list[str] = []
        for name in names:
            row = components[name]
            key = aliases.get(name, {}).get(field, field)
            if not key:
                continue
            value = str(row.get(key) or "")
            if value:
                values.append(value)
        if values and len(set(values)) > 1:
            findings.append({"kind": f"cross_layer_{field}_mismatch"})
    required = ("candidate_id", "source_manifest_sha256", "archive_manifest_sha256", "archive_sha256", "installation_transaction_id", "installed_receipt_sha256", "target_project_id", "target_inventory_sha256", "promotion_transaction_id", "promotion_receipt_sha256", "certification_receipt_sha256", "history_sha256", "policy_sha256", "migration_preview_sha256", "runtime_root_identity_sha256")
    for field in required:
        if not binding.get(field):
            findings.append({"kind": f"release_authority_binding_{field}_missing"})
    return findings


def _summary(components: Mapping[str, Mapping[str, Any]], runtime_root: str | Path | None) -> dict[str, Any]:
    binding = _binding(components, runtime_root)
    findings = _findings(components, binding)
    counted = _counts(findings)
    authority = components["authority"]
    migration = components["migration"]
    freshness = components["freshness"]
    return {
        "ok": not counted,
        "status": "release_authority_ready" if not counted else "release_authority_not_ready",
        "contract_version": RELEASE_AUTHORITY_READINESS_CONTRACT_VERSION,
        **binding,
        "source_candidate_ready": bool(components["handoff"].get("candidate_fresh")),
        "package_coherent": bool(components["handoff"].get("package_coherent")),
        "installed_state": str(components["installed"].get("status") or ""),
        "installed": bool(components["installed"].get("installed")),
        "promoted_release_authority": bool(components["installed"].get("promoted")) and str(components["promotion"].get("status") or "") == "promoted_uncertified",
        "general_release_certified": bool(authority.get("general_release_certified")),
        "native_windows_certified": bool(authority.get("native_windows_certified")),
        "provider_ollama_certified": bool(authority.get("provider_ollama_certified")),
        "model_specific_certified": bool(authority.get("model_specific_certified")),
        "scope_statuses": _scope_rows(authority, migration, freshness),
        "history_status": str(components["history"].get("status") or ""),
        "policy_status": str(components["policy"].get("status") or ""),
        "migration_status": str(migration.get("status") or ""),
        "evidence_freshness_status": str(freshness.get("status") or ""),
        "certification_recovery_status": str(components["certification_recovery"].get("status") or ""),
        "installation_recovery_status": str(components["installation_recovery"].get("status") or ""),
        "recertification_status": str(components["recertification"].get("status") or ""),
        "findings": counted,
        "finding_count": sum(int(x["count"]) for x in counted),
        "installation_inferred": False,
        "promotion_inferred": False,
        "general_release_certification_inferred": False,
        "native_windows_inferred": False,
        "provider_ollama_inferred": False,
        "model_specific_inferred": False,
        "read_only": True,
        "preview_first": True,
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


def create_release_authority_readiness_preview(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    components = _current_components(runtime_root)
    summary = _summary(components, runtime_root)
    directory = release_authority_readiness_directory(runtime_root)
    pointer = read_json(directory / "active_readiness.json")
    generation = int(pointer.get("generation") or 0) + 1
    record = {
        "schema": READINESS_SCHEMA,
        "preview_id": f"release-authority-readiness-{generation}-{secrets.token_hex(8)}",
        "generation": generation,
        "created_at": utc_now(),
        **summary,
    }
    record["readiness_binding_sha256"] = digest_payload({key: record.get(key) for key in sorted(_binding(components, runtime_root))})
    record["record_sha256"] = _record_digest(record)
    atomic_json(directory / "previews" / f"{record['preview_id']}.json", record)
    if record.get("ok"):
        atomic_json(directory / "active_readiness.json", {
            "schema": READINESS_SCHEMA,
            "preview_id": record["preview_id"],
            "generation": generation,
            "readiness_binding_sha256": record["readiness_binding_sha256"],
            "record_sha256": record["record_sha256"],
            "content_free": True,
        })
    else:
        atomic_json(directory / "last_failed_readiness.json", record)
    return _public(record)


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    findings = _counts(row.get("findings") if isinstance(row.get("findings"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not findings,
        "status": str(row.get("status") or "release_authority_readiness_not_previewed"),
        "contract_version": RELEASE_AUTHORITY_READINESS_CONTRACT_VERSION,
        "preview_id": str(row.get("preview_id") or ""),
        "generation": int(row.get("generation") or 0),
        "readiness_binding_sha256": str(row.get("readiness_binding_sha256") or ""),
        "runtime_root_identity_sha256": str(row.get("runtime_root_identity_sha256") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "packaged_version": str(row.get("packaged_version") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(row.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "installation_transaction_id": str(row.get("installation_transaction_id") or ""),
        "installation_transaction_identity_sha256": str(row.get("installation_transaction_identity_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "promotion_transaction_id": str(row.get("promotion_transaction_id") or ""),
        "promotion_transaction_identity_sha256": str(row.get("promotion_transaction_identity_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "promotion_state_sha256": str(row.get("promotion_state_sha256") or ""),
        "certification_transaction_id": str(row.get("certification_transaction_id") or ""),
        "certification_receipt_sha256": str(row.get("certification_receipt_sha256") or ""),
        "certification_state_sha256": str(row.get("certification_state_sha256") or ""),
        "certification_generation": int(row.get("certification_generation") or 0),
        "history_sha256": str(row.get("history_sha256") or ""),
        "history_generation": int(row.get("history_generation") or 0),
        "authority_generation": int(row.get("authority_generation") or 0),
        "authority_state_sha256": str(row.get("authority_state_sha256") or ""),
        "policy_id": str(row.get("policy_id") or ""),
        "policy_sha256": str(row.get("policy_sha256") or ""),
        "policy_generation": int(row.get("policy_generation") or 0),
        "migration_preview_id": str(row.get("migration_preview_id") or ""),
        "migration_preview_sha256": str(row.get("migration_preview_sha256") or ""),
        "source_candidate_ready": bool(row.get("source_candidate_ready")),
        "package_coherent": bool(row.get("package_coherent")),
        "installed_state": str(row.get("installed_state") or ""),
        "installed": bool(row.get("installed")),
        "promoted_release_authority": bool(row.get("promoted_release_authority")),
        "general_release_certified": bool(row.get("general_release_certified")),
        "native_windows_certified": bool(row.get("native_windows_certified")),
        "provider_ollama_certified": bool(row.get("provider_ollama_certified")),
        "model_specific_certified": bool(row.get("model_specific_certified")),
        "scope_statuses": list(row.get("scope_statuses") or []),
        "history_status": str(row.get("history_status") or ""),
        "policy_status": str(row.get("policy_status") or ""),
        "migration_status": str(row.get("migration_status") or ""),
        "evidence_freshness_status": str(row.get("evidence_freshness_status") or ""),
        "certification_recovery_status": str(row.get("certification_recovery_status") or ""),
        "installation_recovery_status": str(row.get("installation_recovery_status") or ""),
        "recertification_status": str(row.get("recertification_status") or ""),
        "findings": findings,
        "finding_count": sum(int(x["count"]) for x in findings),
        "installation_inferred": False,
        "promotion_inferred": False,
        "general_release_certification_inferred": False,
        "native_windows_inferred": False,
        "provider_ollama_inferred": False,
        "model_specific_inferred": False,
        "read_only": True,
        "preview_first": True,
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


def release_authority_readiness_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = release_authority_readiness_directory(runtime_root)
    pointer = read_json(directory / "active_readiness.json")
    preview_id = str(pointer.get("preview_id") or "")
    if not preview_id:
        return _public({"ok": True, "status": "release_authority_readiness_not_previewed"})
    record = read_json(directory / "previews" / f"{preview_id}.json")
    findings: list[dict[str, Any]] = []
    if not record or str(record.get("record_sha256") or "") != _record_digest(record):
        findings.append({"kind": "release_authority_readiness_record_invalid"})
    for field in ("preview_id", "generation", "readiness_binding_sha256", "record_sha256"):
        if str(pointer.get(field) or "") != str(record.get(field) or ""):
            findings.append({"kind": f"release_authority_readiness_pointer_{field}_mismatch"})
    components = _current_components(runtime_root)
    current = _summary(components, runtime_root)
    current_binding = digest_payload({key: current.get(key) for key in sorted(_binding(components, runtime_root))})
    if str(record.get("runtime_root_identity_sha256") or "") != _runtime_identity(runtime_root):
        findings.append({"kind": "release_authority_runtime_root_mismatch"})
    if str(record.get("readiness_binding_sha256") or "") != current_binding:
        findings.append({"kind": "release_authority_readiness_stale"})
    findings.extend(current.get("findings") or [])
    out = dict(record)
    out["findings"] = findings
    out["ok"] = not findings
    out["status"] = "release_authority_ready" if not findings else "release_authority_stale_or_contradictory"
    return _public(out)
