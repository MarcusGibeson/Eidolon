from __future__ import annotations

"""v1243 provider fallback and model governance.

This module creates append-only, content-free provider/model registry snapshots,
selection proposals, exact operator reviews, and outage/fallback assessments. It
never contacts a provider, transmits a prompt, changes a default model, edits
configuration, retries generation, resumes execution, or grants model-management
or execution authority.
"""

import html
import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1243.8"
MILESTONE_NAME = "Provider Fallback and Model Governance"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"
MAX_RECORDS = 300

PROVIDER_CLASSES = {"local", "remote"}
HEALTH_STATES = {"ready", "degraded", "unavailable", "misconfigured", "unknown"}
PRIVACY_TIERS = {"local_only", "redacted_remote", "standard_remote"}
PRIVACY_REQUIREMENTS = {"local_only", "redacted_remote_allowed", "remote_allowed"}
QUALITY_TIERS = {"high", "medium", "low", "unknown"}
LATENCY_TIERS = {"low", "medium", "high", "unknown"}
COST_TIERS = {"none", "low", "medium", "high", "unknown"}
FALLBACK_REASONS = {
    "none", "provider_unavailable", "provider_degraded", "model_unavailable",
    "context_insufficient", "tool_incompatible", "privacy_conflict",
    "capability_mismatch", "operator_requested_review", "health_evidence_stale",
}
SELECTION_DISPOSITIONS = {"accept_selection", "hold", "reject", "request_changes"}
FALLBACK_DISPOSITIONS = {"acknowledge", "hold", "reject_evidence", "request_changes"}
FAILURE_CODES = {
    "none", "connection_failure", "read_timeout", "missing_model", "malformed_response",
    "unsupported_capability", "configuration_error", "provider_outage", "cancelled",
    "unknown_failure",
}
RECOMMENDED_ACTIONS = {
    "no_action", "prepare_new_selection_proposal", "refresh_registry_and_reprepare",
    "hold_for_evidence", "manual_reconciliation_required", "operator_privacy_review_required",
}

AUTHORITY_FLAGS = {
    "provider_registry_inspection_authorized": True,
    "provider_registry_snapshot_preparation_authorized": True,
    "provider_selection_proposal_preparation_authorized": True,
    "provider_selection_review_authorized": True,
    "provider_fallback_assessment_preparation_authorized": True,
    "provider_fallback_review_authorized": True,
    "provider_contact_authorized": False,
    "provider_execution_authorized": False,
    "prompt_transmission_authorized": False,
    "response_acceptance_authorized": False,
    "provider_switch_authorized": False,
    "default_model_change_authorized": False,
    "provider_configuration_change_authorized": False,
    "model_management_authorized": False,
    "model_download_authorized": False,
    "model_installation_authorized": False,
    "automatic_fallback_authorized": False,
    "automatic_retry_authorized": False,
    "automatic_resume_authorized": False,
    "tool_invocation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "cognition_write_authorized": False,
    "approval_creation_authorized": False,
    "approval_consumption_authorized": False,
    "background_execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "old_authority_reusable": False,
}

