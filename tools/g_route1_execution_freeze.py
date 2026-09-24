from __future__ import annotations

"""Build and verify the non-authorizing G-ROUTE1 execution-freeze candidate."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from g_route1_contract import DATA, ROOT, canonical_digest, digest_file
from g_route1_execution_contract import (
    EXPECTED_CALLS, SCHEDULE_PATH, json_digest, load_json, load_model_bindings,
    load_thresholds, validate_schedule, verify_fixture_freeze_current,
)


CONTRACT_VERSION = "g-route1.execution-freeze-candidate.v3"
CANDIDATE_ID = "G-ROUTE1-EXECUTION-R3"
SUPERSEDED_CANDIDATE_ID = "G-ROUTE1-EXECUTION-R2"
FREEZE_PATH = DATA / "EXECUTION_FREEZE_CANDIDATE.json"
HISTORICAL_FREEZE_PATH = DATA / "EXECUTION_FREEZE_CANDIDATE_R2.json"
HISTORICAL_LITERAL_SHA256 = "77138604fc0b63b6860b1b9c0aaa4b43b68cd7560e8a4f8dfffabfdc1d1673cf"
HISTORICAL_CONTENT_SHA256 = "feebf0e418e0cdab94463cdc0464c701e61a867deab72ee1cf93b26a33d7dfb1"
SUPERSEDED_FREEZES = (
    {"candidate_id": "G-ROUTE1-EXECUTION-R1",
     "path": "experiments/G-ROUTE1-candidate/EXECUTION_FREEZE_CANDIDATE_R1.json",
     "literal_sha256": "836ee16db8a6f92e08570473c1e553a8ff564e785feb2c80b9ceb56750770029",
     "content_sha256": "e9f674ecec069d3f296023cc568eb030a650292d2fdad96fe294fc5e20c3ee71"},
    {"candidate_id": "G-ROUTE1-EXECUTION-R2",
     "path": "experiments/G-ROUTE1-candidate/EXECUTION_FREEZE_CANDIDATE_R2.json",
     "literal_sha256": HISTORICAL_LITERAL_SHA256,
     "content_sha256": HISTORICAL_CONTENT_SHA256},
)
PRIOR_EXECUTIONS = (
    {"candidate_id": "G-ROUTE1-EXECUTION-R1", "outcome": "blocked_before_provider_contact",
     "provider_generation_calls": 0, "benchmark_launches": 0, "calls_persisted": 0,
     "reason": "scientific terminal checkpoint remained running after successful provider-free completion"},
    {"candidate_id": "G-ROUTE1-EXECUTION-R2", "outcome": "incomplete_after_provider_contact",
     "provider_generation_calls": 57, "benchmark_launches": 1, "calls_persisted": 56,
     "run_id": "groute1_20260924T022359279436Z",
     "reason": "frozen evaluator raised TypeError on non-hashable model list elements at schedule position 57"},
)
ARTIFACTS = (
    "experiments/G-ROUTE1-candidate/BLOCKED_EXECUTION_R2_EVALUATOR_DEFECT.md",
    "experiments/G-ROUTE1-candidate/EXECUTION_FREEZE_CANDIDATE_R1.json",
    "experiments/G-ROUTE1-candidate/EXECUTION_FREEZE_CANDIDATE_R2.json",
    "experiments/G-ROUTE1-candidate/FIXTURE_VALIDATOR_FREEZE.json",
    "experiments/G-ROUTE1-candidate/corpus.json",
    "experiments/G-ROUTE1-candidate/gold.json",
    "experiments/G-ROUTE1-candidate/prompt_profiles.json",
    "experiments/G-ROUTE1-candidate/model_bindings.json",
    "experiments/G-ROUTE1-candidate/thresholds.json",
    "experiments/G-ROUTE1-candidate/schedule.json",
    "experiments/G-ROUTE1-candidate/VALIDATOR_CONTRACT.md",
    "experiments/G-ROUTE1-candidate/SCORING_CONTRACT.md",
    "experiments/G-ROUTE1-candidate/ABORT_RECOVERY_CONTRACT.md",
    "experiments/G-ROUTE1-candidate/ACTIVITY_CHECKPOINT_CONTRACT.md",
    "experiments/G-ROUTE1-candidate/RUNNER_ARCHITECTURE.md",
    "experiments/G-ROUTE1-candidate/DETERMINISTIC_TEST_RESULTS.json",
    "experiments/G-ROUTE1-candidate/IMPLEMENTATION_AUDIT.md",
    "experiments/G-ROUTE1-candidate/BLOCKED_PREFLIGHT_TERMINAL_CHECKPOINT.md",
    "experiments/G-ROUTE1-candidate/TERMINAL_CHECKPOINT_REPAIR_AUDIT.md",
    "tools/g_route1_contract.py",
    "tools/g_route1_validators.py",
    "tools/g_route1_execution_contract.py",
    "tools/g_route1_operational.py",
    "tools/g_route1_coding_runner.py",
    "tools/g_route1_persistence.py",
    "tools/g_route1_activity.py",
    "tools/g_route1_provider.py",
    "tools/g_route1_scorer.py",
    "tools/g_route1_runner.py",
    "tools/g_route1_execution_tests.py",
    "tools/g_route1_execution_freeze.py",
    "tools/g_route1_execution_freeze_tests.py"
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
    for entry in SUPERSEDED_FREEZES:
        path = root / entry["path"]
        if literal_digest(path) != entry["literal_sha256"]:
            raise ValueError("historical_execution_freeze_literal_digest_mismatch:" + entry["candidate_id"])
        preserved = load_json(path)
        if preserved.get("execution_freeze_content_sha256") != entry["content_sha256"]:
            raise ValueError("historical_execution_freeze_content_digest_mismatch:" + entry["candidate_id"])
        if preserved.get("candidate_id") != entry["candidate_id"]:
            raise ValueError("historical_execution_freeze_identity_mismatch:" + entry["candidate_id"])
    verify_fixture_freeze_current()
    missing = [path for path in ARTIFACTS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("execution_freeze_artifacts_missing:" + ",".join(missing))
    schedule = load_json(root / SCHEDULE_PATH.relative_to(ROOT))
    validate_schedule(schedule["calls"])
    if schedule.get("planned_calls") != EXPECTED_CALLS:
        raise ValueError("execution_freeze_schedule_count_mismatch")
    models = load_model_bindings(root / "experiments/G-ROUTE1-candidate/model_bindings.json")
    thresholds = load_thresholds(root / "experiments/G-ROUTE1-candidate/thresholds.json")
    fixture_freeze = load_json(root / "experiments/G-ROUTE1-candidate/FIXTURE_VALIDATOR_FREEZE.json")
    artifacts = {path: digest_file(root / path) for path in ARTIFACTS}
    seed = {
        "contract_version": CONTRACT_VERSION,
        "candidate_id": CANDIDATE_ID,
        "status": "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION",
        "supersedes_candidate_id": SUPERSEDED_CANDIDATE_ID,
        "superseded_literal_sha256": HISTORICAL_LITERAL_SHA256,
        "superseded_content_sha256": HISTORICAL_CONTENT_SHA256,
        "supersession_reason": (
            "both validators raised TypeError on non-hashable model list elements instead of classifying them, "
            "halting R2 at schedule position 57"
        ),
        "superseded_freezes": [dict(entry) for entry in SUPERSEDED_FREEZES],
        "prior_executions": [dict(entry) for entry in PRIOR_EXECUTIONS],
        "cumulative_provider_generation_calls": sum(row["provider_generation_calls"] for row in PRIOR_EXECUTIONS),
        "cumulative_benchmark_launches": sum(row["benchmark_launches"] for row in PRIOR_EXECUTIONS),
        "corpus_gold_thresholds_schedule_bindings_unchanged_since_r2": True,
        "implementation_commit": implementation_commit or current_commit(root),
        "fixture_freeze_content_sha256": fixture_freeze["freeze_content_sha256"],
        "fixture_freeze_literal_sha256": digest_file(root / "experiments/G-ROUTE1-candidate/FIXTURE_VALIDATOR_FREEZE.json"),
        "schedule_content_sha256": schedule["schedule_content_sha256"],
        "model_bindings_sha256": json_digest(models),
        "thresholds_sha256": json_digest(thresholds),
        "planned_generation_calls": EXPECTED_CALLS,
        "planned_fixtures": 24,
        "planned_model_tiers": 3,
        "planned_repeats": 3,
        "qualification_cells": 72,
        "model_identities": [
            {"tier": row["tier"], "model": row["model"],
             "manifest_digest": row["manifest_digest"], "model_blob_sha256": row["model_blob_sha256"]}
            for row in models["bindings"]
        ],
        "generation_configuration": models["generation_configuration"],
        "digest_convention": "sha256; CRLF and CR normalized to LF for source artifacts",
        "artifacts": artifacts,
        "execution_freeze": True,
        "benchmark_execution_authorized": False,
        "provider_generation_authorized": False,
        "mechanical_pilot_authorized": False,
        "production_routing_authorized": False,
        "automatic_escalation_authorized": False,
        "source_mutation_authorized": False,
        "belief_effects": "none",
        "provider_generation_calls": 0,
        "benchmark_launches": 0,
        "deterministic_tests_passed": True,
        "implementation_audit_verdict": "CLEAN",
        "authorization_artifact_created": False,
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
    for key in (
        "benchmark_execution_authorized", "provider_generation_authorized", "mechanical_pilot_authorized",
        "production_routing_authorized", "automatic_escalation_authorized",
        "source_mutation_authorized", "authorization_artifact_created",
    ):
        if manifest.get(key) is not False:
            reasons.append(f"authority_must_remain_false:{key}")
    if manifest.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")
    if manifest.get("provider_generation_calls") != 0 or manifest.get("benchmark_launches") != 0:
        reasons.append("execution_count_nonzero")
    return {
        "valid": not reasons, "reasons": sorted(set(reasons)),
        "status": manifest.get("status"), "authorized": False,
        "planned_generation_calls": manifest.get("planned_generation_calls"),
        "provider_generation_calls": manifest.get("provider_generation_calls"),
        "benchmark_launches": manifest.get("benchmark_launches"),
        "belief_effects": "none",
    }


def write_manifest(path: Path = FREEZE_PATH, *, implementation_commit: str | None = None) -> dict[str, Any]:
    manifest = build_manifest(implementation_commit=implementation_commit)
    rendered = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        if path.resolve() != FREEZE_PATH.resolve():
            raise FileExistsError("conflicting_execution_freeze_candidate_exists")
        for entry in SUPERSEDED_FREEZES:
            preserved = ROOT / entry["path"]
            if not preserved.is_file() or literal_digest(preserved) != entry["literal_sha256"]:
                raise FileExistsError("historical_execution_freeze_not_preserved:" + entry["candidate_id"])
        existing = load_json(path)
        superseded = any(literal_digest(path) == entry["literal_sha256"] for entry in SUPERSEDED_FREEZES)
        same_generation = existing.get("candidate_id") == CANDIDATE_ID
        if not superseded and not same_generation:
            raise FileExistsError("unexpected_execution_freeze_candidate_exists")
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify G-ROUTE1 execution freeze candidate.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--implementation-commit", default="")
    args = parser.parse_args()
    manifest = write_manifest(implementation_commit=args.implementation_commit or None) if args.write else load_json(FREEZE_PATH)
    result = verify_manifest(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
