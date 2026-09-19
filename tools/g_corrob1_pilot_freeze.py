from __future__ import annotations

"""Prepare and verify a non-authoritative, pilot-capable G-CORROB1 candidate."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from g_corrob1_contract import ROOT, canonical_digest, digest_file
from g_corrob1_freeze import configuration_digest_for_manifest


DATA = ROOT / "experiments" / "G-CORROB1-pilot-capable-r3"
CANDIDATE = DATA / "PILOT_CAPABLE_FREEZE_CANDIDATE.json"
PREFLIGHT = ROOT / "experiments" / "G-CORROB1-candidate-r2" / "PROVIDER_CONFIGURATION_PREFLIGHT.json"
CONTRACT_VERSION = "g-corrob1.mechanical-pilot.freeze-candidate.1"
BASE_CHECKPOINT = "1d840379e7177968c1f744a49989d51f95453823"
PRODUCTION_CANDIDATE_SHA256 = "366a787cbf901f25e795d72ad4f71bd09a1f5318a51ed6549940bc9c3aff5114"

ARTIFACTS = (
    "experiments/G-CORROB1-candidate-r2/EXECUTION_FREEZE_CANDIDATE.json",
    "experiments/G-CORROB1-candidate-r2/MECHANICAL_PILOT_ATTEMPT_1_BLOCKER.md",
    "experiments/G-CORROB1-candidate-r2/corpus.json",
    "experiments/G-CORROB1-candidate-r2/gold_candidate.json",
    "experiments/G-CORROB1-candidate-r2/prompt.txt",
    "experiments/G-CORROB1-candidate-r2/sampling_proposal.json",
    "experiments/G-CORROB1-candidate-r2/PROVIDER_CONFIGURATION_PREFLIGHT.json",
    "experiments/G-CORROB1-pilot-capable-r3/PILOT_FIXTURE.json",
    "experiments/G-CORROB1-pilot-capable-r3/PILOT_SPEC.md",
    "experiments/G-CORROB1-pilot-capable-r3/PILOT_AUTHORIZATION_SPEC.md",
    "experiments/G-CORROB1-pilot-capable-r3/PILOT_IMPLEMENTATION_AUDIT.md",
    "conscious_agent/activity.py",
    "tools/g_evid1_policy.py",
    "tools/g_corrob1_contract.py",
    "tools/g_corrob1_policy.py",
    "tools/g_corrob1_provider.py",
    "tools/g_corrob1_persistence.py",
    "tools/g_corrob1_activity.py",
    "tools/g_corrob1_runner.py",
    "tools/g_corrob1_scorer.py",
    "tools/g_corrob1_freeze.py",
    "tools/g_corrob1_pilot_activity.py",
    "tools/g_corrob1_pilot_verifier.py",
    "tools/g_corrob1_live_pilot.py",
    "tools/g_corrob1_pilot_freeze.py",
    "tools/g_corrob1_pilot_tests.py",
)


def _canonical_manifest_sha256(manifest: Mapping[str, Any]) -> str:
    return canonical_digest(json.dumps(dict(manifest), sort_keys=True, separators=(",", ":")))


def candidate_file_sha256(manifest: Mapping[str, Any]) -> str:
    """Digest the exact deterministic bytes emitted by ``write_candidate``."""
    text = json.dumps(dict(manifest), indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    return canonical_digest(text)


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    missing = [path for path in ARTIFACTS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("pilot_freeze_artifacts_missing:" + ",".join(missing))
    production_candidate_path = root / "experiments/G-CORROB1-candidate-r2/EXECUTION_FREEZE_CANDIDATE.json"
    if digest_file(production_candidate_path) != PRODUCTION_CANDIDATE_SHA256:
        raise ValueError("historical_production_candidate_digest_mismatch")
    production_candidate = json.loads(production_candidate_path.read_text(encoding="utf-8"))
    production_artifacts = dict(production_candidate.get("artifacts") or {})
    for path, expected in production_artifacts.items():
        target = root / path
        if not target.is_file() or digest_file(target) != expected:
            raise ValueError(f"historical_production_artifact_drift:{path}")
    preflight = json.loads((root / PREFLIGHT.relative_to(ROOT)).read_text(encoding="utf-8"))
    artifacts = dict(production_artifacts)
    artifacts["experiments/G-CORROB1-candidate-r2/EXECUTION_FREEZE_CANDIDATE.json"] = digest_file(
        production_candidate_path
    )
    artifacts.update({path: digest_file(root / path) for path in ARTIFACTS})
    seed = {
        "contract_version": CONTRACT_VERSION,
        "candidate_id": "G-CORROB1-pilot-capable-r3",
        "status": "pilot_capable_freeze_candidate_pending_operator_review",
        "base_checkpoint": BASE_CHECKPOINT,
        "production_candidate_sha256": PRODUCTION_CANDIDATE_SHA256,
        "production_artifacts_unchanged": True,
        "pilot_capable": True,
        "pilot_frozen": True,
        "pilot_authorized": False,
        "provider_contact_authorized": False,
        "execution_authorized": False,
        "experiment_authorized": False,
        "belief_effects": "none",
        "record_namespace": "g_corrob1_mechanical_pilot",
        "expected_generation_calls": 2,
        "expected_pairs": 1,
        "production_expected_generation_calls": 192,
        "production_expected_pairs": 96,
        "model_provider": preflight["provider"],
        "provider_version": preflight["provider_version"],
        "requested_model": preflight["requested_model"],
        "resolved_model": preflight["resolved_model"],
        "model_content_digest": preflight["model_manifest_sha256"],
        "model_configuration_digest": configuration_digest_for_manifest(preflight),
        "submitted_parameters": dict(preflight["experiment_submission"]),
        "option_honoring_attestation": preflight["honoring_attestation"],
        "append_only_persistence": True,
        "semantic_evaluation_permitted": False,
        "production_result_permitted": False,
        "semantic_generation_calls": 0,
        "pilot_launch_count": 0,
        "experiment_launch_count": 0,
        "digest_convention": "sha256; CRLF and CR normalized to LF",
        "artifacts": artifacts,
        "abort_conditions": [
            "authorization_missing_or_mismatched", "wrong_model_or_model_digest",
            "provider_fallback_or_configuration_mismatch", "malformed_or_truncated_response",
            "wrong_binding_or_assessor_identity", "duplicate_or_missing_assessor_or_pair",
            "stale_records_or_digest_mismatch", "persistence_interruption",
            "activity_execution_mutation", "pilot_namespace_cross_contamination",
        ],
        "unresolved_limitations": [
            "Ollama does not attest that every submitted generation option is honored",
            "seed submission is verifiable but internal seed honoring requires the authorized live pilot",
            "native Activity UI rendering remains untested in this Tcl/Tk-deficient environment",
        ],
    }
    seed["pilot_freeze_content_sha256"] = _canonical_manifest_sha256(seed)
    return seed


def verify_candidate(manifest: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        expected = build_candidate(root)
    except Exception as error:
        return {"valid": False, "reasons": [f"candidate_rebuild_failed:{type(error).__name__}:{error}"]}
    if dict(manifest) != expected:
        for key in sorted(set(expected) | set(manifest)):
            if expected.get(key) != manifest.get(key):
                reasons.append(f"pilot_candidate_mismatch:{key}")
    if manifest.get("pilot_authorized") is not False:
        reasons.append("candidate_must_not_grant_pilot_authority")
    if manifest.get("experiment_authorized") is not False or manifest.get("execution_authorized") is not False:
        reasons.append("candidate_must_not_grant_experiment_authority")
    if manifest.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")
    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "pilot_capable": manifest.get("pilot_capable") is True,
        "pilot_authorized": False,
        "experiment_authorized": False,
        "provider_contacted": False,
    }


def verify_pilot_authorization(authorization: Mapping[str, Any] | None, root: Path = ROOT) -> dict[str, Any]:
    row = dict(authorization or {})
    reasons: list[str] = []
    manifest = row.get("pilot_manifest")
    if not isinstance(manifest, Mapping):
        return {"valid": False, "reasons": ["pilot_manifest_missing"]}
    candidate_check = verify_candidate(manifest, root)
    if not candidate_check["valid"]:
        reasons.extend("candidate:" + reason for reason in candidate_check["reasons"])
    expected = str(row.get("pilot_manifest_sha256") or "")
    calculated = candidate_file_sha256(manifest)
    if expected != calculated or len(expected) != 64:
        reasons.append("pilot_manifest_digest_mismatch")
    if row.get("pilot_authorized") is not True:
        reasons.append("pilot_not_authorized")
    if row.get("provider_contact_authorized") is not True:
        reasons.append("provider_contact_not_authorized")
    if row.get("experiment_authorized") is not False:
        reasons.append("full_experiment_authority_must_be_false")
    if row.get("expected_generation_calls") != 2 or row.get("expected_pairs") != 1:
        reasons.append("pilot_denominator_authority_mismatch")
    authorization_id = str(row.get("authorization_id") or "")
    if not authorization_id.startswith("gcorrob1pilot_auth_"):
        reasons.append("pilot_authorization_id_invalid")
    if row.get("operator_confirmation") != f"Authorize G-CORROB1 live mechanical pilot {expected}":
        reasons.append("pilot_operator_confirmation_mismatch")
    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "authorization_id": authorization_id,
        "pilot_manifest_sha256": expected,
        "experiment_authorized": False,
    }


def write_candidate(path: Path = CANDIDATE) -> dict[str, Any]:
    manifest = build_candidate()
    text = json.dumps(manifest, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise FileExistsError("conflicting_pilot_freeze_candidate_exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or verify the non-authoritative pilot-capable candidate.")
    parser.add_argument("--write-candidate", action="store_true")
    args = parser.parse_args()
    manifest = write_candidate() if args.write_candidate else json.loads(CANDIDATE.read_text(encoding="utf-8"))
    result = verify_candidate(manifest)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DATA", "CANDIDATE", "PREFLIGHT", "CONTRACT_VERSION", "ARTIFACTS", "build_candidate",
    "candidate_file_sha256", "verify_candidate", "verify_pilot_authorization", "write_candidate",
]