_TOKEN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_PROVIDER_ID = re.compile(r"^provider_[a-z0-9_]{2,48}$")
_MODEL_ID = re.compile(r"^model_[a-z0-9_]{2,48}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_ORCHESTRATION_ID = re.compile(r"^orchestration_plan_[a-f0-9]{24}$")
_SESSION_ID = re.compile(r"^(?:session|prepared_session|launch|execution_session)_[a-z0-9_\-]{2,80}$")
_PRIVATE = ("path", "secret", "password", "token", "credential", "prompt", "content", "endpoint", "url", "private")

_REVIEW_SELECTION = re.compile(
    r"^review provider model selection (?P<decision>accept_selection|hold|reject|request_changes) "
    r"for proposal (?P<proposal>provider_selection_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_REVIEW_FALLBACK = re.compile(
    r"^review provider fallback (?P<decision>acknowledge|hold|reject_evidence|request_changes) "
    r"for assessment (?P<assessment>provider_fallback_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_REGISTRY = re.compile(r"^show provider model governance registry[.!?]*$", re.I)
_SHOW_SNAPSHOTS = re.compile(r"^show provider model registry snapshots[.!?]*$", re.I)
_SHOW_PROPOSALS = re.compile(r"^show provider model selection proposals[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show provider model selection reviews[.!?]*$", re.I)
_SHOW_FALLBACKS = re.compile(r"^show provider fallback assessments[.!?]*$", re.I)
_SHOW_FALLBACK_REVIEWS = re.compile(r"^show provider fallback reviews[.!?]*$", re.I)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _dir(name: str, runtime_root=None) -> Path:
    return _root(runtime_root) / name


def _path(name: str, record_id: str, runtime_root=None) -> Path:
    return _dir(name, runtime_root) / f"{str(record_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "provider-model-governance.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for provider governance lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _hex(value: Any, reason: str, *, allow_empty: bool = False) -> str:
    text = str(value or "").lower().strip()
    if allow_empty and not text:
        return ""
    if not _HEX64.fullmatch(text):
        raise ValueError(reason)
    return text


def _token(value: Any, reason: str, *, pattern: re.Pattern[str] = _TOKEN) -> str:
    text = str(value or "").lower().strip()
    if not pattern.fullmatch(text) or any(part in text for part in _PRIVATE):
        raise ValueError(reason)
    return text


def _tokens(values: Iterable[Any], reason: str) -> list[str]:
    rows = sorted({str(value or "").lower().strip() for value in values or []})
    if any(not _TOKEN.fullmatch(row) or any(part in row for part in _PRIVATE) for row in rows):
        raise ValueError(reason)
    return rows


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "runtime_records_external": True,
        "project_scoped": True,
        "operator_review_required": True,
        "historical_records_immutable": True,
        "exact_registry_health_model_policy_lineage_required": True,
        "fresh_separate_provider_contact_authority_required": True,
        "fresh_separate_execution_authority_required": True,
        "provider_contacted": False,
        "prompt_transmitted": False,
        "response_received": False,
        "provider_switched": False,
        "default_model_changed": False,
        "configuration_changed": False,
        "model_downloaded": False,
        "model_installed": False,
        "commands_executed": False,
        "tests_executed": False,
        "project_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "cognition_written": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_fallback_created": False,
        "automatic_retry_created": False,
        "automatic_resume_created": False,
        "private_prompt_exposed": False,
        "provider_payload_exposed": False,
        "credentials_exposed": False,
        "endpoints_exposed": False,
        "raw_model_inventory_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["provider_model_governance_result_digest"] = _digest(row)
    return row


def provider_model_governance_registry() -> dict[str, Any]:
    result = {
        "ok": True,
        "status": "provider_model_governance_registry_ready",
        "provider_classes": sorted(PROVIDER_CLASSES),
        "health_states": sorted(HEALTH_STATES),
        "privacy_tiers": sorted(PRIVACY_TIERS),
        "privacy_requirements": sorted(PRIVACY_REQUIREMENTS),
        "fallback_reasons": sorted(FALLBACK_REASONS),
        "selection_dispositions": sorted(SELECTION_DISPOSITIONS),
        "fallback_dispositions": sorted(FALLBACK_DISPOSITIONS),
        "failure_codes": sorted(FAILURE_CODES),
        "recommended_actions": sorted(RECOMMENDED_ACTIONS),
        "inspection_only": True,
        **_base(),
    }
    result["registry_digest"] = _digest(result)
    return result


def _normalize_models(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in values or []:
        model_id = _token(raw.get("model_id"), "invalid_model_id", pattern=_MODEL_ID)
        if model_id in seen:
            raise ValueError("duplicate_model_id")
        seen.add(model_id)
        context_window = int(raw.get("context_window") or 0)
        if context_window < 128 or context_window > 2_000_000:
            raise ValueError("invalid_context_window")
        quality = str(raw.get("quality_tier") or "unknown").lower()
        latency = str(raw.get("latency_tier") or "unknown").lower()
        cost = str(raw.get("cost_tier") or "unknown").lower()
        if quality not in QUALITY_TIERS or latency not in LATENCY_TIERS or cost not in COST_TIERS:
            raise ValueError("invalid_model_tradeoff_tier")
        rows.append({
            "model_id": model_id,
            "capability_codes": _tokens(raw.get("capability_codes") or [], "invalid_model_capability"),
            "context_window": context_window,
            "tool_support": bool(raw.get("tool_support")),
            "streaming_support": bool(raw.get("streaming_support")),
            "quality_tier": quality,
            "latency_tier": latency,
            "cost_tier": cost,
            "model_evidence_digest": _hex(raw.get("model_evidence_digest"), "invalid_model_evidence_digest"),
            "enabled": bool(raw.get("enabled", True)),
        })
    if not rows:
        raise ValueError("provider_model_required")
    return sorted(rows, key=lambda row: row["model_id"])


def _normalize_providers(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in values or []:
        provider_id = _token(raw.get("provider_id"), "invalid_provider_id", pattern=_PROVIDER_ID)
        if provider_id in seen:
            raise ValueError("duplicate_provider_id")
        seen.add(provider_id)
        provider_class = str(raw.get("provider_class") or "").lower()
        health_state = str(raw.get("health_state") or "").lower()
        privacy_tier = str(raw.get("privacy_tier") or "").lower()
        if provider_class not in PROVIDER_CLASSES:
            raise ValueError("invalid_provider_class")
        if health_state not in HEALTH_STATES:
            raise ValueError("invalid_provider_health_state")
        if privacy_tier not in PRIVACY_TIERS:
            raise ValueError("invalid_provider_privacy_tier")
        if provider_class == "local" and privacy_tier != "local_only":
            raise ValueError("local_provider_must_be_local_only")
        if provider_class == "remote" and privacy_tier == "local_only":
            raise ValueError("remote_provider_cannot_claim_local_only")
        rows.append({
            "provider_id": provider_id,
            "provider_class": provider_class,
            "health_state": health_state,
            "privacy_tier": privacy_tier,
            "capability_codes": _tokens(raw.get("capability_codes") or [], "invalid_provider_capability"),
            "tool_support": bool(raw.get("tool_support")),
            "streaming_support": bool(raw.get("streaming_support")),
            "health_evidence_digest": _hex(raw.get("health_evidence_digest"), "invalid_health_evidence_digest"),
            "configuration_digest": _hex(raw.get("configuration_digest"), "invalid_configuration_digest"),
            "governance_policy_digest": _hex(raw.get("governance_policy_digest"), "invalid_provider_policy_digest"),
            "models": _normalize_models(raw.get("models") or []),
        })
    if not rows:
        raise ValueError("provider_registry_required")
    return sorted(rows, key=lambda row: row["provider_id"])


def prepare_provider_model_registry_snapshot(
    providers: Iterable[Mapping[str, Any]],
    *,
    registry_policy_digest: str,
    snapshot_evidence_digest: str,
    registry_generation: int,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        rows = _normalize_providers(providers)
        policy = _hex(registry_policy_digest, "invalid_registry_policy_digest")
        evidence = _hex(snapshot_evidence_digest, "invalid_snapshot_evidence_digest")
        generation = int(registry_generation)
        if generation < 1 or generation > 1_000_000:
            raise ValueError("invalid_registry_generation")
    except (ValueError, TypeError) as exc:
        return _failure("provider_model_registry_snapshot_blocked", str(exc))
    basis = {"providers": rows, "registry_policy_digest": policy, "snapshot_evidence_digest": evidence, "registry_generation": generation}
    snapshot_id = f"provider_registry_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": True,
        "status": "provider_model_registry_snapshot_ready",
        "snapshot_id": snapshot_id,
        **basis,
        "provider_count": len(rows),
        "model_count": sum(len(provider["models"]) for provider in rows),
        "local_provider_count": sum(provider["provider_class"] == "local" for provider in rows),
        "remote_provider_count": sum(provider["provider_class"] == "remote" for provider in rows),
        "health_evidence_digest_bound": True,
        "configuration_digest_bound": True,
        "provider_and_model_names_sanitized": True,
        **_base(),
    }, "registry_record_digest")
    with _lock(runtime_root):
        path = _path("provider_model_registry_snapshots", snapshot_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "registry_record_digest"), **existing, **_base()}
        _atomic_json(path, row)
    return row


def load_provider_model_registry_snapshot(snapshot_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path("provider_model_registry_snapshots", snapshot_id, runtime_root))
    if not row:
        return _failure("provider_model_registry_snapshot_missing", snapshot_id)
    if not _valid(row, "registry_record_digest"):
        return _failure("provider_model_registry_snapshot_tampered", snapshot_id)
    return {"ok": bool(row.get("ok")), **row, **_base()}


def _compatibility(provider: Mapping[str, Any], model: Mapping[str, Any], *, privacy_requirement: str, required_capabilities: list[str], minimum_context_window: int, tools_required: bool, streaming_required: bool) -> list[str]:
    issues: list[str] = []
    if provider.get("health_state") != "ready":
        issues.append(f"provider_{provider.get('health_state')}")
    if not model.get("enabled"):
        issues.append("model_disabled")
    combined = set(provider.get("capability_codes") or []) | set(model.get("capability_codes") or [])
    if not set(required_capabilities).issubset(combined):
        issues.append("required_capability_missing")
    if int(model.get("context_window") or 0) < minimum_context_window:
        issues.append("context_window_insufficient")
    if tools_required and not (provider.get("tool_support") and model.get("tool_support")):
        issues.append("tool_support_missing")
    if streaming_required and not (provider.get("streaming_support") and model.get("streaming_support")):
        issues.append("streaming_support_missing")
    provider_class = str(provider.get("provider_class") or "")
    privacy_tier = str(provider.get("privacy_tier") or "")
    if privacy_requirement == "local_only" and provider_class != "local":
        issues.append("local_only_privacy_conflict")
    if privacy_requirement == "redacted_remote_allowed" and provider_class == "remote" and privacy_tier != "redacted_remote":
        issues.append("redacted_remote_policy_conflict")
    return sorted(set(issues))


def prepare_provider_model_selection(
    project_id: str,
    *,
    task_digest: str,
    registry_snapshot_id: str,
    expected_registry_digest: str,
    preferred_provider_id: str,
    preferred_model_id: str,
    privacy_requirement: str,
    required_capabilities: Iterable[Any],
    minimum_context_window: int,
    tools_required: bool,
    streaming_required: bool,
    fallback_reason: str,
    restricted_data_codes: Iterable[Any] = (),
    orchestration_plan_id: str = "",
    orchestration_plan_digest: str = "",
    execution_session_id: str = "",
    execution_session_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    registry = load_provider_model_registry_snapshot(registry_snapshot_id, runtime_root=runtime_root)
    if not registry.get("snapshot_id"):
        return registry
    try:
        project = _token(project_id, "invalid_project_id")
        task = _hex(task_digest, "invalid_task_digest")
        expected = _hex(expected_registry_digest, "invalid_registry_digest")
        if expected != registry.get("registry_record_digest"):
            raise ValueError("stale_or_mismatched_registry_digest")
        preferred_provider = _token(preferred_provider_id, "invalid_preferred_provider_id", pattern=_PROVIDER_ID)
        preferred_model = _token(preferred_model_id, "invalid_preferred_model_id", pattern=_MODEL_ID)
        privacy = str(privacy_requirement or "").lower()
        if privacy not in PRIVACY_REQUIREMENTS:
            raise ValueError("invalid_privacy_requirement")
        capabilities = _tokens(required_capabilities, "invalid_required_capability")
        context_window = int(minimum_context_window)
        if context_window < 128 or context_window > 2_000_000:
            raise ValueError("invalid_minimum_context_window")
        reason = str(fallback_reason or "").lower()
        if reason not in FALLBACK_REASONS:
            raise ValueError("invalid_fallback_reason")
        restricted = _tokens(restricted_data_codes, "invalid_restricted_data_code")
        if orchestration_plan_id:
            if not _ORCHESTRATION_ID.fullmatch(orchestration_plan_id):
                raise ValueError("invalid_orchestration_plan_id")
            orchestration_digest = _hex(orchestration_plan_digest, "invalid_orchestration_plan_digest")
        else:
            orchestration_digest = _hex(orchestration_plan_digest, "unexpected_orchestration_plan_digest", allow_empty=True)
            if orchestration_digest:
                raise ValueError("orchestration_plan_id_required")
        if execution_session_id:
            if not _SESSION_ID.fullmatch(execution_session_id):
                raise ValueError("invalid_execution_session_id")
            session_digest = _hex(execution_session_digest, "invalid_execution_session_digest")
        else:
            session_digest = _hex(execution_session_digest, "unexpected_execution_session_digest", allow_empty=True)
            if session_digest:
                raise ValueError("execution_session_id_required")
    except (ValueError, TypeError) as exc:
        return _failure("provider_model_selection_blocked", str(exc))

    candidates: list[dict[str, Any]] = []
    preferred_found = False
    for provider in registry.get("providers") or []:
        for model in provider.get("models") or []:
            is_preferred = provider.get("provider_id") == preferred_provider and model.get("model_id") == preferred_model
            preferred_found = preferred_found or is_preferred
            issues = _compatibility(provider, model, privacy_requirement=privacy, required_capabilities=capabilities, minimum_context_window=context_window, tools_required=bool(tools_required), streaming_required=bool(streaming_required))
            candidates.append({
                "provider_id": provider.get("provider_id"),
                "model_id": model.get("model_id"),
                "provider_class": provider.get("provider_class"),
                "privacy_tier": provider.get("privacy_tier"),
                "health_state": provider.get("health_state"),
                "context_window": model.get("context_window"),
                "quality_tier": model.get("quality_tier"),
                "latency_tier": model.get("latency_tier"),
                "cost_tier": model.get("cost_tier"),
                "compatible": not issues,
                "issue_codes": issues,
                "preferred": is_preferred,
            })
    if not preferred_found:
        return _failure("provider_model_selection_blocked", "preferred_provider_model_missing")
    candidates.sort(key=lambda row: (not row["preferred"], row["provider_class"] != "local", row["provider_id"], row["model_id"]))
    preferred_row = next(row for row in candidates if row["preferred"])
    compatible = [row for row in candidates if row["compatible"]]
    selected: dict[str, Any] | None = None
    if preferred_row["compatible"] and reason in {"none", "operator_requested_review"}:
        selected = preferred_row
    else:
        selected = next((row for row in compatible if not row["preferred"]), None)
        if selected is None and preferred_row["compatible"]:
            selected = preferred_row
    issues = [] if selected else ["no_compatible_provider_model"]
    if reason == "health_evidence_stale":
        issues.append("fresh_health_evidence_required")
        selected = None
    selection_state = "blocked"
    if selected:
        selection_state = "preferred_ready" if selected["preferred"] else "fallback_proposed"
    tradeoffs: list[str] = []
    if selected and not selected["preferred"]:
        for field in ("quality_tier", "latency_tier", "cost_tier", "provider_class", "privacy_tier"):
            if selected.get(field) != preferred_row.get(field):
                tradeoffs.append(f"{field}_{preferred_row.get(field)}_to_{selected.get(field)}")
    basis = {
        "project_id": project,
        "task_digest": task,
        "registry_snapshot_id": registry_snapshot_id,
        "registry_record_digest": expected,
        "registry_generation": registry.get("registry_generation"),
        "preferred_provider_id": preferred_provider,
        "preferred_model_id": preferred_model,
        "privacy_requirement": privacy,
        "required_capabilities": capabilities,
        "minimum_context_window": context_window,
        "tools_required": bool(tools_required),
        "streaming_required": bool(streaming_required),
        "fallback_reason": reason,
        "restricted_data_codes": restricted,
        "orchestration_plan_id": orchestration_plan_id,
        "orchestration_plan_digest": orchestration_digest,
        "execution_session_id": execution_session_id,
        "execution_session_digest": session_digest,
        "selected_provider_id": selected.get("provider_id") if selected else "",
        "selected_model_id": selected.get("model_id") if selected else "",
    }
    proposal_id = f"provider_selection_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": bool(selected) and not issues,
        "status": "provider_model_selection_ready_for_operator_review" if selected and not issues else "provider_model_selection_blocked",
        "proposal_id": proposal_id,
        **basis,
        "selection_state": selection_state,
        "preferred_compatible": bool(preferred_row["compatible"]),
        "preferred_issue_codes": preferred_row["issue_codes"],
        "candidate_count": len(candidates),
        "compatible_candidate_count": len(compatible),
        "candidate_summaries": candidates,
        "tradeoff_codes": sorted(tradeoffs),
        "privacy_implication_codes": sorted({
            "no_external_data_route" if selected and selected["provider_class"] == "local" else "external_data_route_requires_fresh_approval",
            "restricted_data_must_remain_local" if restricted else "no_restricted_data_codes_declared",
        }),
        "why_preferred_fits_codes": [] if not preferred_row["compatible"] else ["capabilities_compatible", "context_compatible", "privacy_compatible", "health_ready"],
        "why_fallback_needed_codes": sorted(set(preferred_row["issue_codes"] + ([] if reason == "none" else [reason]))),
        "issue_codes": sorted(set(issues)),
        "issue_count": len(set(issues)),
        "selection_acceptable": bool(selected) and not issues,
        "operator_review_phrase": "",
        **_base(),
    }, "proposal_record_digest")
    row["operator_review_phrase"] = f"Review provider model selection accept_selection for proposal {proposal_id} digest {row['proposal_record_digest']}."
    row = _sealed(row, "proposal_record_digest")
    with _lock(runtime_root):
        path = _path("provider_model_selection_proposals", proposal_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "proposal_record_digest") and bool(existing.get("ok")), **existing, **_base()}
        _atomic_json(path, row)
    return row


