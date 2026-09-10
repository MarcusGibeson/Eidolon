from __future__ import annotations

"""Explicit, provider-neutral native conversational experience validation.

The validator sends a bounded set of synthetic conversation fixtures through the
same prompt builder and provider-neutral streaming transport used by Eidolon. It
persists only redacted metrics and classifications. Raw prompts, fixture text,
provider payloads, generated responses, memories, and secrets are never written
to evidence.
"""

import hashlib
import json
import re
import threading
import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality, normalized_content_fingerprint
from conversation_runtime import _AssistantStreamCleaner, _clean_assistant_response
from natural_conversation_quality_evaluation import (
    aggregate_native_conversation_quality,
    evaluate_native_conversation_response,
    native_conversation_scenarios,
)
from provider_neutral_conversation_tuning import build_provider_neutral_tuning_plan
from local_model import (
    LocalModelCancelledError,
    LocalModelClient,
    LocalModelConfig,
    LocalModelError,
)
from local_model_evidence import (
    EVIDENCE_SOURCE_FIXTURE,
    EVIDENCE_SOURCE_NATIVE,
    configuration_digest,
    normalize_evidence_source,
    redact_error,
    sanitize_endpoint,
    utc_timestamp,
)
from paths import DATA_DIR, path_reference
from settings_manager import load_settings


VALIDATION_SCHEMA_VERSION = "4"
CONFIRMATION_PHRASE = "RUN_NATIVE_CONVERSATION_VALIDATION"
EVIDENCE_DIR = DATA_DIR / "native_conversation_validation" / "receipts"
_VALIDATION_LOCK = threading.Lock()
_VALIDATION_ID_RE = re.compile(r"^native_conversation_[A-Za-z0-9_.-]{8,72}$")
_ROLE_LABEL_RE = re.compile(r"^(?:assistant|eidolon)\s*:\s*", re.IGNORECASE)
_PROJECT_CONTAMINATION_RE = re.compile(
    r"\b(?:active project|project status|task queue|release candidate|milestone|verification profile|"
    r"capability list|here are the next steps|development status|operator dashboard)\b",
    re.IGNORECASE,
)
_CAPABILITY_MENU_RE = re.compile(
    r"\b(?:i can help (?:you )?with|here(?:'s| is) what i can do|my capabilities include|choose one of)\b",
    re.IGNORECASE,
)
_SIGNOFF_RE = re.compile(r"\b(?:let me know if you need anything else|feel free to ask|how else can i help)\b[.! ]*$", re.IGNORECASE)
_SUPPORTIVE_SIGNAL_RE = re.compile(
    r"\b(?:that sounds|i hear|makes sense|with you|overwhelming|hard|rough|heavy|take a breath|one thing at a time)\b",
    re.IGNORECASE,
)
_PLAYFUL_SIGNAL_RE = re.compile(
    r"\b(?:cute|charming|tease|flirt|smile|sweet|dangerous|trouble|clever|curious)\b",
    re.IGNORECASE,
)


def _new_validation_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"native_conversation_{stamp}_{uuid.uuid4().hex[:12]}"


def _resolved_validation_id(value: str | None) -> str:
    token = str(value or "").strip() or _new_validation_id()
    if not _VALIDATION_ID_RE.fullmatch(token):
        raise ValueError("Invalid native conversation validation identifier.")
    return token


def _scenarios() -> tuple[dict[str, Any], ...]:
    """Return bounded synthetic fixtures for the current natural-conversation contract."""
    return tuple(scenario.runtime_fixture() for scenario in native_conversation_scenarios())


def _bounded_config(config: LocalModelConfig, timeout_seconds: float) -> LocalModelConfig:
    timeout = max(1.0, min(float(timeout_seconds), 120.0))
    generation = replace(config.generation, max_tokens=min(config.generation.max_tokens, 128))
    return replace(
        config,
        connect_timeout_seconds=min(config.connect_timeout_seconds, timeout),
        read_timeout_seconds=timeout,
        generation=generation,
    ).validated()


