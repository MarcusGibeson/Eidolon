from __future__ import annotations

"""Small adapters for capturing existing Eidolon validated outcomes.

They intentionally do not monkey-patch provider calls or silently collect data.
Callers must provide an explicit runtime root and capture_authorized=True.
"""

from pathlib import Path
from typing import Any, Mapping

from model_training.training_record import record_training_interaction
from model_training.training_capture_runtime import finalize_capture_result

CONTRACT_VERSION = "v2503.4.16"


def capture_software_attempt(
    *, runtime_root: str | Path | None,
    capture_authorized: bool,
    prompt_or_context: Mapping[str, Any] | str,
    model_output: Mapping[str, Any] | str,
    verification: Mapping[str, Any],
    corrected_output: Mapping[str, Any] | str | None = None,
    provenance: Mapping[str, Any] | None = None,
    auto_sanitize: bool = False,
) -> dict[str, Any]:
    result = record_training_interaction(
        runtime_root=runtime_root,
        capture_authorized=capture_authorized,
        task_type="software_repair" if corrected_output is not None else "software_development",
        input_payload=prompt_or_context,
        model_output=model_output,
        validation=dict(verification),
        corrected_output=corrected_output,
        source_system="isolated_coding_execution",
        provenance={"adapter_contract": CONTRACT_VERSION, **dict(provenance or {})},
    )
    return finalize_capture_result(result, runtime_root=runtime_root, capability="coding_repair", auto_sanitize=auto_sanitize)


def capture_research_synthesis(
    *, runtime_root: str | Path | None,
    capture_authorized: bool,
    research_context: Mapping[str, Any] | str,
    model_output: Mapping[str, Any] | str,
    validation: Mapping[str, Any],
    corrected_output: Mapping[str, Any] | str | None = None,
    provenance: Mapping[str, Any] | None = None,
    auto_sanitize: bool = False,
) -> dict[str, Any]:
    result = record_training_interaction(
        runtime_root=runtime_root,
        capture_authorized=capture_authorized,
        task_type="research_synthesis",
        input_payload=research_context,
        model_output=model_output,
        validation=dict(validation),
        corrected_output=corrected_output,
        source_system="governed_public_web_research_adapter",
        provenance={"adapter_contract": CONTRACT_VERSION, **dict(provenance or {})},
    )
    return finalize_capture_result(result, runtime_root=runtime_root, capability="research", auto_sanitize=auto_sanitize)


def capture_validated_outcome(
    *, runtime_root: str | Path | None, capture_authorized: bool, task_type: str,
    input_payload: Mapping[str, Any] | str, model_output: Mapping[str, Any] | str,
    validation: Mapping[str, Any], source_system: str,
    corrected_output: Mapping[str, Any] | str | None = None,
    provenance: Mapping[str, Any] | None = None, auto_sanitize: bool = False,
) -> dict[str, Any]:
    capability = "planning" if task_type == "planning" else "governance"
    result = record_training_interaction(
        runtime_root=runtime_root, capture_authorized=capture_authorized,
        task_type=task_type, input_payload=input_payload, model_output=model_output,
        validation=dict(validation), corrected_output=corrected_output,
        source_system=source_system,
        provenance={"adapter_contract": "v2503.4.37", **dict(provenance or {})},
    )
    return finalize_capture_result(result, runtime_root=runtime_root, capability=capability, auto_sanitize=auto_sanitize)