def load_provider_model_selection(proposal_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path("provider_model_selection_proposals", proposal_id, runtime_root))
    if not row:
        return _failure("provider_model_selection_missing", proposal_id)
    if not _valid(row, "proposal_record_digest"):
        return _failure("provider_model_selection_tampered", proposal_id)
    return {"ok": bool(row.get("ok")), **row, **_base()}


def review_provider_model_selection(proposal_id: str, *, expected_proposal_digest: str, disposition: str, exact_phrase: str, runtime_root=None) -> dict[str, Any]:
    proposal = load_provider_model_selection(proposal_id, runtime_root=runtime_root)
    if not proposal.get("proposal_id"):
        return proposal
    try:
        expected = _hex(expected_proposal_digest, "invalid_proposal_digest")
        decision = str(disposition or "").lower()
        if decision not in SELECTION_DISPOSITIONS:
            raise ValueError("invalid_selection_disposition")
        required = f"Review provider model selection {decision} for proposal {proposal_id} digest {expected}."
        if str(exact_phrase or "") != required:
            raise ValueError("exact_review_phrase_required")
        if expected != proposal.get("proposal_record_digest"):
            raise ValueError("stale_or_mismatched_proposal_digest")
    except ValueError as exc:
        return _failure("provider_model_selection_review_blocked", str(exc))
    basis = {
        "proposal_id": proposal_id,
        "proposal_record_digest": expected,
        "project_id": proposal.get("project_id"),
        "selected_provider_id": proposal.get("selected_provider_id"),
        "selected_model_id": proposal.get("selected_model_id"),
        "disposition": decision,
    }
    review_id = f"provider_selection_review_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": True,
        "status": "provider_model_selection_review_recorded",
        "review_id": review_id,
        **basis,
        "selection_interpretation_accepted": decision == "accept_selection" and bool(proposal.get("selection_acceptable")),
        "operator_follow_up_required": decision != "accept_selection",
        "fresh_provider_contact_authority_still_required": True,
        "provider_contact_authority_created": False,
        "prompt_transmission_authority_created": False,
        "provider_switch_authority_created": False,
        "default_model_change_authority_created": False,
        "execution_resume_authority_created": False,
        **_base(),
    }, "review_record_digest")
    with _lock(runtime_root):
        path = _path("provider_model_selection_reviews", review_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "review_record_digest"), **existing, **_base()}
        _atomic_json(path, row)
    return row


