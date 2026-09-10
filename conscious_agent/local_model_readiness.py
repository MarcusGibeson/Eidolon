from __future__ import annotations

"""Provider-neutral readiness and explicitly confirmed native smoke diagnostics.

The implementation never installs, downloads, deletes, replaces, starts, or
stops models. Readiness performs bounded metadata probes. Native smoke runs only
after explicit operator confirmation and performs small generation, streaming,
and embedding requests against the configured generation and embedding services.
"""

import time
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Callable

from local_model import (
    ERROR_HTTP,
    ERROR_INVALID_CONFIG,
    ERROR_MALFORMED,
    ERROR_MISSING_MODEL,
    ERROR_TIMEOUT,
    ERROR_UNAVAILABLE,
    InvalidConfigurationError,
    LocalModelClient,
    LocalModelConfig,
    LocalModelError,
)

from provider_availability import build_provider_availability_experience

from local_model_evidence import (
    EVIDENCE_SOURCE_NATIVE,
    build_receipt,
    configuration_digest,
    drift_report,
    redact_error,
    sanitize_endpoint,
)

SCHEMA_VERSION = "3"
CAPABILITY_HEALTH = "health"
CAPABILITY_MODEL_LISTING = "model_listing"
CAPABILITY_GENERATION = "generation"
CAPABILITY_STREAMING = "streaming"
CAPABILITY_EMBEDDINGS = "embeddings"
CAPABILITY_VERSION = "version"
SERVICE_GENERATION = "generation"
SERVICE_EMBEDDING = "embedding"

_PROVIDER_CAPABILITIES: dict[str, dict[str, str]] = {
    "ollama": {
        CAPABILITY_HEALTH: "supported",
        CAPABILITY_MODEL_LISTING: "supported",
        CAPABILITY_GENERATION: "supported",
        CAPABILITY_STREAMING: "supported",
        CAPABILITY_EMBEDDINGS: "supported",
        CAPABILITY_VERSION: "supported",
    },
    "llama_cpp": {
        CAPABILITY_HEALTH: "supported",
        CAPABILITY_MODEL_LISTING: "supported",
        CAPABILITY_GENERATION: "supported",
        CAPABILITY_STREAMING: "supported",
        CAPABILITY_EMBEDDINGS: "server_dependent",
        CAPABILITY_VERSION: "server_dependent",
    },
}


@dataclass
class ProbeResult:
    name: str
    status: str
    elapsed_seconds: float
    capability: str | None = None
    service: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def provider_capabilities(provider: str) -> dict[str, dict[str, Any]]:
    contract = _PROVIDER_CAPABILITIES.get(provider, {})
    return {
        name: {"support": support, "available": None, "source": "provider_contract"}
        for name, support in contract.items()
    }


def classify_error(
    error: LocalModelError,
    *,
    capability: str | None = None,
    service: str | None = None,
) -> dict[str, Any]:
    """Normalize transport/provider failures into bounded redacted operator classes."""
    error_dict = redact_error(error, capability=capability, service=service)
    status_code = error.status_code
    if error.code == ERROR_INVALID_CONFIG:
        classification = "configuration_error"
    elif error.code == ERROR_UNAVAILABLE:
        failure_kind = str(error.details.get("failure_kind") or "")
        classification = "connection_failure" if failure_kind == "connection_failure" else "unavailable_service"
    elif error.code == ERROR_TIMEOUT:
        classification = "read_timeout"
    elif error.code == ERROR_MISSING_MODEL:
        classification = "missing_model"
    elif error.code == ERROR_MALFORMED:
        classification = "malformed_response"
    elif error.code == ERROR_HTTP and capability and status_code in {404, 405, 501}:
        classification = "unsupported_capability"
    else:
        classification = error.code
    return {"classification": classification, **error_dict}


