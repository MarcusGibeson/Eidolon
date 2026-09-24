from __future__ import annotations

"""Build and verify the non-executable G-ROUTE1 fixture/validator freeze."""

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from g_route1_contract import DATA, ROOT, canonical_digest, digest_file, load_corpus, load_gold


CONTRACT_VERSION = "g-route1.fixture-validator-freeze.v1"
FREEZE_PATH = DATA / "FIXTURE_VALIDATOR_FREEZE.json"
ARTIFACTS = (
    "docs/ADAPTIVE_COGNITIVE_ROUTING_BENCHMARK_DESIGN.md",
    "qualifications/adaptive_cognitive_routing_benchmark_design.json",
    "experiments/G-ROUTE1-candidate/corpus.json",
    "experiments/G-ROUTE1-candidate/gold.json",
    "experiments/G-ROUTE1-candidate/prompt_profiles.json",
    "experiments/G-ROUTE1-candidate/VALIDATOR_CONTRACT.md",
    "experiments/G-ROUTE1-candidate/INDEPENDENT_CORPUS_GOLD_AUDIT.md",
    "experiments/G-ROUTE1-candidate/CONTAMINATION_LEDGER.md",
    "experiments/G-ROUTE1-candidate/VALIDATOR_AUDIT.md",
    "tools/g_route1_contract.py",
    "tools/g_route1_validators.py",
    "tools/g_route1_fixture_tests.py",
    "tools/adaptive_cognitive_routing_design_tests.py",
    "tools/g_route1_freeze.py",
    "tools/g_route1_freeze_tests.py",
)


def build_manifest(root: Path = ROOT) -> dict[str, Any]:
    missing = [path for path in ARTIFACTS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("freeze_artifacts_missing:" + ",".join(missing))
    corpus = load_corpus(root / "experiments/G-ROUTE1-candidate/corpus.json")
    gold = load_gold(root / "experiments/G-ROUTE1-candidate/gold.json")
    artifacts = {path: digest_file(root / path) for path in ARTIFACTS}
    seed = {
        "contract_version": CONTRACT_VERSION,
        "freeze_id": "G-ROUTE1-FIXTURE-VALIDATOR-R1",
        "status": "fixture_and_validator_frozen_not_executable",
        "base_design_commit": "384388171bf06e11cb4e31df53e51ae54af9ba7d",
        "digest_convention": "sha256; CRLF and CR normalized to LF",
        "corpus_id": corpus["corpus_id"],
        "gold_id": gold["gold_id"],
        "fixture_count": len(corpus["fixtures"]),
        "task_class_count": 6,
        "risk_class_count": 4,
        "model_tiers": list(corpus["model_tiers"]),
        "repeats_per_model": corpus["repeats_per_model"],
        "planned_generation_calls": len(corpus["fixtures"]) * corpus["repeats_per_model"] * len(corpus["model_tiers"]),
        "corpus_frozen": True,
        "gold_frozen": True,
        "prompt_profiles_frozen": True,
        "validators_frozen": True,
        "independent_gold_audit_complete": True,
        "contamination_audit_complete": True,
        "deterministic_validator_audit_complete": True,
        "runner_implemented": False,
        "scorer_implemented": False,
        "schedule_frozen": False,
        "provider_configuration_frozen": False,
        "activity_adapter_implemented": False,
        "persistence_implemented": False,
        "execution_freeze": False,
        "mechanical_pilot_authorized": False,
        "benchmark_execution_authorized": False,
        "provider_generation_authorized": False,
        "production_routing_authorized": False,
        "automatic_escalation_authorized": False,
        "source_apply_authorized": False,
        "belief_effects": "none",
        "provider_generation_calls": 0,
        "benchmark_launches": 0,
        "artifacts": artifacts,
        "next_required_phase": "isolated_runner_scorer_schedule_activity_persistence_and_execution_freeze",
    }
    seed["freeze_content_sha256"] = canonical_digest(
        json.dumps(seed, sort_keys=True, separators=(",", ":"))
    )
    return seed


def verify_manifest(manifest: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        expected = build_manifest(root)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        return {"valid": False, "reasons": [str(exc)], "executable": False}
    if dict(manifest) != expected:
        for key in sorted(set(expected) | set(manifest)):
            if expected.get(key) != manifest.get(key):
                reasons.append(f"manifest_mismatch:{key}")
    denied_flags = (
        "execution_freeze",
        "mechanical_pilot_authorized",
        "benchmark_execution_authorized",
        "provider_generation_authorized",
        "production_routing_authorized",
        "automatic_escalation_authorized",
        "source_apply_authorized",
    )
    for key in denied_flags:
        if manifest.get(key) is not False:
            reasons.append(f"authority_must_remain_false:{key}")
    if manifest.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")
    if manifest.get("provider_generation_calls") != 0 or manifest.get("benchmark_launches") != 0:
        reasons.append("execution_count_nonzero")
    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "fixture_count": manifest.get("fixture_count"),
        "planned_generation_calls": manifest.get("planned_generation_calls"),
        "executable": False,
        "provider_generation_authorized": False,
        "benchmark_execution_authorized": False,
        "belief_effects": "none",
    }


def write_manifest(path: Path = FREEZE_PATH) -> dict[str, Any]:
    manifest = build_manifest()
    rendered = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        raise FileExistsError("conflicting_fixture_validator_freeze_exists")
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the non-executable G-ROUTE1 fixture freeze.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = write_manifest() if args.write else json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    result = verify_manifest(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
