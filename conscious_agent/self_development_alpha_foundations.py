from __future__ import annotations

"""v1270.0-v1270.2 Self-Development Alpha campaign foundations.

This module binds the read-only v1261-v1264 judgment chain to one disposable
v1265 self-candidate preparation.  It creates no provider, test, repair,
application, installation, release, or standing self-update authority.
"""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from alternative_planning_foundations import build_alternative_plan
from development_backlog_generation_foundations import build_backlog_from_assessment
from evidence_based_project_inspection import build_evidence_based_project_assessment
from isolated_self_modification_foundations import prepare_isolated_self_modification, source_only_manifest
from ordinary_chat_development_campaign import _proposal_lock
from priority_selection_foundations import select_priority_from_backlog

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1270.2"
MAX_RECORD_BYTES = 8 * 1024 * 1024

ALPHA_DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "repair_authorized": False,
    "active_source_mutation_authorized": False,
    "source_application_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "self_update_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _runtime_root(value: str | Path | None) -> Path:
    if value is None:
        raise ValueError("self_development_alpha_runtime_root_required")
    return Path(value).expanduser().resolve()


def _campaign_path(campaign_id: str, runtime_root: str | Path | None) -> Path:
    if not re.fullmatch(r"selfalpha_[a-f0-9]{24}", str(campaign_id or "")):
        raise ValueError("invalid_self_development_alpha_campaign_id")
    return _runtime_root(runtime_root) / "self_development_alpha" / "campaigns" / f"{campaign_id}.json"


def _stage_root(runtime_root: str | Path | None, stage: str) -> Path:
    return _runtime_root(runtime_root) / "self_development_alpha" / "stages" / stage


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    data = (json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("self_development_alpha_record_too_large")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, suffix=".tmp") as h:
            h.write(data); h.flush(); os.fsync(h.fileno()); tmp = Path(h.name)
        os.replace(tmp, path); tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_RECORD_BYTES:
        raise ValueError("self_development_alpha_record_too_large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("self_development_alpha_record_invalid")
    return value


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in record.items() if k not in {"record_digest", "operation_status"}})


def validate_self_development_alpha_campaign(record: Mapping[str, Any]) -> dict[str, Any]:
    digest_ok = bool(record.get("record_digest")) and record.get("record_digest") == _record_digest(record)
    authority_ok = all(record.get(k) is v for k, v in ALPHA_DENIED_AUTHORITY.items())
    phase = str(record.get("phase") or "")
    semantic = (
        str(record.get("campaign_id") or "").startswith("selfalpha_")
        and phase in {"prepared", "repair_authorization_required", "operator_review_required", "review_decided", "cancelled", "blocked"}
        and bool(record.get("source_manifest_digest"))
        and bool(record.get("assessment_digest"))
        and bool(record.get("backlog_digest"))
        and bool(record.get("selection_digest"))
        and bool(record.get("plan_digest"))
        and record.get("active_source_modified") is False
        and record.get("operator_review_required") is True
    )
    ok = digest_ok and authority_ok and semantic
    return {"ok": ok, "status": "self_development_alpha_campaign_valid" if ok else "self_development_alpha_campaign_invalid", "digest_valid": digest_ok, "authority_contained": authority_ok, "semantic_valid": semantic}


