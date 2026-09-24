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

CONTRACT_VERSION = "g-route3.execution-freeze-candidate.v2"
CANDIDATE_ID = "G-ROUTE3-EXECUTION-R2"
SUPERSEDED = {"candidate_id": "G-ROUTE3-EXECUTION-R1",
              "path": "experiments/G-ROUTE3-candidate/EXECUTION_FREEZE_CANDIDATE_R1.json",
              "literal_sha256": "b63f0094bbba9c3e822a359cb92b56f66f3ff244e29bbc834ce9af42a4f1653c",
              "binding_sha256": "64eed1ba1a6bb40faa0277f363f4027c09056ef909e6a31bdf71e8ad5ffe3c21",
              "reason": ("independent pre-contact review returned FINDINGS: hidden grader rules in conversation, "
                         "coding and planning, ambiguous gold, a trigger that fired on correct answers, template "
                         "reuse between corpora, a gate that could mask failure, weak table provenance, and a freeze "
                         "check that made Phase B impossible to authorize"),
              "authorized": False, "provider_generation_calls": 0}
FREEZE_PATH = EXECUTION_FREEZE_PATH
ARTIFACTS = tuple(f"experiments/G-ROUTE3-candidate/{name}" for name in (
    "DESIGN.md", "GOLD_DERIVABILITY.md", "GOLD_DERIVABILITY_DIAGNOSTIC.json", "QUALIFICATION_CONTRACT.md",
    "ROUTING_POLICY.md", "SCORING_CONTRACT.md", "CONTAMINATION_ANALYSIS.md", "PRODUCTION_ADAPTER_MAPPING.md",
    "INDEPENDENT_AUDIT.md", "DETERMINISTIC_TEST_RESULTS.json", "INDEPENDENCE_REPORT.json",
    "EXTERNAL_REVIEW_ROUND1.md", "EXECUTION_FREEZE_CANDIDATE_R1.json",
    "corpus_a.json", "gold_a.json", "corpus_b.json", "gold_b.json", "fixture_design.json",
    "model_bindings.json", "thresholds.json", "schedule_a.json", "schedule_b.json",
    "authoring/author_g3_part1.py", "authoring/author_g3_part2.py", "authoring/author_g3_part3.py",
    "authoring/author_g3_part3_round2.py", "authoring/assemble_g3.py",
)) + (
    "experiments/G-ROUTE1-candidate/prompt_profiles.json",
    "tools/g_route1_contract.py", "tools/g_route1_validators.py", "tools/g_route1_operational.py",
    "tools/g_route1_coding_runner.py", "tools/g_route1_persistence.py", "tools/g_route1_provider.py",
    "tools/g_route2_normalization.py", "tools/g_route3_operational.py", "tools/g_route3_triggers.py",
    "tools/g_route3_contract.py", "tools/g_route3_qualification.py", "tools/g_route3_routing.py",
    "tools/g_route3_validation.py", "tools/g_route3_runner.py", "tools/g_route3_independence.py",
    "tools/g_route3_tests.py", "tools/g_route3_freeze.py",
)


def literal_sha256(path: Path) -> str:
    """sha256 of the file's bytes with CRLF and CR normalized to LF, so a git checkout's line endings do not matter."""
    import hashlib
    data = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def current_commit(root: Path = ROOT) -> str:
    return subprocess.run(["git", "-c", "safe.directory=C:/Users/marcu/Eidolon", "rev-parse", "HEAD"],
                          cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def build_manifest(*, implementation_commit: str | None = None, root: Path = ROOT) -> dict[str, Any]:
    superseded = root / SUPERSEDED["path"]
    if not superseded.is_file() or literal_sha256(superseded) != SUPERSEDED["literal_sha256"]:
        raise ValueError("superseded_r1_freeze_not_preserved")
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
    models = load_model_bindings()
    thresholds = load_thresholds()
    seed = {
        "contract_version": CONTRACT_VERSION,
        "candidate_id": CANDIDATE_ID,
        "status": "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION",
        "implementation_commit": implementation_commit or current_commit(root),
        "supersedes": dict(SUPERSEDED),
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
        "operational_validator_contract": "g-route3.operational-validator.v1",
        "semantic_validators_unchanged_from_g_route1": True,
        "conversation_operational_validator_replaced": True,
        "trigger_contract": "g-route3.triggers.v1",
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
        "independent_audit_is_author_self_audit": True,
        "external_review_round1": {"verdict": "FINDINGS", "reviewed_binding": SUPERSEDED["binding_sha256"],
                                   "record": "experiments/G-ROUTE3-candidate/EXTERNAL_REVIEW_ROUND1.md"},
        "external_review_required_before_authorization": True,
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
    # The execution freeze must precede any qualification table. This is checked when the freeze is
    # written, not when it is verified, so a valid freeze stays valid once Phase A has produced a table.
    if (DATA / "QUALIFICATION_TABLE.json").exists():
        raise ValueError("qualification_table_must_not_exist_at_execution_freeze")
    manifest = build_manifest(implementation_commit=implementation_commit)
    rendered = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        replacing_preserved_r1 = literal_sha256(path) == SUPERSEDED["literal_sha256"]
        if load_json(path).get("candidate_id") != CANDIDATE_ID and not replacing_preserved_r1:
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