def _prompt_for(config: LocalModelConfig, scenario: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    profile = classify_conversation_quality(scenario["message"], scenario["history"])
    packet = build_conversation_prompt(
        user_message=scenario["message"],
        self_model={"name": "Eidolon", "active_goals": []},
        desires={"conversation": "natural, attentive, honest, and appropriately playful"},
        memories=[],
        project_context="Synthetic validation project context. Include only for an explicit operator request.",
        goal_context="Synthetic validation goal context.",
        task_context="Synthetic validation task context.",
        conversation_history=scenario["history"],
        context_size=config.context_size,
        max_tokens=config.generation.max_tokens,
    )
    return packet.prompt, profile.receipt_metrics()


def _quality_checks(
    scenario: dict[str, Any],
    raw_response: str,
    visible_response: str,
    operator_request: bool,
    *,
    actual_classification: str,
) -> dict[str, Any]:
    result = evaluate_native_conversation_response(
        scenario,
        visible_response=visible_response,
        raw_response=raw_response,
        actual_classification=actual_classification,
    )
    summary = result.public_summary()
    # Preserve established receipt keys while making the v1102 scorecard authoritative.
    return {
        "visible_role_label": not result.role_label_clean,
        "provider_role_label_removed": bool(_ROLE_LABEL_RE.match(str(raw_response or "").strip())) and result.role_label_clean,
        "project_report_contamination": not result.operator_separation_clean and not operator_request,
        "capability_menu_contamination": "stock_response_hygiene_risk" in result.issue_codes,
        "unsolicited_signoff": bool(_SIGNOFF_RE.search(str(visible_response or "").strip())),
        "supportive_signal": None,
        "playful_signal": None,
        "continuity_signal": result.continuity_signal,
        "continuity_check_required": result.continuity_signal is not None,
        "usable_visible_response": result.usable_response,
        "response_length_bucket": (
            "empty" if not str(visible_response or "").strip() else
            "short" if len(str(visible_response)) <= 240 else
            "medium" if len(str(visible_response)) <= 800 else "long"
        ),
        "v1102_quality": summary,
        "contains_response_text": False,
        "contains_prompt_text": False,
    }


def _stream_scenario(
    config: LocalModelConfig,
    scenario: dict[str, Any],
    *,
    first_token_budget_ms: int,
    total_budget_ms: int,
) -> tuple[dict[str, Any], str]:
    prompt, classification = _prompt_for(config, scenario)
    started = time.monotonic()
    first_transport_chunk: float | None = None
    first_visible_token: float | None = None
    chunks: list[str] = []
    cleaner = _AssistantStreamCleaner("Eidolon")
    visible_chunks: list[str] = []
    retry_count = 0
    try:
        with LocalModelClient(config) as client:
            for chunk in client.stream(prompt):
                now = time.monotonic()
                if first_transport_chunk is None:
                    first_transport_chunk = now
                text = str(chunk)
                chunks.append(text)
                visible = cleaner.feed(text)
                if visible:
                    if first_visible_token is None and visible.strip():
                        first_visible_token = now
                    visible_chunks.append(visible)
            retry_count = client.last_retry_count
        final_visible = cleaner.finish()
        if final_visible:
            if first_visible_token is None and final_visible.strip():
                first_visible_token = time.monotonic()
            visible_chunks.append(final_visible)
        raw_response = "".join(chunks)
        visible_response = _clean_assistant_response("".join(visible_chunks) or raw_response, "Eidolon")
        if first_visible_token is None and visible_response:
            first_visible_token = time.monotonic()
        elapsed_ms = int((time.monotonic() - started) * 1000)
        transport_first_ms = int((first_transport_chunk - started) * 1000) if first_transport_chunk is not None else None
        first_visible_ms = int((first_visible_token - started) * 1000) if first_visible_token is not None else None
        quality = _quality_checks(
            scenario, raw_response, visible_response, bool(classification["explicit_operator_request"]),
            actual_classification=str(classification["kind"]),
        )
        expected_classification = str(scenario["expected"])
        classification_match = classification["kind"] == expected_classification
        quality_result = quality["v1102_quality"]
        hard_failure = quality_result["status"] == "fail"
        warnings = list(quality_result.get("issue_codes") or ()) if quality_result["status"] == "warn" else []
        if first_visible_ms is None or first_visible_ms > first_token_budget_ms:
            warnings.append("first_visible_token_budget_failed")
        if elapsed_ms > total_budget_ms:
            warnings.append("total_response_budget_failed")
        status = "fail" if hard_failure else "warn" if warnings else "pass"
        row = {
            "scenario_id": scenario["id"],
            "classification": classification,
            "expected_classification": expected_classification,
            "classification_match": classification_match,
            "status": status,
            "completion_state": "completed",
            "recovery_state": "not_needed",
            "request_count": 1,
            "retry_count": retry_count,
            "timings_ms": {
                "first_transport_chunk": transport_first_ms,
                "first_visible_token": first_visible_ms,
                "first_token": first_visible_ms,
                "total": elapsed_ms,
            },
            "stream_counts": {
                "transport_chunks": len(chunks),
                "visible_chunks": len(visible_chunks),
            },
            "performance_budget": {
                "first_token_budget_ms": first_token_budget_ms,
                "first_token_metric": "first_visible_token",
                "first_token_within_budget": first_visible_ms is not None and first_visible_ms <= first_token_budget_ms,
                "total_budget_ms": total_budget_ms,
                "total_within_budget": elapsed_ms <= total_budget_ms,
            },
            "quality_checks": quality,
            "warnings": warnings,
            "error": None,
            "redacted": True,
        }
        fingerprint = hashlib.sha256(normalized_content_fingerprint(visible_response).encode("utf-8")).hexdigest() if visible_response else ""
        return row, fingerprint
    except LocalModelError as error:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        row = {
            "scenario_id": scenario["id"],
            "classification": classification,
            "expected_classification": str(scenario["expected"]),
            "classification_match": classification["kind"] == scenario["expected"],
            "status": "fail",
            "completion_state": "cancelled" if isinstance(error, LocalModelCancelledError) else "failed",
            "recovery_state": "operator_recovery_required" if error.code in {"unavailable_service", "missing_model", "timeout"} else "safe_failure",
            "request_count": 1,
            "retry_count": retry_count,
            "timings_ms": {
                "first_transport_chunk": None,
                "first_visible_token": None,
                "first_token": None,
                "total": elapsed_ms,
            },
            "stream_counts": {"transport_chunks": 0, "visible_chunks": 0},
            "performance_budget": {
                "first_token_budget_ms": first_token_budget_ms,
                "first_token_metric": "first_visible_token",
                "first_token_within_budget": False,
                "total_budget_ms": total_budget_ms,
                "total_within_budget": elapsed_ms <= total_budget_ms,
            },
            "quality_checks": {
                "visible_role_label": False,
                "project_report_contamination": False,
                "usable_visible_response": False,
                "continuity_signal": None,
                "continuity_check_required": bool(scenario.get("continuity_terms")),
                "v1102_quality": {
                    "scenario_id": scenario["id"],
                    "dimension": scenario.get("dimension", "general"),
                    "status": "fail",
                    "score_percent": 0,
                    "issue_codes": ["provider_or_transport_failure"],
                    "contains_message_content": False,
                    "contains_response_text": False,
                    "contains_prompt_text": False,
                },
                "contains_response_text": False,
                "contains_prompt_text": False,
            },
            "warnings": [],
            "error": redact_error(error, service="generation", capability="native_conversation"),
            "redacted": True,
        }
        return row, ""
    except Exception:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        row = {
            "scenario_id": scenario["id"],
            "classification": classification,
            "expected_classification": str(scenario["expected"]),
            "classification_match": classification["kind"] == scenario["expected"],
            "status": "fail",
            "completion_state": "failed",
            "recovery_state": "safe_failure",
            "request_count": 1,
            "retry_count": retry_count,
            "timings_ms": {
                "first_transport_chunk": None,
                "first_visible_token": None,
                "first_token": None,
                "total": elapsed_ms,
            },
            "stream_counts": {"transport_chunks": 0, "visible_chunks": 0},
            "performance_budget": {
                "first_token_budget_ms": first_token_budget_ms,
                "first_token_metric": "first_visible_token",
                "first_token_within_budget": False,
                "total_budget_ms": total_budget_ms,
                "total_within_budget": elapsed_ms <= total_budget_ms,
            },
            "quality_checks": {
                "visible_role_label": False,
                "project_report_contamination": False,
                "usable_visible_response": False,
                "continuity_signal": None,
                "continuity_check_required": bool(scenario.get("continuity_terms")),
                "v1102_quality": {
                    "scenario_id": scenario["id"],
                    "dimension": scenario.get("dimension", "general"),
                    "status": "fail",
                    "score_percent": 0,
                    "issue_codes": ["provider_or_transport_failure"],
                    "contains_message_content": False,
                    "contains_response_text": False,
                    "contains_prompt_text": False,
                },
                "contains_response_text": False,
                "contains_prompt_text": False,
            },
            "warnings": [],
            "error": {
                "code": "validator_internal_error",
                "classification": "internal_error",
                "message": "Native conversation validation failed before a structured provider error was available.",
                "redacted": True,
            },
            "redacted": True,
        }
        return row, ""


def _cancellation_probe(config: LocalModelConfig, total_budget_ms: int) -> dict[str, Any]:
    scenario = {
        "id": "cancellation_probe",
        "message": "Give a calm, detailed explanation of why gardens recover after winter.",
        "history": [],
        "expected": "conversation",
    }
    prompt, classification = _prompt_for(config, scenario)
    started = time.monotonic()
    chunks_seen = 0
    state = "not_started"
    error_payload = None
    try:
        with LocalModelClient(config) as client:
            for chunk in client.stream(prompt):
                if str(chunk):
                    chunks_seen += 1
                    client.cancel()
                    state = "cancellation_requested"
        if state == "cancellation_requested":
            state = "completed_before_cancellation_observed"
        else:
            state = "completed_without_stream_content"
    except LocalModelError as error:
        if isinstance(error, LocalModelCancelledError) or error.code in {"cancelled", "interrupted_stream"}:
            state = "cancelled"
        else:
            state = "failed"
        error_payload = redact_error(error, service="generation", capability="cancellation")
    except Exception:
        state = "failed"
        error_payload = {
            "code": "validator_internal_error",
            "classification": "internal_error",
            "message": "Native cancellation validation failed before a structured provider error was available.",
            "redacted": True,
        }
    elapsed_ms = int((time.monotonic() - started) * 1000)
    return {
        "status": "pass" if state == "cancelled" else "warn" if state == "completed_before_cancellation_observed" else "fail",
        "completion_state": state,
        "classification": classification,
        "chunks_seen_before_cancel": chunks_seen,
        "request_count": 1,
        "retry_count": 0,
        "stream_replayed": False,
        "provider_fallback_used": False,
        "provider_switch_performed": False,
        "timings_ms": {"total": elapsed_ms},
        "total_budget_ms": total_budget_ms,
        "total_within_budget": elapsed_ms <= total_budget_ms,
        "error": error_payload,
        "contains_prompt_text": False,
        "contains_response_text": False,
        "redacted": True,
    }


def _report_status(scenarios: Iterable[dict[str, Any]], cancellation: dict[str, Any]) -> str:
    rows = list(scenarios)
    if not rows:
        return "blocked"
    errors = [row.get("error") for row in rows if isinstance(row.get("error"), dict)]
    if errors and len(errors) == len(rows) and all(error.get("code") == "unavailable_service" for error in errors):
        return "unavailable"
    if any(row.get("status") == "fail" for row in rows) or cancellation.get("status") == "fail":
        return "fail"
    if any(row.get("status") == "warn" for row in rows) or cancellation.get("status") != "pass":
        return "partial"
    return "pass"


def _persist_report(report: dict[str, Any]) -> str:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE_DIR / f"{report['validation_id']}.json"
    report["persisted"] = True
    report["evidence_path"] = path_reference(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    return str(path)


def run_native_conversation_validation(
    *,
    confirmed: bool,
    confirmation: str = "",
    settings: dict[str, Any] | None = None,
    config: LocalModelConfig | None = None,
    timeout_seconds: float = 45.0,
    first_token_budget_ms: int = 8000,
    total_budget_ms: int = 30000,
    validation_id: str | None = None,
    persist: bool = True,
    evidence_source: str = EVIDENCE_SOURCE_NATIVE,
) -> dict[str, Any]:
    """Run one bounded native conversation evaluation after exact confirmation."""
    if not confirmed or str(confirmation or "") != CONFIRMATION_PHRASE:
        return {
            "receipt_schema_version": VALIDATION_SCHEMA_VERSION,
            "receipt_type": "native_conversation_validation",
            "status": "blocked",
            "confirmation_required": True,
            "required_confirmation": CONFIRMATION_PHRASE,
            "native_provider_evidence": False,
            "provider_requests_sent": 0,
            "persisted": False,
            "contains_prompts": False,
            "contains_generated_responses": False,
            "contains_memories": False,
            "contains_provider_payloads": False,
            "automatic_model_management": False,
            "operator_control_preserved": True,
            "quality_scorecard": aggregate_native_conversation_quality(()).public_summary(),
            "provider_neutral_tuning_preview": build_provider_neutral_tuning_plan(None).public_summary(),
        }

    run_id = _resolved_validation_id(validation_id)
    source = normalize_evidence_source(evidence_source)
    evidence_path = EVIDENCE_DIR / f"{run_id}.json"
    with _VALIDATION_LOCK:
        if persist and evidence_path.exists():
            existing = json.loads(evidence_path.read_text(encoding="utf-8"))
            existing["replayed_existing_receipt"] = True
            existing["provider_requests_replayed"] = 0
            return existing

        resolved = _bounded_config(config or LocalModelConfig.from_settings(settings or load_settings()), timeout_seconds)
        started = time.monotonic()
        scenario_rows: list[dict[str, Any]] = []
        fingerprints: list[str] = []
        for scenario in _scenarios():
            row, fingerprint = _stream_scenario(
                resolved,
                scenario,
                first_token_budget_ms=max(1, int(first_token_budget_ms)),
                total_budget_ms=max(1, int(total_budget_ms)),
            )
            scenario_rows.append(row)
            if fingerprint:
                fingerprints.append(fingerprint)
            # Stop after the first transport-level unavailable/missing-model failure.
            error = row.get("error") if isinstance(row.get("error"), dict) else {}
            if error.get("code") in {"unavailable_service", "missing_model", "invalid_configuration"}:
                break

        transport_available = not (
            scenario_rows
            and isinstance(scenario_rows[0].get("error"), dict)
            and scenario_rows[0]["error"].get("code") in {"unavailable_service", "missing_model", "invalid_configuration"}
        )
        cancellation = _cancellation_probe(resolved, max(1, int(total_budget_ms))) if transport_available else {
            "status": "not_run",
            "completion_state": "provider_unavailable",
            "request_count": 0,
            "retry_count": 0,
            "stream_replayed": False,
            "provider_fallback_used": False,
            "provider_switch_performed": False,
            "contains_prompt_text": False,
            "contains_response_text": False,
            "redacted": True,
        }
        duplicate_outputs = len(fingerprints) - len(set(fingerprints))
        total_requests = sum(int(row.get("request_count") or 0) for row in scenario_rows) + int(cancellation.get("request_count") or 0)
        total_retries = sum(int(row.get("retry_count") or 0) for row in scenario_rows) + int(cancellation.get("retry_count") or 0)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        report_status = _report_status(scenario_rows, cancellation)
        quality_scorecard = aggregate_native_conversation_quality(
            (row.get("quality_checks") or {}).get("v1102_quality") or {}
            for row in scenario_rows
        ).public_summary()
        if report_status == "unavailable":
            quality_scorecard["status"] = "unavailable"
        tuning_preview = build_provider_neutral_tuning_plan(quality_scorecard).public_summary()
        report = {
            "receipt_schema_version": VALIDATION_SCHEMA_VERSION,
            "receipt_type": "native_conversation_validation",
            "validation_id": run_id,
            "timestamp": utc_timestamp(),
            "evidence_source": source,
            "native_provider_evidence": source == EVIDENCE_SOURCE_NATIVE,
            "status": report_status,
            "provider": resolved.provider,
            "model": resolved.model,
            "generation_endpoint": sanitize_endpoint(resolved.endpoint),
            "configuration_digest": configuration_digest(resolved),
            "scenarios_planned": len(_scenarios()),
            "scenarios_completed": len(scenario_rows),
            "scenarios": scenario_rows,
            "quality_scorecard": quality_scorecard,
            "provider_neutral_tuning_preview": tuning_preview,
            "quality_contract": "v1102-natural-conversation",
            "recovery": {
                "cancellation": cancellation,
                "stream_retry_policy": "never_replay_streaming_request",
                "configured_non_stream_retry_limit": resolved.retry_limit,
                "provider_recovery_state": (
                    "available" if transport_available else "operator_recovery_required"
                ),
                "automatic_provider_fallback": False,
                "automatic_provider_switch": False,
            },
            "duplicates": {
                "provider_requests": 0,
                "visible_responses": max(0, duplicate_outputs),
                "messages": 0,
                "memories": 0,
                "actions": 0,
                "reflections": 0,
                "mutation_receipts": 0,
            },
            "counts": {
                "provider_requests_sent": total_requests,
                "provider_retries": total_retries,
                "persistent_conversation_mutations": 0,
                "memory_writes": 0,
                "action_writes": 0,
                "reflection_writes": 0,
            },
            "timings_ms": {"total_validation": elapsed_ms},
            "performance_budgets": {
                "first_visible_token_ms": max(1, int(first_token_budget_ms)),
                "first_token_ms": max(1, int(first_token_budget_ms)),
                "first_token_metric": "first_visible_token",
                "total_response_ms": max(1, int(total_budget_ms)),
            },
            "contains_prompts": False,
            "contains_generated_responses": False,
            "contains_raw_conversation_text": False,
            "contains_memories": False,
            "contains_secrets": False,
            "contains_credentials": False,
            "contains_provider_payloads": False,
            "contains_raw_events": False,
            "persisted": False,
            "evidence_path": "",
            "automatic_model_management": False,
            "provider_configuration_changed": False,
            "approval_granted": False,
            "release_authorized": False,
            "autonomous_action_performed": False,
            "operator_control_preserved": True,
        }
        if persist:
            _persist_report(report)
        return report


def validation_text(report: dict[str, Any]) -> str:
    lines = [
        "# Native conversational experience validation",
        f"Status: {report.get('status')}",
        f"Provider/model: {report.get('provider', 'n/a')} / {report.get('model', 'n/a')}",
        f"Scenarios: {report.get('scenarios_completed', 0)}/{report.get('scenarios_planned', 0)}",
        f"Quality score: {(report.get('quality_scorecard') or {}).get('average_score_percent', 0)}%",
        f"Tuning preview: {(report.get('provider_neutral_tuning_preview') or {}).get('status', 'evidence_required')}",
    ]
    if report.get("confirmation_required"):
        lines.append(f"Confirmation required: {report.get('required_confirmation')}")
        return "\n".join(lines)
    if report.get("invalid_request"):
        lines.append(f"Blocked reason: {report.get('message', 'Invalid validation request.')}")
        return "\n".join(lines)
    for row in report.get("scenarios") or []:
        timings = row.get("timings_ms") or {}
        lines.append(
            f"- {row.get('scenario_id')}: {row.get('status')} / {row.get('completion_state')} / "
            f"first_visible={timings.get('first_visible_token')}ms transport={timings.get('first_transport_chunk')}ms total={timings.get('total')}ms"
        )
    cancellation = (report.get("recovery") or {}).get("cancellation") or {}
    lines.append(f"Cancellation: {cancellation.get('completion_state', 'not_run')}")
    lines.append(f"Redacted evidence: {report.get('evidence_path') or 'not persisted'}")
    lines.append("No raw prompts, responses, memories, credentials, or provider payloads are included.")
    return "\n".join(lines)


def print_native_conversation_validation(**kwargs: Any) -> dict[str, Any]:
    json_output = bool(kwargs.pop("json_output", False))
    try:
        report = run_native_conversation_validation(**kwargs)
    except ValueError as error:
        report = {
            "receipt_schema_version": VALIDATION_SCHEMA_VERSION,
            "receipt_type": "native_conversation_validation",
            "status": "blocked",
            "invalid_request": True,
            "failure_category": "invalid_configuration",
            "message": str(error),
            "confirmation_required": False,
            "native_provider_evidence": False,
            "provider_requests_sent": 0,
            "persisted": False,
            "contains_prompts": False,
            "contains_generated_responses": False,
            "contains_memories": False,
            "contains_provider_payloads": False,
            "automatic_model_management": False,
            "operator_control_preserved": True,
        }
    print(json.dumps(report, indent=2, default=str) if json_output else validation_text(report))
    return report
