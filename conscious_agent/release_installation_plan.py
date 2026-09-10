from __future__ import annotations

"""Immutable, preview-only installation plan binding and drift detection."""

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_installation_preview import INSTALLATION_PREVIEW_SCHEMA, PROTECTED_EXACT, PROTECTED_PREFIXES, PROTECTED_SUFFIXES, SOURCE_MANAGED_PREFIXES, SOURCE_MANAGED_ROOT_FILES, _preview_binding, _target_inventory, installation_impact_preview_status, preview_directory
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_installation_preview import (
        INSTALLATION_PREVIEW_SCHEMA,
        PROTECTED_EXACT,
        PROTECTED_PREFIXES,
        PROTECTED_SUFFIXES,
        SOURCE_MANAGED_PREFIXES,
        SOURCE_MANAGED_ROOT_FILES,
        _preview_binding,
        _target_inventory,
        installation_impact_preview_status,
        preview_directory,
    )

INSTALLATION_PLAN_CONTRACT_VERSION = "1"
INSTALLATION_PLAN_SCHEMA = "eidolon-installation-plan-v1"
INSTALLATION_PLAN_DIRECTORY = "release_installation_plans"


def plan_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / INSTALLATION_PLAN_DIRECTORY


def protected_policy_sha256() -> str:
    return digest_payload({
        "contract": "eidolon-installation-protected-policy-v1",
        "protected_exact": sorted(PROTECTED_EXACT),
        "protected_prefixes": sorted(PROTECTED_PREFIXES),
        "protected_suffixes": sorted(PROTECTED_SUFFIXES),
        "source_managed_prefixes": sorted(SOURCE_MANAGED_PREFIXES),
        "source_managed_root_files": sorted(SOURCE_MANAGED_ROOT_FILES),
    })


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _load_active_preview(runtime_root: str | Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = preview_directory(runtime_root)
    pointer = read_json(directory / "active_preview.json")
    preview_id = str(pointer.get("preview_id") or "")
    record = read_json(directory / "records" / f"{preview_id}.json") if preview_id else {}
    return pointer, record


def _plan_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-installation-plan-binding-v1",
        "plan_id": str(record.get("plan_id") or ""),
        "preview_id": str(record.get("preview_id") or ""),
        "preview_binding_sha256": str(record.get("preview_binding_sha256") or ""),
        "handoff_generation": int(record.get("handoff_generation") or 0),
        "handoff_record_binding_sha256": str(record.get("handoff_record_binding_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "packaged_version": str(record.get("packaged_version") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_identity_sha256": str(record.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "effects_sha256": str(record.get("effects_sha256") or ""),
        "protected_policy_sha256": str(record.get("protected_policy_sha256") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    effect_counts = row.get("effect_counts") if isinstance(row.get("effect_counts"), dict) else {}
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": str(row.get("status") or "not_planned"),
        "contract_version": INSTALLATION_PLAN_CONTRACT_VERSION,
        "plan_present": bool(row),
        "plan_id": str(row.get("plan_id") or ""),
        "plan_binding_sha256": str(row.get("plan_binding_sha256") or ""),
        "preview_id": str(row.get("preview_id") or ""),
        "preview_binding_sha256": str(row.get("preview_binding_sha256") or ""),
        "handoff_generation": int(row.get("handoff_generation") or 0),
        "candidate_id": str(row.get("candidate_id") or ""),
        "packaged_version": str(row.get("packaged_version") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(row.get("archive_manifest_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_identity_sha256": str(row.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "effects_sha256": str(row.get("effects_sha256") or ""),
        "protected_policy_sha256": str(row.get("protected_policy_sha256") or ""),
        "effect_counts": {key: int(effect_counts.get(key) or 0) for key in ("add", "replace", "remove", "unchanged", "protected", "conflict", "outside-approved-scope")},
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "preview_revalidated": bool(row.get("preview_revalidated")),
        "target_revalidated": bool(row.get("target_revalidated")),
        "policy_revalidated": bool(row.get("policy_revalidated")),
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "read_only_plan": True,
        "confirmation_token_available": False,
        "staging_available": False,
        "installation_apply_available": False,
        "installation_changed": False,
        "project_registry_changed": False,
        "installed": False,
        "approved": False,
        "promoted": False,
        "certified": False,
    }


def create_installation_plan(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    preview_status = installation_impact_preview_status(runtime_root=runtime_root)
    pointer, preview = _load_active_preview(runtime_root)
    contradictions: list[dict[str, Any]] = []
    if not preview_status.get("ok") or not preview:
        contradictions.append({"kind": "coherent_installation_preview_required"})
    if preview and str(preview.get("preview_binding_sha256") or "") != _preview_binding(preview):
        contradictions.append({"kind": "preview_binding_mismatch"})
    if preview and str(pointer.get("preview_binding_sha256") or "") != str(preview.get("preview_binding_sha256") or ""):
        contradictions.append({"kind": "preview_pointer_binding_mismatch"})
    effects = list(preview.get("effects") or []) if isinstance(preview.get("effects"), list) else []
    effects_sha = digest_payload({"schema": "eidolon-installation-effects-v1", "effects": effects})
    if preview and effects_sha != str(preview.get("effects_sha256") or ""):
        contradictions.append({"kind": "preview_effects_digest_mismatch"})
    policy_sha = protected_policy_sha256()
    material = {
        "preview_id": str(preview.get("preview_id") or ""),
        "preview_binding_sha256": str(preview.get("preview_binding_sha256") or ""),
        "handoff_generation": int(preview.get("handoff_generation") or 0),
        "handoff_record_binding_sha256": str(preview.get("handoff_record_binding_sha256") or ""),
        "candidate_id": str(preview.get("candidate_id") or ""),
        "packaged_version": str(preview.get("packaged_version") or ""),
        "source_manifest_sha256": str(preview.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(preview.get("archive_manifest_sha256") or ""),
        "archive_sha256": str(preview.get("archive_sha256") or ""),
        "target_project_id": str(preview.get("target_project_id") or ""),
        "target_identity_sha256": str(preview.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(preview.get("target_inventory_sha256") or ""),
        "effects_sha256": str(preview.get("effects_sha256") or ""),
        "protected_policy_sha256": policy_sha,
    }
    plan_id = f"installation-plan-{digest_payload(material)[:24]}"
    record = {
        "schema": INSTALLATION_PLAN_SCHEMA,
        "contract_version": INSTALLATION_PLAN_CONTRACT_VERSION,
        "plan_id": plan_id,
        "created_at": utc_now(),
        "ok": not contradictions,
        "status": "bound_plan" if not contradictions else "attention_required",
        **material,
        "selected_archive_path": str(preview.get("selected_archive_path") or ""),
        "extracted_root_path": str(preview.get("extracted_root_path") or ""),
        "target_root_path": str(preview.get("target_root_path") or ""),
        "effects": effects,
        "effect_counts": dict(preview.get("effect_counts") or {}),
        "contradictions": contradictions,
        "preview_revalidated": bool(preview_status.get("ok")),
        "target_revalidated": bool(preview_status.get("target_revalidated")),
        "policy_revalidated": True,
        "read_only_plan": True,
        "content_free": True,
    }
    record["plan_binding_sha256"] = _plan_binding(record)
    directory = plan_directory(runtime_root)
    atomic_json(directory / "records" / f"{plan_id}.json", record)
    if record["ok"]:
        atomic_json(directory / "active_plan.json", {
            "schema": INSTALLATION_PLAN_SCHEMA,
            "plan_id": plan_id,
            "plan_binding_sha256": record["plan_binding_sha256"],
            "preview_id": record["preview_id"],
            "target_project_id": record["target_project_id"],
            "content_free": True,
        })
    return _public(record)


def installation_plan_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory = plan_directory(runtime_root)
    pointer = read_json(directory / "active_plan.json")
    plan_id = str(pointer.get("plan_id") or "")
    if not plan_id:
        return _public({})
    record = read_json(directory / "records" / f"{plan_id}.json")
    if not record:
        return _public({"status": "plan_record_missing", "contradictions": [{"kind": "plan_record_missing"}]})
    contradictions = list(record.get("contradictions") or [])
    if str(pointer.get("plan_binding_sha256") or "") != str(record.get("plan_binding_sha256") or ""):
        contradictions.append({"kind": "plan_pointer_binding_mismatch"})
    if str(record.get("plan_binding_sha256") or "") != _plan_binding(record):
        contradictions.append({"kind": "plan_record_binding_mismatch"})
    preview_status = installation_impact_preview_status(runtime_root=runtime_root)
    _, preview = _load_active_preview(runtime_root)
    if not preview_status.get("ok"):
        contradictions.append({"kind": "installation_preview_stale"})
    if str(preview.get("preview_id") or "") != str(record.get("preview_id") or ""):
        contradictions.append({"kind": "active_preview_changed"})
    if str(preview.get("preview_binding_sha256") or "") != str(record.get("preview_binding_sha256") or ""):
        contradictions.append({"kind": "preview_binding_changed"})
    if str(preview.get("effects_sha256") or "") != str(record.get("effects_sha256") or ""):
        contradictions.append({"kind": "preview_effects_changed"})
    if protected_policy_sha256() != str(record.get("protected_policy_sha256") or ""):
        contradictions.append({"kind": "protected_policy_changed"})
    target_root = Path(str(record.get("target_root_path") or "."))
    inventory = _target_inventory(target_root) if str(record.get("target_root_path") or "") else {"ok": False, "digest": ""}
    if str(inventory.get("digest") or "") != str(record.get("target_inventory_sha256") or ""):
        contradictions.append({"kind": "target_project_changed_after_plan"})
    current = dict(record)
    current["contradictions"] = contradictions
    current["ok"] = not contradictions
    current["status"] = "bound_plan" if not contradictions else "stale_plan"
    current["preview_revalidated"] = bool(preview_status.get("ok"))
    current["target_revalidated"] = bool(inventory.get("ok")) and str(inventory.get("digest") or "") == str(record.get("target_inventory_sha256") or "")
    current["policy_revalidated"] = protected_policy_sha256() == str(record.get("protected_policy_sha256") or "")
    return _public(current)
