from __future__ import annotations

"""Explicitly gated Ollama boundary for a later authorized G-ROUTE1 run."""

from dataclasses import dataclass
import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

from g_route1_execution_contract import canonical_json, json_digest, load_model_bindings


CONTRACT_VERSION = "g-route1.ollama-provider.v1"


@dataclass(frozen=True)
class ProviderResult:
    request_id: str
    requested_model: str
    returned_model: str
    raw_body_b64: str
    raw_body_sha256: str
    envelope: dict[str, Any]
    raw_output: str
    output_field: str
    metrics: dict[str, Any]
    latency_seconds: float
    provider_contacted: bool
    submitted_body_sha256: str
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id, "requested_model": self.requested_model,
            "returned_model": self.returned_model, "raw_body_b64": self.raw_body_b64,
            "raw_body_sha256": self.raw_body_sha256, "envelope": dict(self.envelope),
            "raw_output": self.raw_output, "output_field": self.output_field,
            "metrics": dict(self.metrics), "latency_seconds": self.latency_seconds,
            "provider_contacted": self.provider_contacted,
            "submitted_body_sha256": self.submitted_body_sha256, "error": self.error,
        }


def verify_model_receipts(receipts: list[Mapping[str, Any]]) -> dict[str, Any]:
    frozen = load_model_bindings()
    expected = {row["model"]: row for row in frozen["bindings"]}
    reasons: list[str] = []
    if len(receipts) != len(expected):
        reasons.append("model_receipt_count_mismatch")
    for receipt in receipts:
        model = str(receipt.get("requested_model") or "")
        binding = expected.get(model)
        if binding is None:
            reasons.append(f"unknown_model_receipt:{model}")
            continue
        if receipt.get("resolved_model") != model:
            reasons.append(f"model_fallback_or_alias_drift:{model}")
        if receipt.get("manifest_digest") != binding["manifest_digest"]:
            reasons.append(f"model_manifest_digest_mismatch:{model}")
        if receipt.get("model_blob_sha256") != binding["model_blob_sha256"]:
            reasons.append(f"model_blob_digest_mismatch:{model}")
        if receipt.get("provider_version") != frozen["provider_version"]:
            reasons.append(f"provider_version_mismatch:{model}")
        if receipt.get("generation_configuration") != frozen["generation_configuration"]:
            reasons.append(f"generation_configuration_mismatch:{model}")
        if receipt.get("silent_fallback") is not False:
            reasons.append(f"silent_fallback_not_denied:{model}")
    return {
        "valid": not reasons, "reasons": sorted(set(reasons)),
        "provider_contacted_for_generation": False,
        "honoring_attestation": "not_provided_by_ollama",
    }


def extract_output(envelope: Mapping[str, Any]) -> tuple[str, str]:
    response = envelope.get("response")
    thinking = envelope.get("thinking")
    if isinstance(response, str) and response.strip():
        return response, "response"
    if isinstance(thinking, str) and thinking.strip():
        return thinking, "thinking_fallback_when_response_empty"
    return "", "none"


class OllamaRouteAdapter:
    def __init__(self, endpoint: str = "http://127.0.0.1:11434") -> None:
        self.endpoint = endpoint.rstrip("/")

    def inspect_models(self, *, allow_metadata_inspection: bool = False) -> list[dict[str, Any]]:
        """Resolve installed identities without sending a generation request."""
        if not allow_metadata_inspection:
            raise PermissionError("g_route1_metadata_inspection_not_authorized")
        import requests

        frozen = load_model_bindings()
        with requests.Session() as session:
            version_response = session.get(self.endpoint + "/api/version", timeout=(5, 30))
            version_response.raise_for_status()
            tags_response = session.get(self.endpoint + "/api/tags", timeout=(5, 30))
            tags_response.raise_for_status()
        version = str(version_response.json().get("version") or "")
        installed = {str(row.get("model") or row.get("name") or ""): row for row in tags_response.json().get("models", [])}
        receipts = []
        blob_root = Path.home() / ".ollama" / "models" / "blobs"
        for binding in frozen["bindings"]:
            model = binding["model"]
            row = installed.get(model, {})
            blob_exists = (blob_root / ("sha256-" + binding["model_blob_sha256"])).is_file()
            receipts.append({
                "provider_version": version, "requested_model": model,
                "resolved_model": str(row.get("model") or row.get("name") or ""),
                "manifest_digest": str(row.get("digest") or ""),
                "model_blob_sha256": binding["model_blob_sha256"] if blob_exists else "",
                "generation_configuration": frozen["generation_configuration"],
                "silent_fallback": False, "provider_generation_contacted": False,
                "configuration_honoring_attestation": "not_provided_by_ollama",
            })
        return receipts

    def generate(self, request_id: str, body: Mapping[str, Any], *, allow_generation: bool = False) -> ProviderResult:
        if not allow_generation:
            raise PermissionError("g_route1_provider_generation_not_authorized")
        import requests

        submitted = canonical_json(dict(body))
        started = time.perf_counter()
        raw = b""
        envelope: dict[str, Any] = {}
        try:
            with requests.Session() as session:
                response = session.post(self.endpoint + "/api/generate", json=dict(body), timeout=(5, 1200))
                raw = bytes(response.content)
                response.raise_for_status()
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("provider_envelope_not_object")
            envelope = value
            returned = str(value.get("model") or "")
            if returned != body.get("model"):
                raise RuntimeError("provider_model_fallback_detected")
            output, field = extract_output(value)
            metrics = {key: value.get(key) for key in (
                "prompt_eval_count", "eval_count", "total_duration", "load_duration", "done_reason"
            ) if value.get(key) is not None}
            return ProviderResult(
                request_id=request_id, requested_model=str(body["model"]), returned_model=returned,
                raw_body_b64=base64.b64encode(raw).decode("ascii"), raw_body_sha256=hashlib.sha256(raw).hexdigest(),
                envelope=envelope, raw_output=output, output_field=field, metrics=metrics,
                latency_seconds=round(time.perf_counter() - started, 6), provider_contacted=True,
                submitted_body_sha256=json_digest(dict(body)),
            )
        except Exception as exc:
            return ProviderResult(
                request_id=request_id, requested_model=str(body.get("model") or ""), returned_model=str(envelope.get("model") or ""),
                raw_body_b64=base64.b64encode(raw).decode("ascii"), raw_body_sha256=hashlib.sha256(raw).hexdigest(),
                envelope=envelope, raw_output="", output_field="none", metrics={},
                latency_seconds=round(time.perf_counter() - started, 6), provider_contacted=True,
                submitted_body_sha256=json_digest(dict(body)), error=f"{type(exc).__name__}:{exc}"[:500],
            )


__all__ = ["CONTRACT_VERSION", "ProviderResult", "OllamaRouteAdapter", "extract_output", "verify_model_receipts"]