def _guidance(issue: str, config: LocalModelConfig | None, service: str | None = None) -> str:
    provider = config.provider if config else "configured provider"
    generation_endpoint = sanitize_endpoint(config.endpoint) if config else "the configured generation endpoint"
    embedding_endpoint = sanitize_endpoint(config.resolved_embedding_endpoint) if config else "the configured embedding endpoint"
    endpoint = embedding_endpoint if service == SERVICE_EMBEDDING else generation_endpoint
    model = config.embed_model if config and service == SERVICE_EMBEDDING else (config.model if config else "the configured model")
    service_label = "embedding" if service == SERVICE_EMBEDDING else "generation"
    guidance = {
        "configuration_error": "Correct the provider, endpoints, models, timeout, context, or generation settings. No model files were changed.",
        "connection_failure": f"Start or reconnect the {provider} {service_label} service at {endpoint}, then rerun readiness.",
        "unavailable_service": f"Start the {provider} {service_label} service at {endpoint}, or correct that endpoint.",
        "read_timeout": f"The {service_label} service at {endpoint} accepted the request but did not answer in time. Check load, model size, and the configured read timeout.",
        "missing_model": f"Make {model!r} available through the {provider} {service_label} service. Installation remains an explicit operator action.",
        "missing_embedding_model": f"Make {model!r} available through the {provider} embedding service at {endpoint}, or configure an existing embedding model.",
        "malformed_response": f"Confirm {endpoint} exposes the expected {provider} {service_label} API and inspect provider logs for malformed output.",
        "unsupported_capability": f"The {service_label} service at {endpoint} does not expose the requested capability. Enable it server-side or configure a compatible service.",
        "http_failure": f"Inspect the reported HTTP status and {provider} logs for the {service_label} service at {endpoint}, then rerun the bounded check.",
    }
    return guidance.get(issue, f"Inspect the structured {service_label} error and provider logs, then rerun readiness.")


def _empty_service(service: str, endpoint: str, model: str) -> dict[str, Any]:
    return {
        "service": service,
        "endpoint": sanitize_endpoint(endpoint),
        "model": model,
        "available": False,
        "model_available": None,
        "version": None,
        "models": [],
        "issues": [],
        "timings": {},
        "elapsed_seconds": 0.0,
    }


def _base_report(config: LocalModelConfig | None) -> dict[str, Any]:
    generation_endpoint = sanitize_endpoint(config.endpoint) if config else ""
    embedding_endpoint = sanitize_endpoint(config.resolved_embedding_endpoint) if config else ""
    generation_model = config.model if config else ""
    embedding_model = config.embed_model if config else ""
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": config.provider if config else "",
        "endpoint": generation_endpoint,
        "generation_endpoint": generation_endpoint,
        "embedding_endpoint": embedding_endpoint,
        "embedding_endpoint_configured": config.embedding_endpoint if config else "",
        "embedding_endpoint_uses_generation_fallback": config.uses_legacy_single_endpoint if config else True,
        "generation_model": generation_model,
        "embedding_model": embedding_model,
        "service_available": False,
        "generation_service_available": False,
        "embedding_service_available": False,
        "generation_model_available": None,
        "embedding_model_available": None,
        "provider_version": None,
        "embedding_provider_version": None,
        "models": [],
        "embedding_models": [],
        "services": {
            SERVICE_GENERATION: _empty_service(SERVICE_GENERATION, generation_endpoint, generation_model),
            SERVICE_EMBEDDING: _empty_service(SERVICE_EMBEDDING, embedding_endpoint, embedding_model),
        },
        "capabilities": provider_capabilities(config.provider if config else ""),
        "issues": [],
        "guidance": [],
        "status": "blocked",
        "automatic_model_management": False,
        "operator_approval_required": True,
        "configuration_digest": configuration_digest(config) if config else None,
        "evidence_receipt": None,
    }