def load_provider_model_selection_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path("provider_model_selection_reviews", review_id, runtime_root))
    if not row:
        return _failure("provider_model_selection_review_missing", review_id)
    if not _valid(row, "review_record_digest"):
        return _failure("provider_model_selection_review_tampered", review_id)
    return {"ok": bool(row.get("ok")), **row, **_base()}


def prepare_provider_fallback_assessment(
    proposal_id: str,
    *,
    expected_proposal_digest: str,
    proposal_review_id: str,
    expected_review_digest: str,
    current_registry_digest: str,
    observed_provider_id: str,
    observed_model_id: str,
    observed_health_state: str,
    health_evidence_digest: str,
    failure_code: str,
    attempt_count: int,
    prompt_was_transmitted: bool,
    response_was_received: bool,
    evidence_complete: bool,
    runtime_root=None,
) -> dict[str, Any]:
    proposal = load_provider_model_selection(proposal_id, runtime_root=runtime_root)
    review = load_provider_model_selection_review(proposal_review_id, runtime_root=runtime_root)
    if not proposal.get("proposal_id") or not review.get("review_id"):
        return _failure("provider_fallback_assessment_blocked", "missing_selection_lineage")
    try:
        expected_proposal = _hex(expected_proposal_digest, "invalid_proposal_digest")
        expected_review = _hex(expected_review_digest, "invalid_review_digest")
        current_registry = _hex(current_registry_digest, "invalid_current_registry_digest")
        provider_id = _token(observed_provider_id, "invalid_observed_provider_id", pattern=_PROVIDER_ID)
        model_id = _token(observed_model_id, "invalid_observed_model_id", pattern=_MODEL_ID)
        health = str(observed_health_state or "").lower()
        if health not in HEALTH_STATES:
            raise ValueError("invalid_observed_health_state")
        evidence = _hex(health_evidence_digest, "invalid_health_evidence_digest")
        failure = str(failure_code or "").lower()
        if failure not in FAILURE_CODES:
            raise ValueError("invalid_failure_code")
        attempts = int(attempt_count)
        if attempts < 0 or attempts > 1000:
            raise ValueError("invalid_attempt_count")
        if expected_proposal != proposal.get("proposal_record_digest") or expected_review != review.get("review_record_digest"):
            raise ValueError("stale_or_mismatched_selection_lineage")
        if review.get("proposal_id") != proposal_id or not review.get("selection_interpretation_accepted"):
            raise ValueError("accepted_selection_review_required")
    except (ValueError, TypeError) as exc:
        return _failure("provider_fallback_assessment_blocked", str(exc))
    issues: list[str] = []
    if provider_id != proposal.get("selected_provider_id") or model_id != proposal.get("selected_model_id"):
        issues.append("observed_provider_model_mismatch")
    if current_registry != proposal.get("registry_record_digest"):
        issues.append("registry_state_changed")
    if not evidence_complete:
        issues.append("fallback_evidence_incomplete")
    if response_was_received and not prompt_was_transmitted:
        issues.append("impossible_response_without_prompt_transmission")
    if proposal.get("privacy_requirement") == "local_only" and prompt_was_transmitted:
        selected = next((row for row in proposal.get("candidate_summaries") or [] if row.get("provider_id") == provider_id and row.get("model_id") == model_id), {})
        if selected.get("provider_class") == "remote":
            issues.append("local_only_privacy_violation_observed")
    if "observed_provider_model_mismatch" in issues or "impossible_response_without_prompt_transmission" in issues:
        action = "manual_reconciliation_required"
    elif "registry_state_changed" in issues:
        action = "refresh_registry_and_reprepare"
    elif "local_only_privacy_violation_observed" in issues:
        action = "operator_privacy_review_required"
    elif not evidence_complete or health == "unknown":
        action = "hold_for_evidence"
    elif health == "ready" and failure == "none":
        action = "no_action"
    else:
        action = "prepare_new_selection_proposal"
    basis = {
        "proposal_id": proposal_id,
        "proposal_record_digest": expected_proposal,
        "proposal_review_id": proposal_review_id,
        "proposal_review_digest": expected_review,
        "project_id": proposal.get("project_id"),
        "current_registry_digest": current_registry,
        "observed_provider_id": provider_id,
        "observed_model_id": model_id,
        "observed_health_state": health,
        "health_evidence_digest": evidence,
        "failure_code": failure,
        "attempt_count": attempts,
        "prompt_was_transmitted": bool(prompt_was_transmitted),
        "response_was_received": bool(response_was_received),
        "evidence_complete": bool(evidence_complete),
    }
    assessment_id = f"provider_fallback_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": not issues,
        "status": "provider_fallback_assessment_ready_for_operator_review" if not issues else "provider_fallback_assessment_attention_required",
        "assessment_id": assessment_id,
        **basis,
        "recommended_action": action,
        "issue_codes": sorted(set(issues)),
        "issue_count": len(set(issues)),
        "new_selection_proposal_only": action == "prepare_new_selection_proposal",
        "automatic_fallback_permitted": False,
        "automatic_retry_permitted": False,
        "automatic_resume_permitted": False,
        "operator_review_phrase": "",
        **_base(),
    }, "assessment_record_digest")
    row["prompt_transmitted"] = bool(prompt_was_transmitted)
    row["response_received"] = bool(response_was_received)
    row["operator_review_phrase"] = f"Review provider fallback acknowledge for assessment {assessment_id} digest {row['assessment_record_digest']}."
    row = _sealed(row, "assessment_record_digest")
    with _lock(runtime_root):
        path = _path("provider_fallback_assessments", assessment_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "assessment_record_digest") and bool(existing.get("ok")), **existing, **_base()}
        _atomic_json(path, row)
    return row


