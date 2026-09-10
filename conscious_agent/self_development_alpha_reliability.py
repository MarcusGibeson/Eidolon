from __future__ import annotations

"""v1270.6-v1270.8 restart, stale-source, cancellation and operator handoff hardening."""

from pathlib import Path
from typing import Any

from isolated_self_modification_foundations import source_only_manifest, load_self_modification
from isolated_self_modification_reliability import cleanup_isolated_self_modification, cancel_isolated_self_modification
from iterative_self_repair_reliability import cancel_iterative_self_repair
from self_development_alpha_foundations import ALPHA_DENIED_AUTHORITY, _campaign_path, _record_digest, _runtime_root, _stage_root, _write_json, load_self_development_alpha_campaign, validate_self_development_alpha_campaign

CONTRACT_VERSION = "v1270.8"


def validate_self_development_alpha_freshness(campaign_id: str, source_root: str | Path, *, runtime_root: str | Path | None) -> dict[str, Any]:
    record = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime_root)
    if not record or not validate_self_development_alpha_campaign(record).get("ok"):
        return {"ok": False, "status": "self_development_alpha_campaign_invalid"}
    current = source_only_manifest(source_root)["source_manifest_digest"]
    selfrec = load_self_modification(str(record.get("candidate_operation_id") or ""), runtime_root=_stage_root(runtime_root, "v1265"))
    lineage_ok = bool(selfrec) and str(selfrec.get("plan_digest") or "") == str(record.get("plan_digest") or "") and str(selfrec.get("objective_code") or "") == str(record.get("selected_objective_code") or "") and str(selfrec.get("authorization_phrase") or "") == str(record.get("candidate_authorization_phrase") or "")
    ok = current == record.get("source_manifest_digest") and record.get("active_source_modified") is False and lineage_ok
    status = "self_development_alpha_source_current" if ok else "self_development_alpha_lineage_or_source_stale"
    return {"ok": ok, "status": status, "expected_source_manifest_digest": record.get("source_manifest_digest", ""), "current_source_manifest_digest": current, "lineage_valid": lineage_ok, "active_source_modified": False, **ALPHA_DENIED_AUTHORITY}


def cancel_self_development_alpha_campaign(campaign_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root); record = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
    if not record:
        return {"ok": False, "status": "self_development_alpha_campaign_missing"}
    if record.get("phase") in {"operator_review_required", "review_decided"}:
        return {"ok": False, "status": "verified_candidate_requires_review_or_cleanup", "active_source_modified": False, **ALPHA_DENIED_AUTHORITY}
    if record.get("repair_id"):
        cancel_iterative_self_repair(str(record["repair_id"]), runtime_root=_stage_root(runtime, "v1267"))
    if record.get("candidate_operation_id"):
        try: cancel_isolated_self_modification(str(record["candidate_operation_id"]), runtime_root=_stage_root(runtime, "v1265"))
        except Exception: pass
        cleanup_isolated_self_modification(str(record["candidate_operation_id"]), runtime_root=_stage_root(runtime, "v1265"))
    updated = dict(record); updated.update({"phase": "cancelled", "status": "self_development_alpha_cancelled", "active_source_modified": False, **ALPHA_DENIED_AUTHORITY})
    updated["record_digest"] = _record_digest(updated); _write_json(_campaign_path(campaign_id, runtime), updated)
    return updated


def inspect_self_development_alpha_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    required = [
        "evidence_based_project_inspection.py", "development_backlog_generation.py", "priority_selection.py", "alternative_planning.py",
        "isolated_self_modification.py", "intelligent_test_selection.py", "iterative_self_repair.py", "operator_review_handoff.py", "governed_self_update.py",
        "self_development_alpha_foundations.py", "self_development_alpha.py", "self_development_alpha_reliability.py",
    ]
    checks = {name.replace(".py", "_present"): (root / "conscious_agent" / name).is_file() for name in required}
    return {"ok": all(checks.values()), "status": "self_development_alpha_health_ready" if all(checks.values()) else "self_development_alpha_health_blocked", "checks": checks, "read_only": True, "active_source_modified": False, **ALPHA_DENIED_AUTHORITY}


def build_self_development_alpha_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_self_development_alpha_health(source_root=source_root)
    return {
        "ok": health["ok"], "contract_version": CONTRACT_VERSION,
        "status": "self_development_alpha_operator_handoff_ready" if health["ok"] else "self_development_alpha_operator_handoff_blocked",
        "milestone_proves": ["inspect_self", "evidence_backlog", "priority_selection", "alternative_plan", "isolated_self_candidate", "intelligent_test_selection", "bounded_repair", "operator_review_packet"],
        "authority_boundaries": ["v1265_exact_candidate_authorization_retained", "v1267_exact_repair_authorization_retained", "v1268_review_is_non_authorizing", "v1269_update_requires_fresh_preflight_and_exact_authorization", "active_source_unchanged_by_v1270_checkpoint"],
        "native_windows_review": ["cross_process_campaign_locking", "ntfs_junction_and_reparse_containment", "long_paths", "restart_between_each_stage", "dashboard_review_usability"],
        "next_bounded_unit": "v1271 Long-Running Work Sessions", "read_only": True, "active_source_modified": False, **ALPHA_DENIED_AUTHORITY,
    }


__all__ = ["CONTRACT_VERSION", "validate_self_development_alpha_freshness", "cancel_self_development_alpha_campaign", "inspect_self_development_alpha_health", "build_self_development_alpha_operator_handoff"]
