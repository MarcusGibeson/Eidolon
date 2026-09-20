from __future__ import annotations

"""Freeze preparation for the exact-bound conversational execution capability.

The candidate produced here is non-authorizing. A later operator authorization
must contain a separately constructed execution manifest derived exactly from
this candidate and must pass ``verify_authorized_execution_manifest``.
"""

import json
from pathlib import Path
from typing import Any, Mapping

from g_corrob1_contract import ROOT, canonical_digest, digest_file
from g_corrob1_freeze import configuration_digest_for_manifest


DATA = ROOT / "experiments" / "G-CORROB1-authorized-execution-r5"
CANDIDATE = DATA / "EXECUTION_CAPABILITY_FREEZE_CANDIDATE.json"
CONTRACT_VERSION = "g-corrob1.r2.authorized-execution-capability-freeze.1"
MANIFEST_ID = "G-CORROB1-R2"
BASE_CHECKPOINT = "3ecb1930b55ccd83b0dcc6c1139346ae9413cd97"
PROVIDER_ENVELOPE_CANDIDATE_SHA256 = "758c4b8683df43d43cf3299db76b034563e34d2d38259b0f06d4cee5056b28a2"

ARTIFACTS = (
    "experiments/G-CORROB1-candidate-r2/corpus.json",
    "experiments/G-CORROB1-candidate-r2/gold_candidate.json",
    "experiments/G-CORROB1-candidate-r2/prompt.txt",
    "experiments/G-CORROB1-candidate-r2/sampling_proposal.json",
    "experiments/G-CORROB1-candidate-r2/METRICS.md",
    "experiments/G-CORROB1-candidate-r2/THRESHOLD_PROVENANCE.md",
    "experiments/G-CORROB1-candidate-r2/ABORT_RULES.md",
    "experiments/G-CORROB1-candidate-r2/ACTIVITY_SPEC.md",
    "experiments/G-CORROB1-candidate-r2/PREPILOT_RENEWED_GOLD_SIGNOFF.md",
    "experiments/G-CORROB1-candidate-r2/PROVIDER_CONFIGURATION_PREFLIGHT.json",
    "experiments/G-CORROB1-pilot-envelope-r4/PILOT_CAPABLE_FREEZE_CANDIDATE.json",
    "experiments/G-CORROB1-authorized-execution-r5/AUTHORIZATION_SPEC.md",
    "experiments/G-CORROB1-authorized-execution-r5/IMPLEMENTATION_AUDIT.md",
    "conscious_agent/activity.py",
    "conscious_agent/json_storage.py",
    "conscious_agent/runtime_data_bootstrap.py",
    "conscious_agent/authorized_frozen_experiment_execution.py",
    "conscious_agent/chat_action_router.py",
    "conscious_agent/natural_language_action_routing.py",
    "conscious_agent/conversation_runtime.py",
    "tools/g_evid1_policy.py",
    "tools/g_corrob1_contract.py",
    "tools/g_corrob1_policy.py",
    "tools/g_corrob1_provider_envelope.py",
    "tools/g_corrob1_provider.py",
    "tools/g_corrob1_persistence.py",
    "tools/g_corrob1_activity.py",
    "tools/g_corrob1_runner.py",
    "tools/g_corrob1_scorer.py",
    "tools/g_corrob1_freeze.py",
    "tools/g_corrob1_execution_capability_freeze.py",
    "tools/g_corrob1_execution_capability_tests.py",
)


def _serialized_sha256(value: Mapping[str, Any]) -> str:
    return canonical_digest(json.dumps(dict(value), indent=1, ensure_ascii=False, sort_keys=True) + "\n")