def load_provider_fallback_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path("provider_fallback_assessments", assessment_id, runtime_root))
    if not row:
        return _failure("provider_fallback_assessment_missing", assessment_id)
    if not _valid(row, "assessment_record_digest"):
        return _failure("provider_fallback_assessment_tampered", assessment_id)
    public = {"ok": bool(row.get("ok")), **row, **_base()}
    public["prompt_transmitted"] = bool(row.get("prompt_was_transmitted"))
    public["response_received"] = bool(row.get("response_was_received"))
    return public


def review_provider_fallback(assessment_id: str, *, expected_assessment_digest: str, disposition: str, exact_phrase: str, runtime_root=None) -> dict[str, Any]:
    assessment = load_provider_fallback_assessment(assessment_id, runtime_root=runtime_root)
    if not assessment.get("assessment_id"):
        return assessment
    try:
        expected = _hex(expected_assessment_digest, "invalid_assessment_digest")
        decision = str(disposition or "").lower()
        if decision not in FALLBACK_DISPOSITIONS:
            raise ValueError("invalid_fallback_disposition")
        required = f"Review provider fallback {decision} for assessment {assessment_id} digest {expected}."
        if str(exact_phrase or "") != required:
            raise ValueError("exact_review_phrase_required")
        if expected != assessment.get("assessment_record_digest"):
            raise ValueError("stale_or_mismatched_assessment_digest")
    except ValueError as exc:
        return _failure("provider_fallback_review_blocked", str(exc))
    basis = {
        "assessment_id": assessment_id,
        "assessment_record_digest": expected,
        "proposal_id": assessment.get("proposal_id"),
        "project_id": assessment.get("project_id"),
        "disposition": decision,
    }
    review_id = f"provider_fallback_review_{_digest(basis)[:24]}"
    row = _sealed({
        "ok": True,
        "status": "provider_fallback_review_recorded",
        "review_id": review_id,
        **basis,
        "fallback_interpretation_acknowledged": decision == "acknowledge",
        "recommended_action": assessment.get("recommended_action"),
        "new_selection_authority_created": False,
        "provider_contact_authority_created": False,
        "retry_authority_created": False,
        "resume_authority_created": False,
        "fresh_exact_selection_and_contact_authority_still_required": True,
        **_base(),
    }, "review_record_digest")
    with _lock(runtime_root):
        path = _path("provider_fallback_reviews", review_id, runtime_root)
        existing = _read_json(path)
        if existing:
            return {"ok": _valid(existing, "review_record_digest"), **existing, **_base()}
        _atomic_json(path, row)
    return row


