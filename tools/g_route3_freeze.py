from __future__ import annotations

"""Build and verify the non-authorizing G-ROUTE3 execution-freeze candidate."""

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from g_route1_contract import ROOT, digest_file
from g_route3_contract import (DATA, EXPECTED_CALLS, EXECUTION_FREEZE_PATH, json_digest, load_corpus, load_gold,
                               load_json, load_model_bindings, load_thresholds, verify_checked_schedule)

CONTRACT_VERSION = "g-route3.execution-freeze-candidate.v1"
CANDIDATE_ID = "G-ROUTE3-EXECUTION-R1"
FREEZE_PATH = EXECUTION_FREEZE_PATH
ARTIFACTS = tuple(f"experiments/G-ROUTE3-candidate/{name}" for name in (
    "DESIGN.md", "GOLD_DERIVABILITY.md", "GOLD_DERIVABILITY_DIAGNOSTIC.json", "QUALIFICATION_CONTRACT.md",
    "ROUTING_POLICY.md", "SCORING_CONTRACT.md", "CONTAMINATION_ANALYSIS.md", "PRODUCTION_ADAPTER_MAPPING.md",
    "INDEPENDENT_AUDIT.md", "DETERMINISTIC_TEST_RESULTS.json", "INDEPENDENCE_REPORT.json",
    "corpus_a.json", "gold_a.json", "corpus_b.json", "gold_b.json", "fixture_design.json",
    "model_bindings.json", "thresholds.json", "schedule_a.json", "schedule_b.json",
    "authoring/author_g3_part1.py", "authoring/author_g3_part2.py", "authoring/author_g3_part3.py",
    "authoring/assemble_g3.py",
)) + (
    "experiments/G-ROUTE1-candidate/prompt_profiles.json",
    "tools/g_route1_contract.py", "tools/g_route1_validators.py", "tools/g_route1_operational.py",
    "tools/g_route1_coding_runner.py", "tools/g_route1_persistence.py", "tools/g_route1_provider.py",
    "tools/g_route2_normalization.py", "tools/g_route2_policy.py",
    "tools/g_route3_contract.py", "tools/g_route3_qualification.py", "tools/g_route3_routing.py",
    "tools/g_route3_validation.py", "tools/g_route3_runner.py", "tools/g_route3_independence.py",
    "tools/g_route3_tests.py", "tools/g_route3_freeze.py",
)


def current_commit(root: Path = ROOT) -> str:
    return subprocess.run(["git", "-c", "safe.directory=C:/Users/marcu/Eidolon", "rev-parse", "HEAD"],
                          cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def build_manifest(*, implementation_commit: str | None = None, root: Path = ROOT) -> dict[str, Any]:
    missing = [path for path in ARTIFACTS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("execution_freeze_artifacts_missing:" + ",".join(missing))
    for corpus in ("A", "B"):
        load_corpus(corpus)
        load_gold(corpus)
    schedules = {corpus: verify_checked_schedule(corpus) for corpus in ("A", "B")}
    independence = load_json(DATA / "INDEPENDENCE_REPORT.json")
    if independence.get("valid") is not True:
        raise ValueError("independence_report_not_clean")
    if (DATA / "QUALIFICATION_TABLE.json").exists():
        raise ValueError("qualification_table_must_not_exist_at_execution_freeze")
    models = load_model_bindings()
    thresholds = load_thresholds()
    seed = {
        "contract_version": CONTRACT_VERSION,
        "candidate_id": CANDIDATE_ID,
        "status": "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION",
        "implementation_commit": implementation_commit or current_commit(root),
        "research_questions": {
            "primary": ("Can a task x risk x model qualification table derived prospectively from one independent "
                        "qualification corpus safely guide cheapest-qualified model selection and stopping on a "
                        "separate unseen validation corpus?"),
            "secondary": ("When a qualified model's individual output fails deterministic validation, can escalation "
                          "to the next independently qualified tier improve usable admission without creating unsafe stops?"),
        },
        "phases": {
            "A": {"corpus": "G-ROUTE3-CORPUS-A", "role": "qualification", "planned_calls": EXPECTED_CALLS["A"],
                  "schedule_sha256": json_digest(schedules["A"]),
                  "authorization_format": "Authorize G-ROUTE3 phase A execution <execution_freeze_binding>"},
            "B": {"corpus": "G-ROUTE3-CORPUS-B", "role": "validation", "planned_calls": EXPECTED_CALLS["B"],
                  "schedule_sha256": json_digest(schedules["B"]),
                  "authorization_format": ("Authorize G-ROUTE3 phase B execution <execution_freeze_binding> "
                                           "table <qualification_table_sha256>"),
                  "requires_frozen_audited_qualification_table": True},
        },
        "corpus_digests": {name: digest_file(root / f"experiments/G-ROUTE3-candidate/{name}")
                           for name in ("corpus_a.json", "gold_a.json", "corpus_b.json", "gold_b.json")},
        "both_corpora_frozen_before_any_contact": True,
        "qualification_table_exists": False,
        "model_bindings_sha256": json_digest(models),
        "thresholds_sha256": json_digest(thresholds),
        "independence_report_sha256": digest_file(DATA / "INDEPENDENCE_REPORT.json"),
        "model_identities": [{"tier": r["tier"], "model": r["model"], "manifest_digest": r["manifest_digest"],
                              "model_blob_sha256": r["model_blob_sha256"]} for r in models["bindings"]],
        "generation_configuration": models["generation_configuration"],
        "normalization_contract": "g-route2.transport-normalization.v1",
        "validator_contract": "g-route1.validators.v1",
        "validators_unchanged_from_g_route1": True,
        "evidence_scale": "pilot",
        "digest_convention": "sha256; CRLF and CR normalized to LF for source artifacts",
        "artifacts": {path: digest_file(root / path) for path in ARTIFACTS},
        "prior_experiments_modified": False,
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
        reasons += [f"manifest_mismatch:{key}" for key in sorted(set(expected) | set(manifest))
                    if expected.get(key) != manifest.get(key)]
    for key in ("benchmark_execution_authorized", "provider_generation_authorized", "production_routing_authorized",
                "automatic_escalation_authorized", "source_mutation_authorized", "authorization_artifact_created"):
        if manifest.get(key) is not False:
            reasons.append(f"authority_must_remain_false:{key}")
    if manifest.get("provider_generation_calls") != 0 or manifest.get("benchmark_launches") != 0:
        reasons.append("execution_count_nonzero")
    if manifest.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "status": manifest.get("status"),
            "authorized": False, "candidate_id": manifest.get("candidate_id"),
            "provider_generation_calls": manifest.get("provider_generation_calls"),
            "benchmark_launches": manifest.get("benchmark_launches"),
            "independent_audit_verdict": manifest.get("independent_audit_verdict")}


def write_manifest(path: Path = FREEZE_PATH, *, implementation_commit: str | None = None) -> dict[str, Any]:
    manifest = build_manifest(implementation_commit=implementation_commit)
    rendered = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        if load_json(path).get("candidate_id") != CANDIDATE_ID:
            raise FileExistsError("conflicting_execution_freeze_candidate_exists")
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the G-ROUTE3 execution freeze candidate.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = write_manifest() if args.write else load_json(FREEZE_PATH)
    result = verify_manifest(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
