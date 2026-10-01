from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HUMAN = HERE / "DESIGN_CANDIDATE.md"
MACHINE = HERE / "DESIGN_CANDIDATE.json"
REPORT = HERE / "DESIGN_VALIDATION_REPORT.json"


class DuplicateKeyError(ValueError):
    pass


def load_json_unique(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateKeyError(f"duplicate_key:{path}:{key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def cp_zero_upper(trials: int, alpha: float = 0.05) -> float:
    return 1.0 - alpha ** (1.0 / trials)


def cp_success_lower(successes: int, trials: int, alpha: float = 0.05) -> float:
    def upper_tail(p: float) -> float:
        return sum(
            math.comb(trials, value) * p**value * (1.0 - p) ** (trials - value)
            for value in range(successes, trials + 1)
        )

    low, high = 0.0, 1.0
    for _ in range(100):
        mid = (low + high) / 2.0
        if upper_tail(mid) < alpha:
            low = mid
        else:
            high = mid
    return high


def require(condition: bool, name: str, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    checks: list[str] = []
    contract = load_json_unique(MACHINE)
    human = HUMAN.read_text(encoding="utf-8")

    require(contract["schema_version"] == "g-extract1.design-candidate.v2", "schema_v2", checks)
    require(contract["experiment"]["status"] == "READY_FOR_G_EXTRACT1_DESIGN_REREVIEW", "status", checks)
    require(not contract["experiment"]["implemented"], "not_implemented", checks)
    require(not contract["experiment"]["blueprint_authorized"], "blueprint_not_authorized", checks)
    require(not contract["experiment"]["fixture_authoring_authorized"], "fixture_authoring_not_authorized", checks)
    require(not contract["experiment"]["execution_authorized"], "execution_not_authorized", checks)
    require(contract["experiment"]["provider_generation_calls"] == 0, "provider_calls_zero", checks)
    require(contract["experiment"]["belief_effects"] == "none", "belief_effects_none", checks)

    corpus = contract["corpus"]
    phases = contract["phases"]
    require(corpus["phase_a_scored_fixtures"] == 70, "phase_a_fixture_count", checks)
    require(corpus["phase_b_scored_fixtures"] == 70, "phase_b_fixture_count", checks)
    require(corpus["phase_a_reserves"] + corpus["phase_b_reserves"] == 28, "reserve_count", checks)
    require(corpus["total_to_author_before_model_contact"] == 168, "total_authored_count", checks)
    require(phases["A"]["scheduled_calls"] == 70 * 2 * 3 == 420, "phase_a_calls", checks)
    require(phases["B"]["maximum_scheduled_calls"] == 70 * 3 == 210, "phase_b_calls", checks)
    require(contract["efficiency"]["maximum_total_calls"] == 630, "maximum_calls", checks)
    require(abs(contract["efficiency"]["maximum_call_reduction_fraction"] - (1 - 630 / 1395)) < 1e-6,
            "call_reduction", checks)

    confidence = contract["confidence_contract"]
    require(abs(confidence["zero_failures_of_35_upper_95"] - cp_zero_upper(35)) < 5e-10,
            "cp_0_of_35", checks)
    require(abs(confidence["zero_failures_of_30_upper_95"] - cp_zero_upper(30)) < 5e-10,
            "cp_0_of_30", checks)
    require(abs(confidence["29_successes_of_30_lower_95"] - cp_success_lower(29, 30)) < 5e-10,
            "cp_29_of_30", checks)
    require(abs(confidence["27_successes_of_30_lower_95"] - cp_success_lower(27, 30)) < 5e-10,
            "cp_27_of_30", checks)
    require(not confidence["iid_population_claim_allowed"], "no_iid_population_claim", checks)

    families = contract["family_assignment_contract"]["priority_first_match"]
    require([row["family"] for row in families] == ["E7", "E5", "E4", "E1", "E2", "E3", "E6"],
            "family_precedence", checks)
    composed = contract["composed_feature_requirements"]
    require(len(composed["requirements"]) == 4, "composed_rows", checks)
    require(sum(row["minimum_distinct_fixtures"] for row in composed["requirements"]) == 8,
            "composed_fixture_total", checks)
    require(composed["fixtures_must_be_distinct_across_quota_rows"], "composed_distinctness", checks)

    ambiguity = contract["ambiguity_contract"]
    require(len(ambiguity["primary_outcome_precedence"]) == 8, "ambiguity_outcome_count", checks)
    require([row["priority"] for row in ambiguity["primary_outcome_precedence"]] == list(range(1, 9)),
            "ambiguity_precedence", checks)
    require(ambiguity["phase_a_gate"]["required_distinct_fixtures"] == 5, "ambiguity_a_fixtures", checks)
    require(ambiguity["phase_a_gate"]["required_observations"] == 10, "ambiguity_a_observations", checks)
    require(ambiguity["phase_a_gate"]["required_correct_recognition_observations"] == 10,
            "ambiguity_a_recognition", checks)
    require(ambiguity["phase_b_gate"]["required_observations"] == 5, "ambiguity_b_observations", checks)
    require(not ambiguity["malformed_refusal_truncation_evasion_receive_semantic_credit"],
            "no_evasion_credit", checks)

    exact = contract["exact_value_contract"]["semantic_rules"]
    require("5.0 and 5e0 fail" in exact["integer"], "integer_representation", checks)
    require("5.0, 5.00 and 5e0 are equivalent" in exact["number"], "number_equivalence", checks)
    require("duplicates" in exact["json_object"], "duplicate_key_rule", checks)
    require(exact["timezone"] == "out of scope", "timezone_out_of_scope", checks)

    reserve = contract["reserve_activation_contract"]
    require(reserve["reserves_per_phase_round_primary_family_slot"] == 1, "one_mapped_reserve", checks)
    require(not reserve["selection_pool_allowed"], "no_reserve_pool", checks)
    require(not reserve["post_contact_replacement_allowed"], "no_post_contact_replacement", checks)

    result = contract["result_state_machine"]
    verdicts = [row["verdict"] for row in result["first_match_precedence"]]
    require(result["exactly_one_primary_verdict"], "one_primary_verdict", checks)
    require(verdicts == ["INVALID", "BLOCKED_CONFIGURATION_MISMATCH", "ABORTED", "INCOMPLETE",
                         "NO_PHASE_A_CELL_QUALIFIED", "QUALIFICATION_METHOD_FAILED_VALIDATION",
                         "MIXED_TARGETED_REQUALIFICATION_SUPPORTED", "TARGETED_REQUALIFICATION_SUPPORTED"],
            "result_precedence", checks)

    states = contract["cell_state_machine"]
    require(states["phase_b_selector"] == "sorted exact set of A_QUALIFIED_FOR_B cell IDs",
            "machine_phase_b_selector", checks)
    require(not states["operator_selection_allowed"], "no_operator_cell_selection", checks)
    require(not states["phase_a_phase_b_pooling_allowed"], "no_phase_pooling", checks)
    require(not states["failed_cell_reentry_allowed"], "no_failed_cell_reentry", checks)

    classifications = {
        key: row["classification"] for key, row in contract["cell_gates"]["phase_a"].items()
    }
    require(classifications["family_semantic_floor"] == "enforced_redundant_pass_guardrail",
            "family_floor_classification", checks)
    require(classifications["binding_correctness"] == "enforced_redundant_pass_guardrail",
            "binding_guardrail_classification", checks)
    require(classifications["correlated_false_clean"] == "enforced_redundant_pass_guardrail",
            "correlated_guardrail_classification", checks)

    baseline = contract["baseline_binding"]
    for artifact in baseline["existing_behavior_artifacts"]:
        path = ROOT / artifact["path"]
        require(path.is_file(), f"baseline_exists:{artifact['role']}", checks)
        require(sha256(path) == artifact["sha256"], f"baseline_sha256:{artifact['role']}", checks)
        require(git_blob(path) == artifact["git_blob"], f"baseline_git_blob:{artifact['role']}", checks)
    template_sha = hashlib.sha256(
        baseline["structured_extraction_assembled_template"].encode("utf-8")
    ).hexdigest()
    require(template_sha == baseline["structured_extraction_assembled_template_sha256"],
            "assembled_template_sha256", checks)
    require(baseline["only_template_placeholder"] == "{SUBJECT}", "only_subject_placeholder", checks)
    require(baseline["semantic_scorer"]["executable_path"] is None, "scorer_not_implemented", checks)
    require(baseline["exact_value_comparator"]["executable_path"] is None, "comparator_not_implemented", checks)

    gold = contract["gold_adjudication_contract"]
    require(gold["determinacy_values"] == ["determinate", "ambiguous_nonaccept"],
            "gold_determinacy_values", checks)
    require(gold["fixtures_gold_reserves_equivalence_and_adjudication_freeze_together"],
            "gold_joint_freeze", checks)
    require(not gold["post_contact_gold_repair_allowed"], "no_post_contact_gold_repair", checks)

    history = contract["historical_binding"]
    closure = ROOT / "experiments/G-ROUTE4-candidate/closure/G_ROUTE4_CLOSURE.json"
    diagnostic = ROOT / "experiments/G-ROUTE4-candidate/closure/PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json"
    require(sha256(closure) == history["closure_sha256"], "historical_closure_unchanged", checks)
    require(sha256(diagnostic) == history["diagnostic_sha256"], "historical_diagnostic_unchanged", checks)

    required_human_tokens = [
        "g-extract1.ambiguity-scoring.v1",
        "10/10 observations",
        "g-extract1.reserve-activation.v1",
        "ef41104bde4915eba10a5ff1705383cf0b3d72e613fd7af87f72f5b06d2d5579",
        "MIXED_TARGETED_REQUALIFICATION_SUPPORTED",
        "benchmark decision statistics",
        "5.0` and `5e0` fail",
        "READY_FOR_G_EXTRACT1_DESIGN_REREVIEW",
    ]
    for token in required_human_tokens:
        require(token in human, f"human_contract_token:{token}", checks)

    allowed_names = {
        "DESIGN_CANDIDATE.md",
        "DESIGN_CANDIDATE.json",
        "DESIGN_REVISION_CHANGELOG.md",
        "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md",
        "DESIGN_VALIDATION_REPORT.json",
        "validate_design.py",
    }
    unexpected = sorted(path.name for path in HERE.iterdir() if path.name not in allowed_names)
    require(not unexpected, "no_fixture_or_runtime_artifacts", checks)

    governance = contract["governance"]
    require(governance["g_route4_remains_failed"], "g_route4_failed_preserved", checks)
    require(not governance["source_runtime_behavior_changed"], "runtime_unchanged", checks)
    require(not governance["provider_contacted"], "no_provider_contact", checks)
    require(not governance["new_experiment_started"], "no_experiment_launch", checks)
    require(governance["belief_effects"] == "none", "governance_belief_effects_none", checks)

    report = {
        "schema_version": "g-extract1.design-validation-report.v1",
        "verdict": "PASS",
        "check_count": len(checks),
        "checks": checks,
        "artifacts": {
            "DESIGN_CANDIDATE.md": sha256(HUMAN),
            "DESIGN_CANDIDATE.json": sha256(MACHINE),
            "DESIGN_REVISION_CHANGELOG.md": sha256(HERE / "DESIGN_REVISION_CHANGELOG.md"),
            "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md": sha256(
                HERE / "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md"
            ),
            "validate_design.py": sha256(Path(__file__)),
        },
        "provider_generation_calls": 0,
        "scored_fixtures_authored": 0,
        "reserve_fixtures_authored": 0,
        "belief_effects": "none",
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write_report:
        REPORT.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
