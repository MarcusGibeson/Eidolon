from __future__ import annotations

"""Provider boundary for G-CORROB1-R2.

Construction and verification are offline. Network methods require an explicit
contact flag and are never called by imports, tests, freeze preparation, or CLI.
"""

from dataclasses import dataclass
import hashlib
import json
import re
import time
from typing import Any, Mapping

from g_corrob1_contract import assert_minimal_semantic_body, canonical_digest, load_sampling


CONTRACT_VERSION = "g-corrob1.r2.provider-candidate.1"
EXPECTED_PROVIDER = "ollama"
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def configuration_digest(value: Mapping[str, Any]) -> str:
    return canonical_digest(json.dumps(dict(value), sort_keys=True, separators=(",", ":")))


def prepared_configuration() -> dict[str, Any]:
    proposal = load_sampling()
    return {
        "provider": proposal["provider"],
        "provider_version": None,
        "model": proposal["model_name"],
        "parameters": dict(proposal["parameters"]),
        "fresh_context_per_call": True,
        "provider_attempts_per_scheduled_call": 1,
        "json_repair_calls": 0,
        "silent_retries": False,
        "model_content_digest": None,
        "model_configuration_digest": configuration_digest({
            "provider": proposal["provider"], "model": proposal["model_name"],
            "parameters": proposal["parameters"], "fresh_context_per_call": True,
            "provider_attempts_per_scheduled_call": 1,
        }),
        "verification_limitations": [
            "offline preparation cannot resolve the installed model content digest",
            "Ollama accepts submitted generation options but does not attest that every option was honored",
            "seed behavior requires later mechanical-pilot verification and cannot establish reasoning independence",
        ],
        "provider_contacted": False,
    }


def verify_preflight_receipt(receipt: Mapping[str, Any], *, require_model_digest: bool = True) -> dict[str, Any]:
    proposal = load_sampling()
    reasons: list[str] = []
    if receipt.get("provider") != EXPECTED_PROVIDER:
        reasons.append("provider_mismatch")
    if not str(receipt.get("provider_version") or ""):
        reasons.append("provider_version_unresolved")
    if receipt.get("requested_model") != proposal["model_name"]:
        reasons.append("requested_model_mismatch")
    if receipt.get("resolved_model") != proposal["model_name"]:
        reasons.append("resolved_model_mismatch_or_fallback")
    digest = str(receipt.get("model_content_digest") or "").lower()
    if require_model_digest and not DIGEST_RE.fullmatch(digest):
        reasons.append("model_content_digest_unresolved")
    expected_parameters = dict(proposal["parameters"])
    if receipt.get("submitted_parameters") != expected_parameters:
        reasons.append("submitted_parameters_mismatch")
    support = receipt.get("parameter_submission_support") or {}
    for name in expected_parameters:
        if support.get(name) is not True:
            reasons.append(f"parameter_submission_unverified:{name}")
    if receipt.get("seed_submission_supported") is not True:
        reasons.append("seed_submission_unverified")
    if receipt.get("fresh_session_per_call") is not True:
        reasons.append("fresh_session_not_verified")
    if receipt.get("retry_limit") != 0:
        reasons.append("retry_policy_mismatch")
    if receipt.get("silent_fallback") is not False:
        reasons.append("silent_fallback_not_denied")
    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "honoring_attestation": str(receipt.get("honoring_attestation") or "unavailable"),
        "contract_version": CONTRACT_VERSION,
    }


@dataclass(frozen=True)
class ProviderResult:
    request_id: str
    raw_response: str
    returned_model: str
    metrics: dict[str, Any]
    seconds: float
    provider_contacted: bool
    submitted_body_sha256: str
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id, "raw_response": self.raw_response,
            "returned_model": self.returned_model, "metrics": dict(self.metrics),
            "seconds": self.seconds, "provider_contacted": self.provider_contacted,
            "submitted_body_sha256": self.submitted_body_sha256, "error": self.error,
        }


class OllamaExperimentAdapter:
    """Single-attempt, fresh-session Ollama adapter for later authorized use."""

    def __init__(self, endpoint: str = "http://localhost:11434") -> None:
        self.endpoint = str(endpoint).rstrip("/")

    def inspect_model(self, model: str, *, allow_provider_contact: bool = False) -> dict[str, Any]:
        if not allow_provider_contact:
            raise PermissionError("provider_contact_not_authorized")
        import requests

        with requests.Session() as session:
            version_response = session.get(self.endpoint + "/api/version", timeout=(5, 30))
            version_response.raise_for_status()
            provider_version = str(version_response.json().get("version") or "")
            response = session.get(self.endpoint + "/api/tags", timeout=(5, 30))
            response.raise_for_status()
            payload = response.json()
        matches = [row for row in payload.get("models", []) if row.get("name") == model or row.get("model") == model]
        if len(matches) != 1:
            raise RuntimeError("configured_model_not_uniquely_resolved")
        row = matches[0]
        digest = str(row.get("digest") or "").lower()
        proposal = load_sampling()
        return {
            "provider": EXPECTED_PROVIDER, "provider_version": provider_version,
            "requested_model": model, "resolved_model": str(row.get("model") or row.get("name")),
            "model_content_digest": digest, "submitted_parameters": dict(proposal["parameters"]),
            "parameter_submission_support": {name: True for name in proposal["parameters"]},
            "seed_submission_supported": True, "fresh_session_per_call": True, "retry_limit": 0,
            "silent_fallback": False, "honoring_attestation": "not_provided_by_ollama",
            "provider_contacted": True,
        }

    def generate(self, request_id: str, body: Mapping[str, Any], *,
                 allow_provider_contact: bool = False) -> ProviderResult:
        if not allow_provider_contact:
            raise PermissionError("provider_contact_not_authorized")
        assert_minimal_semantic_body(body)
        import requests

        encoded = json.dumps(dict(body), sort_keys=True, separators=(",", ":"))
        started = time.perf_counter()
        try:
            # A new Session per call prevents conversation/session reuse. Requests performs no
            # application-level retry here, and no response-repair request exists.
            with requests.Session() as session:
                response = session.post(self.endpoint + "/api/generate", json=dict(body), timeout=(5, 900))
                response.raise_for_status()
                payload = response.json()
            returned_model = str(payload.get("model") or body["model"])
            if returned_model != body["model"]:
                raise RuntimeError("provider_model_fallback_detected")
            metrics = {key: payload.get(key) for key in
                       ("prompt_eval_count", "eval_count", "total_duration", "load_duration") if payload.get(key) is not None}
            return ProviderResult(
                request_id=request_id, raw_response=str(payload.get("response") or ""),
                returned_model=returned_model, metrics=metrics,
                seconds=round(time.perf_counter() - started, 6), provider_contacted=True,
                submitted_body_sha256=canonical_digest(encoded),
            )
        except Exception as error:
            return ProviderResult(
                request_id=request_id, raw_response="", returned_model="", metrics={},
                seconds=round(time.perf_counter() - started, 6), provider_contacted=True,
                submitted_body_sha256=canonical_digest(encoded),
                error=f"{type(error).__name__}:{error}"[:400],
            )


__all__ = [
    "CONTRACT_VERSION", "EXPECTED_PROVIDER", "ProviderResult", "OllamaExperimentAdapter",
    "configuration_digest", "prepared_configuration", "verify_preflight_receipt",
]