def _project(row: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if key in row}


_SNAPSHOT_PUBLIC = ("ok", "status", "snapshot_id", "registry_record_digest", "registry_policy_digest", "snapshot_evidence_digest", "registry_generation", "provider_count", "model_count", "local_provider_count", "remote_provider_count", "providers", "content_free", "provider_contact_authorized", "model_management_authorized")
_PROPOSAL_PUBLIC = ("ok", "status", "proposal_id", "proposal_record_digest", "project_id", "task_digest", "registry_snapshot_id", "registry_record_digest", "preferred_provider_id", "preferred_model_id", "selected_provider_id", "selected_model_id", "privacy_requirement", "required_capabilities", "minimum_context_window", "tools_required", "streaming_required", "fallback_reason", "restricted_data_codes", "orchestration_plan_id", "orchestration_plan_digest", "execution_session_id", "execution_session_digest", "selection_state", "preferred_compatible", "preferred_issue_codes", "candidate_count", "compatible_candidate_count", "candidate_summaries", "tradeoff_codes", "privacy_implication_codes", "why_preferred_fits_codes", "why_fallback_needed_codes", "issue_codes", "issue_count", "selection_acceptable", "operator_review_phrase", "content_free", "provider_contact_authorized", "prompt_transmission_authorized", "provider_switch_authorized", "default_model_change_authorized", "old_authority_reusable")
_REVIEW_PUBLIC = ("ok", "status", "review_id", "review_record_digest", "proposal_id", "proposal_record_digest", "project_id", "selected_provider_id", "selected_model_id", "disposition", "selection_interpretation_accepted", "operator_follow_up_required", "fresh_provider_contact_authority_still_required", "provider_contact_authority_created", "prompt_transmission_authority_created", "provider_switch_authority_created", "default_model_change_authority_created", "execution_resume_authority_created", "content_free", "old_authority_reusable")
_FALLBACK_PUBLIC = ("ok", "status", "assessment_id", "assessment_record_digest", "proposal_id", "proposal_record_digest", "proposal_review_id", "proposal_review_digest", "project_id", "current_registry_digest", "observed_provider_id", "observed_model_id", "observed_health_state", "health_evidence_digest", "failure_code", "attempt_count", "prompt_was_transmitted", "response_was_received", "evidence_complete", "recommended_action", "issue_codes", "issue_count", "new_selection_proposal_only", "automatic_fallback_permitted", "automatic_retry_permitted", "automatic_resume_permitted", "operator_review_phrase", "content_free", "provider_contact_authorized", "automatic_fallback_authorized", "automatic_retry_authorized", "old_authority_reusable")
_FALLBACK_REVIEW_PUBLIC = ("ok", "status", "review_id", "review_record_digest", "assessment_id", "assessment_record_digest", "proposal_id", "project_id", "disposition", "fallback_interpretation_acknowledged", "recommended_action", "new_selection_authority_created", "provider_contact_authority_created", "retry_authority_created", "resume_authority_created", "fresh_exact_selection_and_contact_authority_still_required", "content_free", "old_authority_reusable")