def _apply_availability(
    report: dict[str, Any],
    *,
    previous_state: str | None = None,
    checking: bool = False,
) -> dict[str, Any]:
    availability = build_provider_availability_experience(
        report, previous_state=previous_state, checking=checking,
    )
    report["availability"] = availability
    report["readiness_state"] = availability["state"]
    return report


def _probe_service(client: LocalModelClient, service: str, endpoint: str, model: str) -> dict[str, Any]:
    started = time.monotonic()
    row = _empty_service(service, endpoint, model)
    hard_failure = False
    version_started = time.monotonic()
    try:
        row["version"] = client.version(service)
        row["available"] = True
    except LocalModelError as error:
        issue = classify_error(error, capability=CAPABILITY_VERSION, service=service)
        row["issues"].append(issue)
        hard_failure = issue["classification"] in {
            "connection_failure", "unavailable_service", "read_timeout", "malformed_response"
        }
        if issue["classification"] == "unsupported_capability":
            hard_failure = False
    row["timings"]["version_seconds"] = round(time.monotonic() - version_started, 4)
    if not hard_failure:
        models_started = time.monotonic()
        try:
            row["models"] = client.list_models(service)
            row["available"] = True
        except LocalModelError as error:
            issue = classify_error(error, capability=CAPABILITY_MODEL_LISTING, service=service)
            row["issues"].append(issue)
            if issue["classification"] not in {"unsupported_capability"}:
                row["available"] = row["available"] and issue["classification"] not in {
                    "connection_failure", "unavailable_service", "read_timeout", "malformed_response"
                }
        row["timings"]["model_listing_seconds"] = round(time.monotonic() - models_started, 4)
    if row["models"]:
        row["model_available"] = model in row["models"]
    row["elapsed_seconds"] = round(time.monotonic() - started, 4)
    return row


