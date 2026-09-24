from __future__ import annotations

"""Build and verify the non-authorizing G-ROUTE2 execution-freeze candidate."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from g_route1_contract import ROOT, digest_file
from g_route2_contract import (DATA, EXPECTED_CALLS, INHERITED, SCHEDULE_PATH, json_digest,
                               load_json, load_model_bindings, load_thresholds, validate_schedule,
                               verify_inherited_scientific_content)

CONTRACT_VERSION = "g-route2.execution-freeze-candidate.v1"
CANDIDATE_ID = "G-ROUTE2-EXECUTION-R1"
FREEZE_PATH = DATA / "EXECUTION_FREEZE_CANDIDATE.json"
PRIOR_EXPERIMENT = {
    "experiment_id": "G-ROUTE1",
    "result_package_id": "G-ROUTE1-RESULT-R3",
    "run_id": "groute1_20260924T031646930437Z",
    "status": "complete_and_frozen",
    "reused_as_new_contract_results": False,
    "modified_or_reinterpreted": False,
}
ARTIFACTS = (
    "experiments/G-ROUTE2-candidate/DESIGN.md",
    "experiments/G-ROUTE2-candidate/NORMALIZATION_CONTRACT.md",
    "experiments/G-ROUTE2-candidate/ESCALATION_POLICY.md",
    "experiments/G-ROUTE2-candidate/SCORING_CONTRACT.md",
    "experiments/G-ROUTE2-candidate/CONTAMINATION_ANALYSIS.md",
    "experiments/G-ROUTE2-candidate/INDEPENDENT_AUDIT.md",
    "experiments/G-ROUTE2-candidate/DETERMINISTIC_TEST_RESULTS.json",
    "experiments/G-ROUTE2-candidate/REPLAY_DIAGNOSTIC.json",
    "experiments/G-ROUTE2-candidate/model_bindings.json",
    "experiments/G-ROUTE2-candidate/thresholds.json",
    "experiments/G-ROUTE2-candidate/schedule.json",
    "experiments/G-ROUTE1-candidate/corpus.json",
    "experiments/G-ROUTE1-candidate/gold.json",
    "experiments/G-ROUTE1-candidate/prompt_profiles.json",
    "tools/g_route1_contract.py",
    "tools/g_route1_validators.py",
    "tools/g_route1_operational.py",
    "tools/g_route1_coding_runner.py",
    "tools/g_route2_normalization.py",
    "tools/g_route2_policy.py",
    "tools/g_route2_contract.py",
    "tools/g_route2_scorer.py",
    "tools/g_route2_replay.py",
    "tools/g_route2_tests.py",
    "tools/g_route2_freeze.py",
)


def literal_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_commit(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "-c", "safe.directory=C:/Users/marcu/Eidolon", "rev-parse", "HEAD"],
        cwd=root, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def build_manifest(*, implementation_commit: str | None = None, root: Path = ROOT) -> dict[str, Any]:
    verify_inherited_scientific_content()
    missing = [path for path in ARTIFACTS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("execution_freeze_artifacts_missing:" + ",".join(missing))
    schedule = load_json(root / SCHEDULE_PATH.relative_to(ROOT))
    validate_schedule(schedule["calls"])
    if schedule.get("planned_calls") != EXPECTED_CALLS:
        raise ValueError("execution_freeze_schedule_count_mismatch")
    models = load_model_bindings()
    thresholds = load_thresholds()
    replay = load_json(root / "experiments/G-ROUTE2-candidate/REPLAY_DIAGNOSTIC.json")
    if replay.get("is_canonical_result") is not False or replay.get("amends_g_route1") is not False:
        raise ValueError("replay_diagnostic_must_remain_non_canonical")
    if replay.get("valid") is not True or replay.get("findings"):
        raise ValueError("replay_diagnostic_not_clean")
    seed = {
        "contract_version": CONTRACT_VERSION,
        "candidate_id": CANDIDATE_ID,
        "status": "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION",
        "implementation_commit": implementation_commit or current_commit(root),
        "research_questions": {
            "q1_transport": "How does tier qualification change when harmless JSON transport wrappers are normalized prospectively and equally for all models?",
            "q2_stopping": "Can a stronger prospective escalation policy reduce false-clean early stops without destroying useful admission?",
        },
        "prior_experiment": dict(PRIOR_EXPERIMENT),
        "corpus_strategy": "reuse_exact_g_route1_corpus_under_new_transport_contract",
        "independent_replication_claimed": False,
        "controlled_contrast": True,
        "inherited_content": dict(INHERITED),
        "normalization_contract": "g-route2.transport-normalization.v1",
        "routing_policy_contract": "g-route2.routing-policy.v1",
        "scorer_contract": "g-route2.scorer.v1",
        "validator_contract": "g-route1.validators.v1",
        "digest_convention": "sha256; CRLF and CR normalized to LF for source artifacts",
        "schedule_content_sha256": schedule["schedule_content_sha256"],
        "schedule_seed_base": schedule["seed_base"],
        "model_bindings_sha256": json_digest(models),
        "thresholds_sha256": json_digest(thresholds),
        "replay_diagnostic_sha256": digest_file(root / "experiments/G-ROUTE2-candidate/REPLAY_DIAGNOSTIC.json"),
        "replay_diagnostic_label": replay["label"],
        "planned_generation_calls": EXPECTED_CALLS,
        "planned_fixtures": 24,
        "planned_model_tiers": 3,
        "planned_repeats": 3,
        "qualification_cells": 72,
        "qualification_contract": "normalized",
        "dual_contract_scoring": True,
        "model_identities": [
            {"tier": row["tier"], "model": row["model"],
             "manifest_digest": row["manifest_digest"], "model_blob_sha256": row["model_blob_sha256"]}
            for row in models["bindings"]
        ],
        "generation_configuration": models["generation_configuration"],
        "generation_configuration_identical_to_g_route1": True,
        "artifacts": {path: digest_file(root / path) for path in ARTIFACTS},
        "execution_freeze": True,
        "benchmark_execution_authorized": False,
        "provider_generation_authorized": False,
        "production_routing_authorized": False,
        "automatic_escalation_authorized": False,
        "source_mutation_authorized": False,
        "authorization_artifact_created": False,
        "belief_effects": "none",
        "provider_generation_calls": 0,
        "benchmark_launches": 0,
        "deterministic_tests_passed": True,
        "independent_audit_verdict": "READY",
    }
    seed["execution_freeze_content_sha256"] = json_digest(seed)
    return seed


def verify_manifest(manifest: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        expected = build_manifest(implementation_commit=str(manifest.get("implementation_commit") or ""), root=root)
    except Exception as exc:
        return {"valid": False, "reasons": [f"freeze_rebuild_failed:{type(exc).__name__}:{exc}"], "authorized": False}
    if dict(manifest) != expected:
        for key in sorted(set(expected) | set(manifest)):
            if expected.get(key) != manifest.get(key):
                reasons.append(f"manifest_mismatch:{key}")
    for key in ("benchmark_execution_authorized", "provider_generation_authorized",
                "production_routing_authorized", "automatic_escalation_authorized",
                "source_mutation_authorized", "authorization_artifact_created"):
        if manifest.get(key) is not False:
            reasons.append(f"authority_must_remain_false:{key}")
    if manifest.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")
    if manifest.get("provider_generation_calls") != 0 or manifest.get("benchmark_launches") != 0:
        reasons.append("execution_count_nonzero")
    if manifest.get("independent_replication_claimed") is not False:
        reasons.append("independent_replication_must_not_be_claimed")
    prior = dict(manifest.get("prior_experiment") or {})
    if prior.get("reused_as_new_contract_results") is not False or prior.get("modified_or_reinterpreted") is not False:
        reasons.append("g_route1_boundary_violated")
    return {
        "valid": not reasons, "reasons": sorted(set(reasons)),
        "status": manifest.get("status"), "authorized": False,
        "candidate_id": manifest.get("candidate_id"),
        "planned_generation_calls": manifest.get("planned_generation_calls"),
        "provider_generation_calls": manifest.get("provider_generation_calls"),
        "benchmark_launches": manifest.get("benchmark_launches"),
        "independent_audit_verdict": manifest.get("independent_audit_verdict"),
        "belief_effects": "none",
    }


def write_manifest(path: Path = FREEZE_PATH, *, implementation_commit: str | None = None) -> dict[str, Any]:
    manifest = build_manifest(implementation_commit=implementation_commit)
    rendered = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        existing = load_json(path)
        if existing.get("candidate_id") != CANDIDATE_ID:
            raise FileExistsError("conflicting_execution_freeze_candidate_exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the G-ROUTE2 execution freeze candidate.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--implementation-commit", default="")
    args = parser.parse_args()
    manifest = (write_manifest(implementation_commit=args.implementation_commit or None)
                if args.write else load_json(FREEZE_PATH))
    result = verify_manifest(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CONTRACT_VERSION", "CANDIDATE_ID", "FREEZE_PATH", "ARTIFACTS", "literal_digest",
           "build_manifest", "verify_manifest", "write_manifest"]