def execution_manifest_sha256(value: Mapping[str, Any]) -> str:
    return canonical_digest(json.dumps(dict(value), sort_keys=True, separators=(",", ":")))


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    missing = [path for path in ARTIFACTS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("execution_capability_artifacts_missing:" + ",".join(missing))
    provider_candidate = root / "experiments/G-CORROB1-pilot-envelope-r4/PILOT_CAPABLE_FREEZE_CANDIDATE.json"
    if digest_file(provider_candidate) != PROVIDER_ENVELOPE_CANDIDATE_SHA256:
        raise ValueError("provider_envelope_candidate_digest_mismatch")
    preflight = json.loads(
        (root / "experiments/G-CORROB1-candidate-r2/PROVIDER_CONFIGURATION_PREFLIGHT.json").read_text(
            encoding="utf-8"
        )
    )
    seed = {
        "contract_version": CONTRACT_VERSION,
        "manifest_id": MANIFEST_ID,
        "candidate_id": "G-CORROB1-authorized-execution-r5",
        "status": "execution_capability_frozen_pending_separate_operator_authorization",
        "base_checkpoint": BASE_CHECKPOINT,
        "provider_envelope_candidate_sha256": PROVIDER_ENVELOPE_CANDIDATE_SHA256,
        "capability_frozen": True,
        "execution_frozen": True,
        "execution_authorized": False,
        "full_experiment_authorized": False,
        "provider_contact_authorized": False,
        "authorization_artifact_created": False,
        "one_run_only": True,
        "authorization_scope": "one_frozen_g_corrob1_r2_execution",
        "expected_generation_calls": 192,
        "expected_pairs": 96,
        "belief_effects": "none",
        "model_provider": preflight["provider"],
        "provider_version": preflight["provider_version"],
        "requested_model": preflight["requested_model"],
        "resolved_model": preflight["resolved_model"],
        "model_content_digest": preflight["model_manifest_sha256"],
        "model_configuration_digest": configuration_digest_for_manifest(preflight),
        "submitted_parameters": dict(preflight["experiment_submission"]),
        "provider_fallback_permitted": False,
        "retries_permitted": False,
        "chat_input_contract": "exact_manifest_id_only",
        "chat_can_create_authorization": False,
        "chat_can_override_paths_or_configuration": False,
        "terminal_projection": "run_id_state_reason_code_terminal_reference_only",
        "semantic_results_exposed_to_chat": False,
        "activity_operational_only": True,
        "provider_call_count": 0,
        "experiment_launch_count": 0,
        "digest_convention": "sha256; CRLF and CR normalized to LF for source files",
        "artifacts": {path: digest_file(root / path) for path in ARTIFACTS},
    }
    seed["capability_freeze_content_sha256"] = canonical_digest(
        json.dumps(seed, sort_keys=True, separators=(",", ":"))
    )
    return seed


def verify_candidate(value: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        expected = build_candidate(root)
    except Exception as error:
        return {"valid": False, "reasons": [f"candidate_rebuild_failed:{type(error).__name__}:{error}"]}
    if dict(value) != expected:
        for key in sorted(set(expected) | set(value)):
            if expected.get(key) != value.get(key):
                reasons.append(f"candidate_mismatch:{key}")
    for field in ("execution_authorized", "full_experiment_authorized", "provider_contact_authorized"):
        if value.get(field) is not False:
            reasons.append(f"candidate_must_not_grant:{field}")
    if value.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "provider_contacted": False}


def verify_authorized_execution_manifest(value: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        candidate = build_candidate(root)
        serialized = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        if not verify_candidate(serialized, root)["valid"]:
            reasons.append("installed_capability_candidate_invalid")
        candidate_file_sha = digest_file(CANDIDATE)
    except Exception as error:
        return {"valid": False, "reasons": [f"candidate_unavailable:{type(error).__name__}:{error}"]}

    row = dict(value or {})
    allowed_extra = {
        "authorization_manifest_contract", "execution_base_candidate_sha256",
        "status", "execution_authorized", "full_experiment_authorized",
        "provider_contact_authorized", "authorized_manifest_content_sha256",
    }
    if set(row) != set(candidate) | allowed_extra:
        reasons.append("authorized_manifest_fields_mismatch")
    for key, expected in candidate.items():
        if key in {"status", "execution_authorized", "full_experiment_authorized", "provider_contact_authorized"}:
            continue
        if row.get(key) != expected:
            reasons.append(f"authorized_manifest_candidate_drift:{key}")
    if row.get("authorization_manifest_contract") != "g-corrob1.r2.authorized-execution-manifest.1":
        reasons.append("authorized_manifest_contract_mismatch")
    if row.get("execution_base_candidate_sha256") != candidate_file_sha:
        reasons.append("execution_base_candidate_digest_mismatch")
    if row.get("status") != "execution_frozen_authorized_for_one_run":
        reasons.append("authorized_manifest_status_mismatch")
    for field in ("execution_authorized", "full_experiment_authorized", "provider_contact_authorized"):
        if row.get(field) is not True:
            reasons.append(f"authorized_manifest_missing:{field}")
    content = dict(row)
    supplied = str(content.pop("authorized_manifest_content_sha256", ""))
    calculated = canonical_digest(json.dumps(content, sort_keys=True, separators=(",", ":")))
    if supplied != calculated:
        reasons.append("authorized_manifest_content_digest_mismatch")
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "provider_contacted": False}


def write_candidate(path: Path = CANDIDATE) -> dict[str, Any]:
    value = build_candidate()
    text = json.dumps(value, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise FileExistsError("conflicting_execution_capability_candidate_exists")
    path.write_text(text, encoding="utf-8", newline="\n")
    return value


__all__ = [
    "DATA", "CANDIDATE", "CONTRACT_VERSION", "MANIFEST_ID", "ARTIFACTS",
    "build_candidate", "write_candidate", "verify_candidate",
    "verify_authorized_execution_manifest", "execution_manifest_sha256",
]