def provider_readiness(
    settings: dict[str, Any] | None = None,
    *,
    config: LocalModelConfig | None = None,
    identity_config: LocalModelConfig | None = None,
    evidence_source: str = EVIDENCE_SOURCE_NATIVE,
    previous_state: str | None = None,
) -> dict[str, Any]:
    """Return bounded readiness for generation and embedding services."""
    started = time.monotonic()
    try:
        resolved = (config or LocalModelConfig.from_settings(settings)).validated()
        identity = (identity_config or resolved).validated()
    except (LocalModelError, TypeError, ValueError) as raw_error:
        error = raw_error if isinstance(raw_error, LocalModelError) else InvalidConfigurationError(str(raw_error))
        issue = classify_error(error)
        report = _base_report(None)
        report["issues"].append(issue)
        report["guidance"].append(_guidance(issue["classification"], None))
        report["elapsed_seconds"] = round(time.monotonic() - started, 4)
        return _apply_availability(report, previous_state=previous_state)

    report = _base_report(identity)
    try:
        with LocalModelClient(resolved) as client:
            generation = _probe_service(client, SERVICE_GENERATION, resolved.endpoint, resolved.model)
            if resolved.uses_legacy_single_endpoint:
                embedding = {
                    **generation,
                    "service": SERVICE_EMBEDDING,
                    "endpoint": resolved.resolved_embedding_endpoint,
                    "model": resolved.embed_model,
                    "models": list(generation["models"]),
                    "issues": [dict(issue, service=SERVICE_EMBEDDING) for issue in generation["issues"]],
                }
                embedding["model_available"] = (
                    resolved.embed_model in embedding["models"] if embedding["models"] else None
                )
            else:
                embedding = _probe_service(
                    client, SERVICE_EMBEDDING, resolved.resolved_embedding_endpoint, resolved.embed_model
                )
    except LocalModelError as error:
        report["issues"].append(classify_error(error))
        report["elapsed_seconds"] = round(time.monotonic() - started, 4)
        return _apply_availability(report, previous_state=previous_state)

    report["services"] = {SERVICE_GENERATION: generation, SERVICE_EMBEDDING: embedding}
    report["generation_service_available"] = bool(generation["available"])
    report["embedding_service_available"] = bool(embedding["available"])
    report["service_available"] = report["generation_service_available"]
    report["generation_model_available"] = generation["model_available"]
    report["embedding_model_available"] = embedding["model_available"]
    report["provider_version"] = generation["version"]
    report["embedding_provider_version"] = embedding["version"]
    report["models"] = list(generation["models"])
    report["embedding_models"] = list(embedding["models"])
    report["issues"].extend(generation["issues"])
    report["issues"].extend(embedding["issues"])

    if generation["model_available"] is False:
        report["issues"].append({
            "classification": "missing_model",
            "capability": CAPABILITY_GENERATION,
            "service": SERVICE_GENERATION,
            "endpoint": sanitize_endpoint(resolved.endpoint),
            "model": resolved.model,
            "message": f"Configured generation model {resolved.model!r} was not reported by the generation service.",
            "redacted": True,
        })
    if embedding["model_available"] is False:
        report["issues"].append({
            "classification": "missing_embedding_model",
            "capability": CAPABILITY_EMBEDDINGS,
            "service": SERVICE_EMBEDDING,
            "endpoint": sanitize_endpoint(resolved.resolved_embedding_endpoint),
            "model": resolved.embed_model,
            "message": f"Configured embedding model {resolved.embed_model!r} was not reported by the embedding service.",
            "redacted": True,
        })

    capabilities = report["capabilities"]
    capabilities[CAPABILITY_HEALTH]["available"] = generation["available"] and embedding["available"]
    capabilities[CAPABILITY_VERSION]["available"] = (
        generation["version"] is not None and embedding["version"] is not None
    )
    capabilities[CAPABILITY_MODEL_LISTING]["available"] = bool(generation["models"] or embedding["models"])
    capabilities[CAPABILITY_GENERATION]["available"] = (
        generation["available"] and generation["model_available"] is not False
    )
    capabilities[CAPABILITY_STREAMING]["available"] = capabilities[CAPABILITY_GENERATION]["available"]
    capabilities[CAPABILITY_EMBEDDINGS]["available"] = (
        embedding["available"] and embedding["model_available"] is not False
    )

    # Unsupported version endpoints are informative but do not prevent readiness.
    material_issues = [
        item for item in report["issues"]
        if not (
            item.get("classification") == "unsupported_capability"
            and item.get("capability") == CAPABILITY_VERSION
        )
    ]
    report["guidance"] = list(dict.fromkeys(
        _guidance(str(item.get("classification")), resolved, str(item.get("service") or "") or None)
        for item in material_issues
    ))

    generation_blocking = {
        "configuration_error", "connection_failure", "unavailable_service", "read_timeout",
        "missing_model", "malformed_response", "http_failure",
    }
    generation_classes = {
        str(item.get("classification")) for item in material_issues
        if item.get("service") in {None, "", SERVICE_GENERATION}
    }
    embedding_classes = {
        str(item.get("classification")) for item in material_issues
        if item.get("service") == SERVICE_EMBEDDING
    }
    if not generation["available"] or generation["model_available"] is False or generation_classes & generation_blocking:
        report["status"] = "blocked"
    elif not embedding["available"] or embedding["model_available"] is False or embedding_classes:
        report["status"] = "degraded"
    elif material_issues:
        report["status"] = "degraded"
    else:
        report["status"] = "ready"
    report["elapsed_seconds"] = round(time.monotonic() - started, 4)
    readiness_checks = [
        {
            "name": f"{service}_service_readiness",
            "status": "pass" if row.get("available") and row.get("model_available") is not False else "fail",
            "capability": CAPABILITY_HEALTH,
            "service": service,
            "elapsed_seconds": row.get("elapsed_seconds", 0.0),
            "details": {},
            "error": row.get("issues", [None])[0] if row.get("issues") else None,
        }
        for service, row in report["services"].items()
    ]
    report["evidence_receipt"] = build_receipt(
        receipt_type="provider_readiness",
        config=identity,
        result=report["status"],
        checks=readiness_checks,
        elapsed_seconds=report["elapsed_seconds"],
        evidence_source=evidence_source,
    )
    return _apply_availability(report, previous_state=previous_state)


