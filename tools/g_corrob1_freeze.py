from __future__ import annotations

"""Prepare and verify a non-authoritative G-CORROB1-R2 implementation manifest.

This tool cannot create an execution freeze or authorize a provider call.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from g_corrob1_contract import ROOT, DATA, canonical_digest, digest_file


CONTRACT_VERSION = "g-corrob1.r2.freeze-preparation-candidate.1"
CANDIDATE = DATA / "IMPLEMENTATION_FREEZE_CANDIDATE.json"
EXECUTION_CANDIDATE = DATA / "EXECUTION_FREEZE_CANDIDATE.json"
PREFLIGHT = DATA / "PROVIDER_CONFIGURATION_PREFLIGHT.json"
ARTIFACTS = (
    "experiments/G-CORROB1-candidate-r2/DESIGN.md",
    "experiments/G-CORROB1-candidate-r2/SEMANTIC_CONTRACT.md",
    "experiments/G-CORROB1-candidate-r2/corpus.json",
    "experiments/G-CORROB1-candidate-r2/gold_candidate.json",
    "experiments/G-CORROB1-candidate-r2/prompt.txt",
    "experiments/G-CORROB1-candidate-r2/sampling_proposal.json",
    "experiments/G-CORROB1-candidate-r2/METRICS.md",
    "experiments/G-CORROB1-candidate-r2/ABORT_RULES.md",
    "experiments/G-CORROB1-candidate-r2/ACTIVITY_SPEC.md",
    "experiments/G-CORROB1-candidate-r2/STRUCTURAL_PILOT_SPEC.md",
    "experiments/G-CORROB1-candidate-r2/SECOND_PREREGISTRATION_AUDIT.md",
    "experiments/G-CORROB1-candidate-r2/THRESHOLD_PROVENANCE.md",
    "experiments/G-CORROB1-candidate-r2/GOLD_IMPLEMENTATION_AUDIT.md",
    "experiments/G-CORROB1-candidate-r2/IMPLEMENTATION_AUDIT.md",
    "experiments/G-CORROB1-candidate-r2/PREPILOT_INDEPENDENT_GOLD_SIGNOFF.md",
    "experiments/G-CORROB1-candidate-r2/HISTORICAL_PRE_R22_CANDIDATE.md",
    "experiments/G-CORROB1-candidate-r2/R22_REPAIR_RECORD.md",
    "experiments/G-CORROB1-candidate-r2/PREPILOT_RENEWED_GOLD_SIGNOFF.md",
    "experiments/G-CORROB1-candidate-r2/PROVIDER_CONFIGURATION_PREFLIGHT.json",
    "experiments/G-CORROB1-candidate-r2/PROVIDER_CONFIGURATION_PREFLIGHT.md",
    "tools/g_evid1_policy.py",
    "conscious_agent/activity.py",
    "tools/g_corrob1_contract.py",
    "tools/g_corrob1_policy.py",
    "tools/g_corrob1_provider.py",
    "tools/g_corrob1_persistence.py",
    "tools/g_corrob1_activity.py",
    "tools/g_corrob1_runner.py",
    "tools/g_corrob1_scorer.py",
    "tools/g_corrob1_freeze.py",
    "tools/g_corrob1_implementation_tests.py",
    "tools/g_corrob1_prepilot_gold_signoff_tests.py",
    "tools/g_corrob1_execution_freeze_tests.py",
)


def build_manifest(root: Path = ROOT) -> dict[str, Any]:
    missing = [path for path in ARTIFACTS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("freeze_candidate_artifacts_missing:" + ",".join(missing))
    artifacts = {path: digest_file(root / path) for path in ARTIFACTS}
    seed = {
        "contract_version": CONTRACT_VERSION,
        "candidate_id": "G-CORROB1-candidate-r2-implementation",
        "status": "implementation_candidate_not_execution_frozen",
        "execution_authorized": False,
        "execution_frozen": False,
        "provider_contact_authorized": False,
        "pilot_authorized": False,
        "belief_effects": "none",
        "base_checkpoint": "e1d9fedb4975bf98eae03627ff7cd37dd53ce361",
        "implementation_commit": "66ee6d90696778d631239ee944dad611b583195f",
        "blocking_gold_audit_commit": "5cfae23c1e2d3a3e52dc92c4dec0cb13eb5a44ac",
        "second_audit_sha256": "a06871c1f025526baecaa3724e6e6f7d2929398b745f0e6dcc471c4253331613",
        "revision_manifest_sha256": "5b7587b4a1a706e9a04899c90aafef0b867c568c31c02fa47f902fc275f88792",
        "digest_convention": "sha256; CRLF and CR normalized to LF",
        "artifacts": artifacts,
        "unresolved_execution_freeze_gates": [
            "provider cannot attest that every submitted option is honored",
            "authorized structural pilot",
            "post-pilot execution-freeze review and explicit operator authorization",
        ],
    }
    seed["candidate_content_sha256"] = canonical_digest(json.dumps(seed, sort_keys=True, separators=(",", ":")))
    return seed


def verify_manifest(manifest: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    expected = build_manifest(root)
    reasons = []
    if dict(manifest) != expected:
        for key in sorted(set(expected) | set(manifest)):
            if expected.get(key) != manifest.get(key):
                reasons.append(f"manifest_mismatch:{key}")
    return {"valid": not reasons, "reasons": reasons, "execution_frozen": False,
            "execution_authorized": False, "provider_contacted": False}


def verify_execution_manifest(manifest: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    """Verify a later explicitly authorized execution manifest, never a candidate."""
    reasons = []
    if manifest.get("status") != "execution_frozen_authorized" or manifest.get("execution_frozen") is not True:
        reasons.append("not_an_execution_freeze")
    if manifest.get("candidate_id") != "G-CORROB1-candidate-r2-implementation":
        reasons.append("candidate_identity_mismatch")
    if manifest.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(ARTIFACTS):
        reasons.append("execution_artifact_set_mismatch")
    else:
        for path, expected in artifacts.items():
            target = root / path
            if not target.is_file() or digest_file(target) != expected:
                reasons.append(f"execution_artifact_digest_mismatch:{path}")
    if manifest.get("independent_gold_signoff_complete") is not True:
        reasons.append("independent_gold_signoff_incomplete")
    if not str(manifest.get("model_content_digest") or ""):
        reasons.append("model_content_digest_missing")
    if manifest.get("experiment_authorized") is not True:
        reasons.append("experiment_not_authorized")
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "provider_contacted": False}


def build_execution_freeze_candidate(root: Path = ROOT) -> dict[str, Any]:
    implementation = build_manifest(root)
    preflight_path = root / PREFLIGHT.relative_to(ROOT)
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    seed = {
        "contract_version": "g-corrob1.r2.execution-freeze-candidate.1",
        "candidate_id": "G-CORROB1-candidate-r2-implementation",
        "status": "execution_freeze_candidate_pending_operator_review",
        "implementation_complete": True,
        "execution_frozen": True,
        "execution_authorized": False,
        "pilot_authorized": False,
        "experiment_authorized": False,
        "provider_contact_authorized": False,
        "belief_effects": "none",
        "implementation_commit": "66ee6d90696778d631239ee944dad611b583195f",
        "blocking_gold_audit_commit": "5cfae23c1e2d3a3e52dc92c4dec0cb13eb5a44ac",
        "independent_gold_signoff_complete": True,
        "independent_gold_signoff_sha256": implementation["artifacts"][
            "experiments/G-CORROB1-candidate-r2/PREPILOT_RENEWED_GOLD_SIGNOFF.md"
        ],
        "model_provider": preflight["provider"],
        "provider_version": preflight["provider_version"],
        "requested_model": preflight["requested_model"],
        "resolved_model": preflight["resolved_model"],
        "model_content_digest": preflight["model_manifest_sha256"],
        "provider_configuration_sha256": digest_file(preflight_path),
        "model_configuration_digest": configuration_digest_for_manifest(preflight),
        "option_honoring_attestation": preflight["honoring_attestation"],
        "semantic_generation_calls": 0,
        "pilot_launch_count": 0,
        "experiment_launch_count": 0,
        "digest_convention": "sha256; CRLF and CR normalized to LF",
        "artifacts": dict(implementation["artifacts"]),
        "unresolved_limitations": [
            "Ollama does not attest that every submitted generation option is honored",
            "seed behavior and request capture require an explicitly authorized mechanical pilot",
            "native Activity UI rendering remains untested in this Tcl/Tk-deficient environment",
        ],
    }
    seed["execution_freeze_content_sha256"] = canonical_digest(
        json.dumps(seed, sort_keys=True, separators=(",", ":"))
    )
    return seed


def configuration_digest_for_manifest(preflight: Mapping[str, Any]) -> str:
    value = {
        "provider": preflight["provider"],
        "provider_version": preflight["provider_version"],
        "requested_model": preflight["requested_model"],
        "resolved_model": preflight["resolved_model"],
        "model_manifest_sha256": preflight["model_manifest_sha256"],
        "experiment_submission": preflight["experiment_submission"],
    }
    return canonical_digest(json.dumps(value, sort_keys=True, separators=(",", ":")))


def verify_execution_freeze_candidate(
    manifest: Mapping[str, Any], root: Path = ROOT
) -> dict[str, Any]:
    expected = build_execution_freeze_candidate(root)
    reasons = []
    if dict(manifest) != expected:
        for key in sorted(set(expected) | set(manifest)):
            if expected.get(key) != manifest.get(key):
                reasons.append(f"execution_candidate_mismatch:{key}")
    if manifest.get("pilot_authorized") is not False:
        reasons.append("pilot_authorization_must_remain_false")
    if manifest.get("experiment_authorized") is not False:
        reasons.append("experiment_authorization_must_remain_false")
    if verify_execution_manifest(manifest, root)["valid"]:
        reasons.append("candidate_must_not_be_executable")
    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "execution_frozen": manifest.get("execution_frozen") is True,
        "pilot_authorized": False,
        "experiment_authorized": False,
        "provider_contacted_for_semantic_observations": False,
    }


def write_execution_freeze_candidate(path: Path = EXECUTION_CANDIDATE) -> dict[str, Any]:
    manifest = build_execution_freeze_candidate()
    text = json.dumps(manifest, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise FileExistsError("conflicting_execution_freeze_candidate_exists")
    path.write_text(text, encoding="utf-8", newline="\n")
    return manifest


def write_candidate(path: Path = CANDIDATE) -> dict[str, Any]:
    manifest = build_manifest()
    text = json.dumps(manifest, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise FileExistsError("conflicting_candidate_manifest_exists")
    path.write_text(text, encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or verify a non-executable G-CORROB1-R2 freeze candidate.")
    parser.add_argument("--write-candidate", action="store_true")
    parser.add_argument("--write-execution-candidate", action="store_true")
    parser.add_argument("--verify-execution-candidate", action="store_true")
    args = parser.parse_args()
    if args.write_execution_candidate or args.verify_execution_candidate:
        manifest = (
            write_execution_freeze_candidate()
            if args.write_execution_candidate
            else json.loads(EXECUTION_CANDIDATE.read_text(encoding="utf-8"))
        )
        result = verify_execution_freeze_candidate(manifest)
        print(json.dumps(result, indent=1, sort_keys=True))
        return 0 if result["valid"] else 1
    manifest = write_candidate() if args.write_candidate else json.loads(CANDIDATE.read_text(encoding="utf-8"))
    result = verify_manifest(manifest)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
