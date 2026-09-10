from __future__ import annotations

"""Redacted local-model configuration digests and provider evidence receipts.

Receipts are returned to the caller only. This module never persists evidence,
model prompts, responses, credentials, raw provider events, or request payloads.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

from local_model import LocalModelConfig, LocalModelError

RECEIPT_SCHEMA_VERSION = "1"
EVIDENCE_SOURCE_NATIVE = "native_provider"
EVIDENCE_SOURCE_FIXTURE = "fixture_simulation"
_ALLOWED_EVIDENCE_SOURCES = {EVIDENCE_SOURCE_NATIVE, EVIDENCE_SOURCE_FIXTURE}
_ALLOWED_RECEIPT_TYPES = {"provider_readiness", "native_provider_smoke"}
_ALLOWED_ERROR_DETAIL_KEYS = {"failure_kind", "exception_type", "yielded_content"}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sanitize_endpoint(endpoint: str) -> str:
    """Return a bounded endpoint without credentials, query, or fragment data."""
    raw = str(endpoint or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return "[invalid-endpoint]"
    scheme = parsed.scheme.lower()
    host = parsed.hostname or ""
    if not scheme or not host:
        return "[invalid-endpoint]"
    host_text = f"[{host}]" if ":" in host and not host.startswith("[") else host
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = f"{host_text}:{port}" if port is not None else host_text
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def configuration_digest(config: LocalModelConfig) -> str:
    """Hash the complete validated local-model configuration without exposing it."""
    resolved = config.validated()
    payload = {
        "provider": resolved.provider,
        "generation_endpoint": resolved.endpoint,
        "embedding_endpoint": resolved.resolved_embedding_endpoint,
        "embedding_endpoint_configured": resolved.embedding_endpoint,
        "generation_model": resolved.model,
        "embedding_model": resolved.embed_model,
        "context_size": resolved.context_size,
        "connect_timeout_seconds": resolved.connect_timeout_seconds,
        "read_timeout_seconds": resolved.read_timeout_seconds,
        "ollama_keep_alive_minutes": resolved.ollama_keep_alive_minutes,
        "retry_limit": resolved.retry_limit,
        "retry_delay_seconds": resolved.retry_delay_seconds,
        "generation": {
            "max_tokens": resolved.generation.max_tokens,
            "temperature": resolved.generation.temperature,
            "top_p": resolved.generation.top_p,
            "top_k": resolved.generation.top_k,
            "repeat_penalty": resolved.generation.repeat_penalty,
            "seed": resolved.generation.seed,
            "stop": list(resolved.generation.stop),
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_evidence_source(value: str) -> str:
    source = str(value or EVIDENCE_SOURCE_NATIVE).strip().lower()
    return source if source in _ALLOWED_EVIDENCE_SOURCES else EVIDENCE_SOURCE_FIXTURE


def _bounded_text(value: Any, limit: int = 300) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def redact_error(error: LocalModelError | dict[str, Any], *, service: str | None = None, capability: str | None = None) -> dict[str, Any]:
    """Return a bounded provider error safe for API, dashboard, CLI, and receipts."""
    payload = error.to_dict() if isinstance(error, LocalModelError) else dict(error)
    endpoint = sanitize_endpoint(str(payload.get("endpoint") or ""))
    raw_message = _bounded_text(payload.get("message"))
    raw_endpoint = str(payload.get("endpoint") or "")
    if raw_endpoint and raw_endpoint in raw_message:
        raw_message = raw_message.replace(raw_endpoint, endpoint)
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    safe_details = {
        key: details[key]
        for key in _ALLOWED_ERROR_DETAIL_KEYS
        if key in details and isinstance(details[key], (str, int, float, bool, type(None)))
    }
    return {
        "code": _bounded_text(payload.get("code"), 80),
        "message": raw_message,
        "provider": _bounded_text(payload.get("provider"), 40),
        "endpoint": endpoint,
        "model": _bounded_text(payload.get("model"), 160),
        "retryable": bool(payload.get("retryable")),
        "status_code": payload.get("status_code") if isinstance(payload.get("status_code"), int) else None,
        "details": safe_details,
        "service": service,
        "capability": capability,
        "redacted": True,
    }


def drift_report(current_digest: str, expected_digest: str | None) -> dict[str, Any]:
    current = str(current_digest or "").strip().lower()
    expected = str(expected_digest or "").strip().lower()
    if not expected:
        return {
            "status": "not_compared",
            "detected": False,
            "expected_configuration_digest": None,
            "current_configuration_digest": current,
        }
    valid_expected = len(expected) == 64 and all(character in "0123456789abcdef" for character in expected)
    if not valid_expected:
        return {
            "status": "invalid_expected_digest",
            "detected": True,
            "expected_configuration_digest": "[invalid-digest]",
            "current_configuration_digest": current,
            "message": "The readiness configuration digest is invalid. Rerun readiness and use the returned 64-character digest.",
        }
    matched = expected == current
    return {
        "status": "matched" if matched else "detected",
        "detected": not matched,
        "expected_configuration_digest": expected,
        "current_configuration_digest": current,
        "message": None if matched else "Readiness and native smoke used different local-model settings. Rerun readiness before native smoke.",
    }


def _capability_rows(checks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for check in checks:
        details = check.get("details") if isinstance(check.get("details"), dict) else {}
        error = check.get("error") if isinstance(check.get("error"), dict) else None
        row = {
            "name": _bounded_text(check.get("name"), 100),
            "capability": _bounded_text(check.get("capability"), 80) or None,
            "service": _bounded_text(check.get("service"), 40) or None,
            "result": _bounded_text(check.get("status"), 30),
            "elapsed_seconds": round(float(check.get("elapsed_seconds") or 0.0), 4),
        }
        if "dimensions" in details:
            row["embedding_dimensions"] = int(details["dimensions"])
        if error:
            row["error_classification"] = _bounded_text(error.get("classification") or error.get("code"), 80)
        rows.append(row)
    return rows


def build_receipt(
    *,
    receipt_type: str,
    config: LocalModelConfig,
    result: str,
    checks: Iterable[dict[str, Any]],
    elapsed_seconds: float,
    evidence_source: str,
    configuration_drift: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = config.validated()
    check_rows = _capability_rows(checks)
    embedding_dimensions = next(
        (row["embedding_dimensions"] for row in check_rows if "embedding_dimensions" in row),
        None,
    )
    source = normalize_evidence_source(evidence_source)
    receipt_kind = _bounded_text(receipt_type, 80)
    native_evidence = (
        source == EVIDENCE_SOURCE_NATIVE
        and receipt_kind in _ALLOWED_RECEIPT_TYPES
        and bool(check_rows)
    )
    return {
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_type": receipt_kind,
        "evidence_source": source,
        "native_provider_evidence": native_evidence,
        "timestamp": utc_timestamp(),
        "provider": resolved.provider,
        "generation_endpoint": sanitize_endpoint(resolved.endpoint),
        "embedding_endpoint": sanitize_endpoint(resolved.resolved_embedding_endpoint),
        "generation_model": resolved.model,
        "embedding_model": resolved.embed_model,
        "configuration_digest": configuration_digest(resolved),
        "result": result,
        "tested_capabilities": check_rows,
        "embedding_dimensions": embedding_dimensions,
        "timings": {
            "total_elapsed_seconds": round(float(elapsed_seconds), 4),
            "checks": {row["name"]: row["elapsed_seconds"] for row in check_rows if row["name"]},
        },
        "configuration_drift": configuration_drift or drift_report(configuration_digest(resolved), None),
        "contains_prompts": False,
        "contains_generated_responses": False,
        "contains_credentials": False,
        "contains_raw_events": False,
        "contains_request_payloads": False,
        "contains_stack_traces": False,
        "persisted": False,
        "automatic_model_management": False,
        "operator_approval_required": True,
    }