def _bounded_config(config: LocalModelConfig, timeout_seconds: float) -> LocalModelConfig:
    timeout = max(0.1, min(float(timeout_seconds), 120.0))
    generation = replace(config.generation, max_tokens=min(config.generation.max_tokens, 32), temperature=0.0)
    return replace(
        config,
        connect_timeout_seconds=min(config.connect_timeout_seconds, min(timeout, 10.0)),
        read_timeout_seconds=min(config.read_timeout_seconds, timeout),
        retry_limit=0,
        generation=generation,
    ).validated()


def _run_probe(
    name: str,
    capability: str,
    service: str,
    callback: Callable[[], dict[str, Any]],
) -> ProbeResult:
    started = time.monotonic()
    try:
        details = callback()
    except LocalModelError as error:
        normalized = classify_error(error, capability=capability, service=service)
        status = "unsupported" if normalized["classification"] == "unsupported_capability" else "fail"
        return ProbeResult(
            name, status, round(time.monotonic() - started, 4), capability, service, error=normalized
        )
    except Exception as error:
        normalized = {
            "classification": "unexpected_error",
            "capability": capability,
            "service": service,
            "message": f"Unexpected {type(error).__name__} during the bounded provider check.",
            "redacted": True,
        }
        return ProbeResult(
            name, "fail", round(time.monotonic() - started, 4), capability, service, error=normalized
        )
    return ProbeResult(
        name, "pass", round(time.monotonic() - started, 4), capability, service, details=details
    )