def prepare_self_development_alpha_campaign(
    source_root: str | Path,
    *,
    external_evidence: Iterable[Mapping[str, Any]] = (),
    priority_context: Iterable[Mapping[str, Any]] = (),
    plan_context: Iterable[Mapping[str, Any]] = (),
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    source = Path(source_root).expanduser().resolve(strict=True)
    external_evidence = list(external_evidence)
    priority_context = list(priority_context)
    plan_context = list(plan_context)
    assessment = build_evidence_based_project_assessment(source, external_evidence=external_evidence)
    backlog = build_backlog_from_assessment(assessment)
    selection = select_priority_from_backlog(backlog, priority_context=priority_context)
    plan = build_alternative_plan(selection, backlog, plan_context=plan_context)
    if selection.get("status") != "priority_selected" or plan.get("status") != "alternative_plan_selected":
        raise ValueError("unique_self_development_priority_and_plan_required")
    selfmod = prepare_isolated_self_modification(source, plan, selection, backlog, runtime_root=_stage_root(runtime_root, "v1265"))
    if selfmod.get("mutation_candidate") is not True or not selfmod.get("operation_id"):
        raise ValueError("v1270_requires_mutation_capable_selected_improvement")
    source_manifest = source_only_manifest(source)
    selected_eval = next((r for r in selection.get("evaluations") or [] if r.get("work_item_id") == selection.get("selected_work_item_id")), {})
    selected_approach = next((r for r in plan.get("approaches") or [] if r.get("approach_id") == plan.get("selected_approach_id")), {})
    seed = f"{assessment.get('assessment_digest')}:{backlog.get('backlog_digest')}:{selection.get('selection_digest')}:{plan.get('plan_digest')}:{selfmod.get('operation_id')}"
    campaign_id = "selfalpha_" + hashlib.sha256(seed.encode()).hexdigest()[:24]
    path = _campaign_path(campaign_id, runtime_root)
    with _proposal_lock("devc_" + campaign_id.split("_", 1)[1], _runtime_root(runtime_root)):
        existing = _read_json(path)
        if existing:
            if not validate_self_development_alpha_campaign(existing).get("ok"):
                raise ValueError("stored_self_development_alpha_campaign_invalid")
            return {**existing, "operation_status": "restored"}
        record = {
            "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "status": "self_development_alpha_prepared", "phase": "prepared", "campaign_id": campaign_id,
            "source_manifest_digest": source_manifest["source_manifest_digest"],
            "assessment_digest": assessment.get("assessment_digest", ""), "backlog_digest": backlog.get("backlog_digest", ""),
            "selection_digest": selection.get("selection_digest", ""), "plan_digest": plan.get("plan_digest", ""),
            "selected_work_item_id": selection.get("selected_work_item_id"), "selected_objective_code": selected_eval.get("objective_code", ""),
            "selected_priority_score": selected_eval.get("net_score"), "selected_approach_id": plan.get("selected_approach_id"),
            "selected_strategy_code": selected_approach.get("strategy_code", ""), "selection_confidence": selection.get("selection_confidence", ""),
            "plan_confidence": plan.get("selection_confidence", ""), "candidate_operation_id": selfmod.get("operation_id", ""),
            "candidate_authorization_digest": selfmod.get("authorization_digest", ""), "candidate_authorization_phrase": selfmod.get("authorization_phrase", ""), "repair_id": "", "test_selection_id": "", "review_id": "",
            "improvement_proposed": True, "proposal_is_judgment_not_authority": True, "candidate_materialized": True,
            "candidate_provider_executed": False, "tests_executed": False, "repair_attempt_count": 0,
            "operator_review_required": True, "operator_decision": "pending", "v1269_consideration_ready": False,
            "active_source_modified": False, "content_minimized": True, "private_runtime_content_exposed": False,
            **ALPHA_DENIED_AUTHORITY,
        }
        record["record_digest"] = _record_digest(record)
        _write_json(path, record)
        return {**record, "operation_status": "created"}


def load_self_development_alpha_campaign(campaign_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return _read_json(_campaign_path(campaign_id, runtime_root))


def public_self_development_alpha_campaign(record: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "ok", "status", "phase", "campaign_id", "source_manifest_digest", "assessment_digest", "backlog_digest", "selection_digest", "plan_digest",
        "selected_work_item_id", "selected_objective_code", "selected_priority_score", "selected_approach_id", "selected_strategy_code", "candidate_authorization_phrase",
        "selection_confidence", "plan_confidence", "candidate_operation_id", "test_selection_id", "repair_id", "review_id",
        "improvement_proposed", "candidate_materialized", "candidate_provider_executed", "tests_executed", "repair_attempt_count",
        "operator_review_required", "operator_decision", "v1269_consideration_ready", "active_source_modified", "content_minimized",
    )
    return {k: record.get(k) for k in keys} | ALPHA_DENIED_AUTHORITY


__all__ = [
    "CONTRACT_VERSION", "ALPHA_DENIED_AUTHORITY", "prepare_self_development_alpha_campaign", "load_self_development_alpha_campaign",
    "public_self_development_alpha_campaign", "validate_self_development_alpha_campaign", "_digest", "_record_digest", "_campaign_path", "_stage_root", "_write_json", "_runtime_root",
]
