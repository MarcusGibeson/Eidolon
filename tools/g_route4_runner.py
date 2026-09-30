# forked from g_route3_runner
from __future__ import annotations

"""The R7 runner surface for G-ROUTE4 (design "Identity and separation": the runner fork provides only what R7 uses).

It provides exactly: ``GovernedOllamaProvider``, the fixed endpoint, ``verify_model_receipts``, ``sanitize_strings``
and the guarded paths. The forked module's superseded R6 collection path, its coding sandbox calls and its activity
reporting are not carried: this module imports neither the coding runner nor the persistence module. Collection,
scoring, the table freeze and Phase B′ are the R7 lifecycle's (``g_route4_lifecycle`` through ``g_route4_launch``).
"""

from typing import Any, Mapping

from g_route4_contract import load_model_bindings

CONTRACT_VERSION = "g-route4.runner.v1"
OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
GUARDED_PATHS = (
    "experiments/G-ROUTE4-candidate/model_bindings.json",
    "experiments/G-ROUTE4-candidate/thresholds.json",
    "experiments/G-ROUTE4-candidate/schedule_a.json",
    "experiments/G-ROUTE4-candidate/schedule_b.json",
    "experiments/G-ROUTE4-candidate/corpus_a.json",
    "experiments/G-ROUTE4-candidate/corpus_b.json",
    "experiments/G-ROUTE4-candidate/gold_a.json",
    "experiments/G-ROUTE4-candidate/gold_b.json",
    "experiments/G-ROUTE4-candidate/fixture_families.json",
    "experiments/G-ROUTE1-candidate/prompt_profiles.json", "experiments/G-ROUTE1-candidate/model_bindings.json",
    "tools/g_route1_validators.py", "tools/g_route1_operational.py", "tools/g_route1_provider.py",
    "tools/g_route1_contract.py", "tools/g_route1_execution_contract.py", "tools/g_route1_freeze.py",
    "tools/g_route2_normalization.py",
    "tools/g_route3_operational.py", "tools/g_route3_triggers.py", "tools/g_route3_conversation.py",
    "tools/g_route3_semantics.py", "tools/g_route3_routing.py",
    "tools/g_route4_contract.py", "tools/g_route4_qualification.py", "tools/g_route4_validation.py",
    "tools/g_route4_freeze.py", "tools/g_route4_launch.py", "tools/g_route4_runner.py",
)


def sanitize_strings(value: Any) -> Any:
    """Replace lone surrogates (from JSON escapes such as \\ud800) so a record can always be sealed as UTF-8."""
    if isinstance(value, str):
        return value.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
    if isinstance(value, list):
        return [sanitize_strings(item) for item in value]
    if isinstance(value, dict):
        return {sanitize_strings(key): sanitize_strings(item) for key, item in value.items()}
    return value


def verify_model_receipts(receipts: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Model identity preflight against G-ROUTE4's own frozen, guarded bindings."""
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
    return {"valid": not reasons, "reasons": sorted(set(reasons))}


class GovernedOllamaProvider:
    """The only provider the authorized path accepts. It builds its own Ollama adapter; nothing is injected."""

    synthetic_provider = False

    def __init__(self) -> None:
        from g_route1_provider import OllamaRouteAdapter
        self.endpoint = OLLAMA_ENDPOINT          # fixed: the authorized path cannot be pointed elsewhere
        self.adapter = OllamaRouteAdapter(self.endpoint)

    def model_receipts(self) -> list[dict[str, Any]]:
        return self.adapter.inspect_models(allow_metadata_inspection=True)

    def __call__(self, call_id: str, body: Mapping[str, Any]):
        return self.adapter.generate(call_id, body, allow_generation=True)


__all__ = ["CONTRACT_VERSION", "OLLAMA_ENDPOINT", "GUARDED_PATHS", "sanitize_strings", "verify_model_receipts",
           "GovernedOllamaProvider"]