def native_model_smoke(
    settings: dict[str, Any] | None = None,
    *,
    config: LocalModelConfig | None = None,
    confirmed: bool = False,
    timeout_seconds: float = 30.0,
    readiness_configuration_digest: str | None = None,
    evidence_source: str = EVIDENCE_SOURCE_NATIVE,
) -> dict[str, Any]:
    """Run explicitly approved bounded health, generation, stream, and embedding checks."""
    started = time.monotonic()
    if not confirmed:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "native_evidence": False,
            "confirmation_required": True,
            "checks": [],
            "guidance": ["Rerun with explicit native-smoke confirmation. No request was sent."],
            "automatic_model_management": False,
        }
    try:
        configured = (config or LocalModelConfig.from_settings(settings)).validated()
        resolved = _bounded_config(configured, timeout_seconds)
    except (LocalModelError, TypeError, ValueError) as raw_error:
        error = raw_error if isinstance(raw_error, LocalModelError) else InvalidConfigurationError(str(raw_error))
        normalized = classify_error(error)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "native_evidence": False,
            "confirmation_required": False,
            "checks": [],
            "issues": [normalized],
            "guidance": [_guidance(normalized["classification"], None)],
            "automatic_model_management": False,
        }

    current_digest = configuration_digest(configured)
    drift = drift_report(current_digest, readiness_configuration_digest)
    if drift["detected"]:
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "native_evidence": False,
            "confirmation_required": False,
            "provider": resolved.provider,
            "generation_endpoint": sanitize_endpoint(resolved.endpoint),
            "embedding_endpoint": sanitize_endpoint(resolved.resolved_embedding_endpoint),
            "generation_model": resolved.model,
            "embedding_model": resolved.embed_model,
            "configuration_digest": current_digest,
            "configuration_drift": drift,
            "checks": [],
            "issues": [{
                "classification": "configuration_drift",
                "service": None,
                "capability": None,
                "message": drift["message"],
                "redacted": True,
            }],
            "guidance": ["Rerun readiness with the current settings, then explicitly confirm native smoke using that configuration digest."],
            "automatic_model_management": False,
        }
        report["evidence_receipt"] = build_receipt(
            receipt_type="native_provider_smoke", config=configured, result="blocked", checks=[],
            elapsed_seconds=time.monotonic() - started, evidence_source=evidence_source, configuration_drift=drift,
        )
        return report

    readiness = provider_readiness(
        config=resolved,
        identity_config=configured,
        evidence_source=evidence_source,
    )
    readiness_status = "pass" if readiness["status"] != "blocked" else "fail"
    checks: list[ProbeResult] = [ProbeResult(
        "health_and_model_readiness",
        readiness_status,
        float(readiness.get("elapsed_seconds") or 0.0),
        CAPABILITY_HEALTH,
        None,
        details=readiness,
    )]
    if readiness["status"] == "blocked":
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "native_evidence": evidence_source == EVIDENCE_SOURCE_NATIVE,
            "confirmation_required": False,
            "provider": resolved.provider,
            "endpoint": sanitize_endpoint(resolved.endpoint),
            "generation_endpoint": sanitize_endpoint(resolved.endpoint),
            "embedding_endpoint": sanitize_endpoint(resolved.resolved_embedding_endpoint),
            "generation_model": resolved.model,
            "embedding_model": resolved.embed_model,
            "timeout_seconds": resolved.read_timeout_seconds,
            "configuration_digest": current_digest,
            "configuration_drift": drift,
            "checks": [item.to_dict() for item in checks],
            "guidance": readiness["guidance"],
            "automatic_model_management": False,
        }
        report["evidence_receipt"] = build_receipt(
            receipt_type="native_provider_smoke", config=configured, result="blocked", checks=report["checks"],
            elapsed_seconds=time.monotonic() - started, evidence_source=evidence_source, configuration_drift=drift,
        )
        return report

    with LocalModelClient(resolved) as client:
        checks.append(_run_probe(
            "bounded_generation",
            CAPABILITY_GENERATION,
            SERVICE_GENERATION,
            lambda: {"response_chars": len(client.generate("Reply with exactly EIDOLON_NATIVE_OK."))},
        ))
        checks.append(_run_probe(
            "bounded_streaming",
            CAPABILITY_STREAMING,
            SERVICE_GENERATION,
            lambda: {"response_chars": len("".join(client.stream("Reply with exactly EIDOLON_STREAM_OK.")))},
        ))
        checks.append(_run_probe(
            "bounded_embedding",
            CAPABILITY_EMBEDDINGS,
            SERVICE_EMBEDDING,
            lambda: {"dimensions": len(client.embed("Eidolon native embedding smoke"))},
        ))

    generation_failed = any(
        item.status != "pass" and item.service == SERVICE_GENERATION for item in checks
    )
    embedding_failed = any(
        item.status != "pass" and item.service == SERVICE_EMBEDDING for item in checks
    )
    if generation_failed:
        status = "blocked"
    elif embedding_failed or readiness["status"] == "degraded":
        status = "partial"
    else:
        status = "pass"
    issues = [item.error for item in checks if item.error]
    guidance = list(dict.fromkeys(
        _guidance(str(item.get("classification")), resolved, str(item.get("service") or "") or None)
        for item in issues
    ))
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "native_evidence": evidence_source == EVIDENCE_SOURCE_NATIVE,
        "confirmation_required": False,
        "provider": resolved.provider,
        "endpoint": sanitize_endpoint(resolved.endpoint),
        "generation_endpoint": sanitize_endpoint(resolved.endpoint),
        "embedding_endpoint": sanitize_endpoint(resolved.resolved_embedding_endpoint),
        "embedding_endpoint_uses_generation_fallback": resolved.uses_legacy_single_endpoint,
        "generation_model": resolved.model,
        "embedding_model": resolved.embed_model,
        "timeout_seconds": resolved.read_timeout_seconds,
        "configuration_digest": current_digest,
        "configuration_drift": drift,
        "checks": [item.to_dict() for item in checks],
        "issues": issues,
        "guidance": guidance,
        "automatic_model_management": False,
    }
    report["evidence_receipt"] = build_receipt(
        receipt_type="native_provider_smoke", config=configured, result=status, checks=report["checks"],
        elapsed_seconds=time.monotonic() - started, evidence_source=evidence_source, configuration_drift=drift,
    )
    return report