def _public_list(directory: str, seal_field: str, keys: Iterable[str], plural: str, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _dir(directory, runtime_root)
    if root.exists():
        for path in sorted(root.glob("*.json"))[-MAX_RECORDS:]:
            row = _read_json(path)
            if row and _valid(row, seal_field):
                rows.append(_project(row, keys))
    singular = plural[:-1] if plural.endswith("s") else plural
    return {"ok": True, "status": f"provider_model_governance_{plural}_ready", f"{singular}_count": len(rows), plural: rows, **_base()}


def public_provider_model_registry_snapshots(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("provider_model_registry_snapshots", "registry_record_digest", _SNAPSHOT_PUBLIC, "snapshots", runtime_root)


def public_provider_model_selection_proposals(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("provider_model_selection_proposals", "proposal_record_digest", _PROPOSAL_PUBLIC, "proposals", runtime_root)


def public_provider_model_selection_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("provider_model_selection_reviews", "review_record_digest", _REVIEW_PUBLIC, "reviews", runtime_root)


def public_provider_fallback_assessments(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("provider_fallback_assessments", "assessment_record_digest", _FALLBACK_PUBLIC, "fallback_assessments", runtime_root)


def public_provider_fallback_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("provider_fallback_reviews", "review_record_digest", _FALLBACK_REVIEW_PUBLIC, "fallback_reviews", runtime_root)


def provider_model_governance_dashboard_record(*, runtime_root=None) -> dict[str, Any]:
    snapshots = public_provider_model_registry_snapshots(runtime_root=runtime_root)
    proposals = public_provider_model_selection_proposals(runtime_root=runtime_root)
    reviews = public_provider_model_selection_reviews(runtime_root=runtime_root)
    fallbacks = public_provider_fallback_assessments(runtime_root=runtime_root)
    accepted = {row.get("proposal_id") for row in reviews.get("reviews", []) if row.get("selection_interpretation_accepted")}
    pending = sum(1 for row in proposals.get("proposals", []) if row.get("selection_acceptable") and row.get("proposal_id") not in accepted)
    blocked = sum(1 for row in proposals.get("proposals", []) if row.get("issue_count")) + sum(1 for row in fallbacks.get("fallback_assessments", []) if row.get("issue_count"))
    status = "blocked" if blocked else ("awaiting_review" if pending else ("ready" if snapshots.get("snapshot_count") else "unknown"))
    result = {
        "ok": blocked == 0,
        "status": status,
        "record_id": "provider-model-governance",
        "project_id": "provider-governance",
        "panel_id": "orchestration",
        "summary": "Content-free provider selection, privacy, health, capability, and fallback evidence.",
        "snapshot_count": snapshots.get("snapshot_count", 0),
        "proposal_count": proposals.get("proposal_count", 0),
        "review_count": reviews.get("review_count", 0),
        "fallback_assessment_count": fallbacks.get("fallback_assessment_count", 0),
        "review_required": pending > 0,
        "blocker_count": blocked,
        "authority_state": "none",
        "safe_next_action": "review_exact_provider_selection" if pending else "inspect_provider_governance_evidence",
        "read_only": True,
        **_base(),
    }
    result["record_digest"] = _digest(result)
    return result


def render_provider_model_governance_dashboard_html(*, runtime_root=None) -> str:
    record = provider_model_governance_dashboard_record(runtime_root=runtime_root)
    registry = provider_model_governance_registry()
    cards = "".join(
        f"<article><h2>{html.escape(title)}</h2><p>{html.escape(detail)}</p></article>"
        for title, detail in (
            ("Registry", "Sanitized provider, model, capability, privacy, and health evidence."),
            ("Selection", "Exact preferred-model and fallback compatibility review."),
            ("Privacy", "Local-only and redacted-remote routing constraints remain explicit."),
            ("Authority", "No provider contact, prompt transmission, retry, resume, or model switch authority."),
        )
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Provider and Model Governance</title>"
        "<style>body{font-family:system-ui;background:#090b12;color:#edf3fb;padding:28px}.deck{max-width:1180px;margin:auto}.banner,article{background:#111827;border:1px solid #334155;border-radius:14px;padding:18px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.safe{color:#7dd3fc}.muted{color:#94a3b8}code{color:#c4b5fd}</style></head><body><main class='deck'>"
        f"<section class='banner'><h1>Provider Fallback and Model Governance</h1><p>Status: <strong>{html.escape(str(record['status']))}</strong></p>"
        "<p class='safe'>GET-only inspection. No provider is contacted and no model or default is changed.</p>"
        f"<p class='muted'>Registry contract: {html.escape(str(registry['contract_version']))}</p></section>"
        f"<section class='grid'>{cards}</section><section class='banner'><h2>Read-only surfaces</h2>"
        "<code>/api/cognition/provider-model-governance-registry</code><br><code>/api/cognition/provider-model-registry-snapshots</code><br>"
        "<code>/api/cognition/provider-model-selection-proposals</code><br><code>/api/cognition/provider-fallback-assessments</code>"
        "</section></main></body></html>"
    )


def provider_model_governance_response(row: Mapping[str, Any]) -> str:
    if not row.get("ok"):
        return f"Provider/model governance control was blocked: {row.get('status', 'unknown')} ({row.get('reason', '')})."
    status = str(row.get("status") or "")
    if "review_recorded" in status:
        return "Recorded the exact provider/model governance review. No provider contact, prompt transmission, model switch, retry, resume, or execution authority was created."
    if "ready_for_operator_review" in status:
        return "Prepared content-free provider/model evidence for operator review. No provider was contacted and no prompt or model setting changed."
    return "Provider/model governance records are ready for read-only inspection."


def process_provider_model_governance_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _REVIEW_SELECTION.fullmatch(text)
    if match:
        row = review_provider_model_selection(match.group("proposal"), expected_proposal_digest=match.group("digest"), disposition=match.group("decision"), exact_phrase=text, runtime_root=runtime_root)
        return {"active": True, "response": provider_model_governance_response(row), "provider_model_governance": row}
    match = _REVIEW_FALLBACK.fullmatch(text)
    if match:
        row = review_provider_fallback(match.group("assessment"), expected_assessment_digest=match.group("digest"), disposition=match.group("decision"), exact_phrase=text, runtime_root=runtime_root)
        return {"active": True, "response": provider_model_governance_response(row), "provider_model_governance": row}
    for regex, factory in (
        (_SHOW_REGISTRY, provider_model_governance_registry),
        (_SHOW_SNAPSHOTS, public_provider_model_registry_snapshots),
        (_SHOW_PROPOSALS, public_provider_model_selection_proposals),
        (_SHOW_REVIEWS, public_provider_model_selection_reviews),
        (_SHOW_FALLBACKS, public_provider_fallback_assessments),
        (_SHOW_FALLBACK_REVIEWS, public_provider_fallback_reviews),
    ):
        if regex.fullmatch(text):
            row = factory(runtime_root=runtime_root) if factory is not provider_model_governance_registry else factory()
            return {"active": True, "response": provider_model_governance_response(row), "provider_model_governance": row}
    return {"active": False}


def build_provider_model_governance_contract() -> dict[str, Any]:
    retained_modules = (
        "provider_availability",
        "provider_recovery_evidence",
        "local_model",
        "local_model_configuration",
        "local_model_readiness",
        "multi_tool_orchestration",
        "execution_session_authorization_bounded_launch",
    )
    available = []
    for module_name in retained_modules:
        try:
            __import__(f"conscious_agent.{module_name}")
            available.append(module_name)
        except ImportError:
            try:
                __import__(module_name)
                available.append(module_name)
            except ImportError:
                pass
    return {
        "ok": len(available) == len(retained_modules),
        "status": "provider_model_governance_contract_ready" if len(available) == len(retained_modules) else "provider_model_governance_contract_blocked",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "retained_provider_model_module_count": len(available),
        "retained_provider_model_modules": available,
        "provider_model_capability_registry_digest_bound": True,
        "local_remote_privacy_classification_required": True,
        "health_configuration_and_model_evidence_bound": True,
        "context_tool_streaming_compatibility_checked": True,
        "quality_latency_cost_tradeoffs_recorded": True,
        "fallback_reason_required": True,
        "accepted_selection_is_interpretation_only": True,
        "provider_outage_never_triggers_automatic_fallback": True,
        "fresh_exact_provider_contact_authority_required": True,
        "ordinary_chat_exact_reviews": True,
        "cli_inspection": True,
        "get_only_api_inspection": True,
        "dashboard_read_model_available": True,
        "stale_tamper_replay_privacy_adversarial_hardening_required": True,
        **_base(),
    }