def readiness_text(report: dict[str, Any]) -> str:
    lines = [
        "# Local model provider readiness",
        "",
        f"Status: {report.get('status')}",
        f"Provider: {report.get('provider')}",
        f"Generation endpoint: {report.get('generation_endpoint')}",
        f"Embedding endpoint: {report.get('embedding_endpoint')} (fallback: {report.get('embedding_endpoint_uses_generation_fallback')})",
        f"Generation model: {report.get('generation_model')} (available: {report.get('generation_model_available')})",
        f"Embedding model: {report.get('embedding_model')} (available: {report.get('embedding_model_available')})",
        f"Generation service available: {report.get('generation_service_available')}",
        f"Embedding service available: {report.get('embedding_service_available')}",
        f"Configuration digest: {report.get('configuration_digest')}",
        "",
        "Capabilities:",
    ]
    for name, row in (report.get("capabilities") or {}).items():
        lines.append(f"- {name}: contract={row.get('support')} available={row.get('available')}")
    if report.get("issues"):
        lines.extend(["", "Issues:"])
        for issue in report["issues"]:
            service = issue.get("service") or "configuration"
            lines.append(f"- {service}/{issue.get('classification')}: {issue.get('message', '')}")
    if report.get("guidance"):
        lines.extend(["", "Operator guidance:"])
        lines.extend(f"- {item}" for item in report["guidance"])
    lines.extend(["", "No models were installed, downloaded, deleted, or replaced."])
    return "\n".join(lines)


def native_smoke_text(report: dict[str, Any]) -> str:
    lines = [
        "# Native local model smoke",
        "",
        f"Status: {report.get('status')}",
        f"Provider: {report.get('provider', '[not resolved]')}",
        f"Generation endpoint: {report.get('generation_endpoint', report.get('endpoint', '[not resolved]'))}",
        f"Embedding endpoint: {report.get('embedding_endpoint', '[not resolved]')}",
        f"Native evidence attempted: {report.get('native_evidence')}",
        f"Configuration digest: {report.get('configuration_digest')}",
        f"Configuration drift: {(report.get('configuration_drift') or {}).get('status')}",
        "",
        "Checks:",
    ]
    checks = report.get("checks") or []
    lines.extend(
        f"- {item.get('status')}: {item.get('name')} [{item.get('service') or 'combined'}] ({item.get('elapsed_seconds')}s)"
        for item in checks
    )
    if not checks:
        lines.append("- [none executed]")
    if report.get("guidance"):
        lines.extend(["", "Operator guidance:"])
        lines.extend(f"- {item}" for item in report["guidance"])
    lines.extend(["", "Native smoke is read-only and never manages model files."])
    return "\n".join(lines)


def print_provider_readiness(*, json_output: bool = False) -> dict[str, Any]:
    import json

    report = provider_readiness()
    print(json.dumps(report, indent=2, default=str) if json_output else readiness_text(report))
    return report


def print_native_model_smoke(
    *,
    confirmed: bool,
    timeout_seconds: float = 30.0,
    json_output: bool = False,
    readiness_configuration_digest: str | None = None,
) -> dict[str, Any]:
    import json

    report = native_model_smoke(
        confirmed=confirmed,
        timeout_seconds=timeout_seconds,
        readiness_configuration_digest=readiness_configuration_digest,
    )
    print(json.dumps(report, indent=2, default=str) if json_output else native_smoke_text(report))
    return report
