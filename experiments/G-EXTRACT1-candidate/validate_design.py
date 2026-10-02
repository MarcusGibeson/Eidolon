from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
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
    for _ in range(120):
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


def ids(rows: list[dict[str, Any]], key: str = "id") -> list[str]:
    return [str(row[key]) for row in rows]


def validate(contract: dict[str, Any], human: str) -> list[str]:
    checks: list[str] = []
    require(contract["schema_version"] == "g-extract1.design-candidate.v3", "schema_v3", checks)
    require(contract["experiment"]["status"] == "READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_3", "status", checks)
    for field in ("implemented", "blueprint_authorized", "fixture_authoring_authorized", "execution_authorized"):
        require(contract["experiment"][field] is False, f"authority_false:{field}", checks)
    require(contract["experiment"]["provider_generation_calls"] == 0, "provider_calls_zero", checks)
    require(contract["experiment"]["belief_effects"] == "none", "belief_effects_none", checks)

    corpus = contract["corpus"]
    phases = contract["phases"]
    require(corpus["families_per_phase_round"] == 7, "seven_families", checks)
    require(corpus["fixtures_per_family_phase_round"] == 5, "five_per_family", checks)
    require(corpus["fixtures_per_phase_round"] == 35, "thirty_five_per_round", checks)
    require(corpus["determinate_fixtures_per_phase_round"] == 30, "thirty_determinate", checks)
    require(corpus["ambiguity_fixtures_per_phase_round"] == 5, "five_ambiguity", checks)
    require(corpus["phase_a_scored_fixtures"] == corpus["phase_b_scored_fixtures"] == 70, "phase_fixture_counts", checks)
    require(corpus["phase_a_reserves"] == corpus["phase_b_reserves"] == 14, "reserve_counts", checks)
    require(corpus["total_to_author_before_model_contact"] == 168, "total_authored_count", checks)
    require(phases["A"]["scheduled_calls"] == 70 * 2 * 3 == 420, "phase_a_calls", checks)
    require(phases["B"]["maximum_scheduled_calls"] == 70 * 3 == 210, "phase_b_calls", checks)
    require(contract["efficiency"]["maximum_total_calls"] == 630, "maximum_calls", checks)
    require(abs(contract["efficiency"]["maximum_call_reduction_fraction"] - (1 - 630 / 1395)) < 1e-6, "call_reduction", checks)

    operation = contract["operation_definition_contract"]
    require(operation["contract_id"] == "g-extract1.operation-definitions.v1", "operation_contract_id", checks)
    require(operation["minimum_operation_nodes_per_fixture"] == 1, "operation_min_nodes", checks)
    require(operation["maximum_operation_nodes_per_fixture"] == 2, "operation_max_nodes", checks)
    require(operation["sentences_per_operation_node"] == 1, "one_sentence_per_operation", checks)
    require(operation["free_form_operation_instruction_allowed"] is False, "no_free_form_operations", checks)
    expected_templates = {
        "ADD": "{target} is {left} plus {right}.",
        "SUBTRACT": "{target} is {minuend} minus {subtrahend}.",
        "MULTIPLY": "{target} is {left} times {right}.",
        "DIVIDE": "{target} is {dividend} divided by {divisor}.",
        "SUM": "{target} is the sum of {operands}.",
        "COUNT": "{target} is the number of entries in {collection}.",
        "ELAPSED_MINUTES": "{target} is the elapsed minutes from {start} to {end}.",
        "CALENDAR_DAY_OFFSET": "{target} is {date} plus {days} calendar days.",
        "CLOCK_MINUTE_OFFSET": "{target} is {time} plus {minutes} minutes.",
        "GT": "{target} is true when {left} is greater than {right}.",
        "GTE": "{target} is true when {left} is greater than or equal to {right}.",
        "LT": "{target} is true when {left} is less than {right}.",
        "LTE": "{target} is true when {left} is less than or equal to {right}.",
        "EQ": "{target} is true when {left} is equal to {right}.",
        "ENTITY_FIELD_BIND": "{target} is {source_field} for the entity whose {selector_field} equals {selector_value}.",
        "EXACT_COPY": "{target} is copied exactly from {source_field}.",
    }
    catalog = {row["id"]: row for row in operation["catalog"]}
    require(set(catalog) == set(expected_templates) | {"UNIT_CONVERSION"}, "operation_catalog_ids", checks)
    for operation_id, template in expected_templates.items():
        require(catalog[operation_id]["template"] == template, f"operation_template:{operation_id}", checks)
    require(catalog["UNIT_CONVERSION"]["template_source"] == "unit_conversion_catalog.template", "unit_template_source", checks)
    conversion_templates = {
        "HOURS_TO_MINUTES": "{target} is {source} multiplied by 60, expressed in minutes.",
        "MINUTES_TO_HOURS": "{target} is {source} divided by 60, expressed in hours.",
        "KILOGRAMS_TO_GRAMS": "{target} is {source} multiplied by 1000, expressed in grams.",
        "GRAMS_TO_KILOGRAMS": "{target} is {source} divided by 1000, expressed in kilograms.",
        "DOLLARS_TO_CENTS": "{target} is {source} multiplied by 100, expressed in cents.",
        "CENTS_TO_DOLLARS": "{target} is {source} divided by 100, expressed in dollars.",
    }
    conversions = {row["id"]: row for row in operation["unit_conversion_catalog"]}
    require(set(conversions) == set(conversion_templates), "conversion_catalog_ids", checks)
    for conversion_id, template in conversion_templates.items():
        require(conversions[conversion_id]["template"] == template, f"conversion_template:{conversion_id}", checks)
    require(operation["historical_absence_schema"] == "provided|not_provided", "historical_absence_schema", checks)
    require(operation["historical_absence_sentinel"] == "not_provided", "historical_absence_sentinel", checks)
    require(operation["phase_a_b_same_operation_id_has_byte_identical_wording"], "phase_wording_identical", checks)
    prohibited = set(operation["prohibited_instruction_features"])
    require({"intermediate calculations", "edge-case reminders", "worked examples", "outcome-derived coaching"} <= prohibited, "operation_prohibitions", checks)

    families = contract["family_assignment_contract"]
    require(families["metadata_derived_not_author_selected"], "metadata_derived_families", checks)
    expected_family_order = ["E7", "E5", "E4", "E1", "E2", "E3", "E6"]
    require([row["family"] for row in families["priority_first_match"]] == expected_family_order, "family_precedence", checks)
    require([row["priority"] for row in families["priority_first_match"]] == list(range(1, 8)), "family_priorities", checks)
    require(set(families["metadata_schema"]) == {
        "unresolved_required_field_count", "unknown_sentinel_available", "entity_record_count",
        "entity_disambiguation_required", "terminal_operation", "source_operation_types",
        "output_role_type", "threshold_operator", "temporal_operation", "aggregation_operation",
        "entity_selector_role", "source_fact_sequence", "direct_copy_only",
    }, "family_metadata_fields", checks)
    require(families["no_predicate_match_is_authoring_error"], "family_no_match_error", checks)
    require(families["multiple_predicate_matches_use_first_match_only"], "family_first_match", checks)
    require("principal challenge" not in json.dumps(families).lower(), "no_subjective_family_phrase", checks)

    composed = contract["composed_feature_requirements"]
    require(ids(composed["requirements"]) == ["C1", "C2", "C3", "C4"], "composed_ids", checks)
    require(sum(row["minimum_distinct_fixtures"] for row in composed["requirements"]) == 8, "composed_total", checks)
    require(composed["fixtures_must_be_distinct_across_quota_rows"], "composed_distinct", checks)
    require(composed["minimum_distinct_composed_fixtures_per_phase_round"] == 8, "composed_minimum", checks)

    ambiguity = contract["ambiguity_contract"]
    require(ambiguity["contract_id"] == "g-extract1.ambiguity-scoring.v2", "ambiguity_contract_id", checks)
    historical = ambiguity["historical_model_facing_contract"]
    require(historical == {
        "schema_type": "provided|not_provided",
        "sentinel": "not_provided",
        "instruction": "Use 'not_provided' when the text says a value has not been provided.",
        "new_sentinel_allowed": False,
    }, "ambiguity_historical_contract", checks)
    outcomes = ambiguity["primary_outcome_precedence"]
    expected_outcomes = [
        "infrastructure_missing", "provider_truncated", "empty_output", "json_parse_failure",
        "non_object_root", "schema_invalid", "exact_valid_not_provided",
        "exact_valid_unsupported_value", "exact_valid_supported_field_error",
    ]
    require(ids(outcomes, "outcome") == expected_outcomes, "ambiguity_outcomes", checks)
    require([row["priority"] for row in outcomes] == list(range(1, 10)), "ambiguity_precedence", checks)
    require(not ambiguity["natural_language_refusal_is_separate_primary_outcome"], "no_refusal_intent_classifier", checks)
    require(not ambiguity["malformed_truncation_prose_receive_semantic_credit"], "no_malformed_semantic_credit", checks)
    require(ambiguity["phase_a_gate"]["required_distinct_fixtures"] == 5, "ambiguity_a_fixtures", checks)
    require(ambiguity["phase_a_gate"]["required_observations"] == 10, "ambiguity_a_observations", checks)
    require(ambiguity["phase_a_gate"]["required_correct_recognition_observations"] == 10, "ambiguity_a_recognition", checks)
    require(ambiguity["phase_b_gate"]["required_observations"] == 5, "ambiguity_b_observations", checks)
    require(ambiguity["phase_b_gate"]["required_correct_recognition_observations"] == 5, "ambiguity_b_recognition", checks)

    exact = contract["exact_value_contract"]
    rules = exact["semantic_rules"]
    require("5.0 and 5e0 fail" in rules["integer"], "integer_representation", checks)
    require("5.0, 5.00 and 5e0 are equivalent" in rules["number"], "number_equivalence", checks)
    require("duplicates, extras, omissions and nulls invalid" in rules["json_object"], "json_shape_rules", checks)
    require(rules["timezone"] == "out of scope", "timezone_out_of_scope", checks)
    require(exact["operational_semantic_disagreement_rule"] == "operationally accepted plus semantically invalid is false-clean", "false_clean_bridge", checks)

    contamination = contract["contamination_contract"]
    require(contamination["authored_model_facing_character_set"].startswith("printable ASCII"), "ascii_authoring", checks)
    require(contamination["boilerplate_exclusion"]["method"].startswith("construct similarity payload"), "boilerplate_by_construction", checks)
    require([row["selector"] for row in contamination["boilerplate_exclusion"]["excluded_request_spans"]] == ["request.system", "request.prompt", "request.input_marker"], "boilerplate_exact_spans", checks)
    require(contamination["tokenizer"]["engine"] == "Python re ASCII", "tokenizer_engine", checks)
    re.compile(contamination["tokenizer"]["pattern"], re.ASCII)
    require(contamination["ngram"]["size"] == 5, "ngram_size", checks)
    require(contamination["maximum_payload_token_5gram_jaccard_exclusive"] == 0.2, "jaccard_limit", checks)
    component_ids = ids(contamination["fingerprint"]["components"])
    require(component_ids == ["operation_graph", "output_schema_roles", "entity_role_graph", "boundary_relation", "temporal_pattern", "source_fact_layout"], "fingerprint_components", checks)
    for row in contamination["fingerprint"]["components"]:
        require("derivation" in row, f"fingerprint_derivation:{row['id']}", checks)
        require("structure" in row or ("type" in row and "allowed" in row), f"fingerprint_shape:{row['id']}", checks)
    required_pair_scopes = {
        "every G-ROUTE4 extraction fixture versus every G-EXTRACT1 scored or reserve fixture",
        "Phase A versus Phase A", "Phase A versus Phase B", "Phase B versus Phase B",
        "every scored fixture versus every reserve", "reserve versus reserve",
    }
    require(set(contamination["pairwise_scope"]) == required_pair_scopes, "pairwise_scope", checks)
    require(contamination["two_implementation_differential_required_before_freeze"], "two_implementation_contamination", checks)
    require(contamination["lineage_labels_alone_prove_independence"] is False, "lineage_not_independence", checks)

    reserve = contract["reserve_activation_contract"]
    require(reserve["reserves_per_phase_round_primary_family_slot"] == 1, "one_mapped_reserve", checks)
    require(not reserve["selection_pool_allowed"], "no_reserve_pool", checks)
    require(not reserve["post_contact_replacement_allowed"], "no_postcontact_reserve", checks)
    require({"composed_quota_row", "required_secondary_features", "primary_family", "phase", "round"} <= set(reserve["required_match_dimensions"]), "reserve_composed_binding", checks)
    require(reserve["replacement_must_preserve_every_composed_quota_count"], "reserve_preserves_composed", checks)

    gates_a = contract["cell_gates"]["phase_a"]
    gates_b = contract["cell_gates"]["phase_b"]
    require(gates_a["denominator_integrity"]["required_observations"] == 70, "gate_a_observations", checks)
    require(gates_a["denominator_integrity"]["required_repeat_pairs"] == 35, "gate_a_pairs", checks)
    require(gates_b["denominator_integrity"]["required_observations"] == 35, "gate_b_observations", checks)
    for label, gates in (("a", gates_a), ("b", gates_b)):
        require(gates["determinate_semantic_correctness"]["denominator_determinate_fixtures"] == 30, f"gate_{label}_semantic_denominator", checks)
        minimum_semantic = gates["determinate_semantic_correctness"].get("minimum_fixtures_with_both_repeats_correct", gates["determinate_semantic_correctness"].get("minimum_correct_fixtures"))
        require(minimum_semantic == 29, f"gate_{label}_semantic_minimum", checks)
        minimum_structural = gates["determinate_structural_validity"].get("minimum_fixtures_with_both_repeats_valid", gates["determinate_structural_validity"].get("minimum_valid_fixtures"))
        require(minimum_structural == 29, f"gate_{label}_structural_minimum", checks)
        minimum_useful = gates["useful_correct_acceptance"].get("minimum_fixtures_with_both_repeats_accepted_and_correct", gates["useful_correct_acceptance"].get("minimum_accepted_and_correct_fixtures"))
        require(minimum_useful == 27, f"gate_{label}_useful_minimum", checks)
        require(gates["false_clean"]["maximum_affected_fixtures"] == 0, f"gate_{label}_false_clean", checks)
        require(gates["family_semantic_floor"]["classification"] == "enforced_redundant_pass_guardrail", f"gate_{label}_family_guardrail", checks)
        require(gates["binding_correctness"]["classification"] == "enforced_redundant_pass_guardrail", f"gate_{label}_binding_guardrail", checks)
    require(gates_a["correlated_false_clean"]["classification"] == "enforced_redundant_pass_guardrail", "gate_a_correlated", checks)
    require(gates_b["correlated_false_clean"]["classification"] == "not_applicable_single_observation_phase", "gate_b_no_repeat_guardrail", checks)

    confidence = contract["confidence_contract"]
    require(abs(confidence["zero_failures_of_35_upper_95"] - cp_zero_upper(35)) < 5e-10, "cp_0_of_35", checks)
    require(abs(confidence["zero_failures_of_30_upper_95"] - cp_zero_upper(30)) < 5e-10, "cp_0_of_30", checks)
    require(abs(confidence["29_successes_of_30_lower_95"] - cp_success_lower(29, 30)) < 5e-10, "cp_29_of_30", checks)
    require(abs(confidence["27_successes_of_30_lower_95"] - cp_success_lower(27, 30)) < 5e-10, "cp_27_of_30", checks)
    require(not confidence["iid_population_claim_allowed"], "no_iid_population_claim", checks)

    cell = contract["cell_state_machine"]
    require(cell["phase_b_selector"] == "sorted exact set of A_QUALIFIED_FOR_B cell IDs", "phase_b_selector", checks)
    require(not cell["operator_selection_allowed"], "no_operator_selection", checks)
    require(not cell["phase_a_phase_b_pooling_allowed"], "no_pooling", checks)
    require(not cell["failed_cell_reentry_allowed"], "no_reentry", checks)
    require(len(cell["transitions"]) == 9, "cell_transition_count", checks)

    events = contract["integrity_event_contract"]
    required_invalid = {
        "PROTECTED_ARTIFACT_DIGEST_MISMATCH", "GOLD_DIGEST_MISMATCH", "SCORER_DIGEST_MISMATCH",
        "COMPARATOR_DIGEST_MISMATCH", "MODEL_IDENTITY_MISMATCH_AFTER_CONTACT",
        "PROVIDER_VERSION_MISMATCH_AFTER_CONTACT", "GENERATION_CONFIGURATION_MISMATCH",
        "SEED_MISMATCH", "SCHEDULE_POSITION_MISMATCH", "DUPLICATE_CALL",
        "SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT", "UNAUTHORIZED_RETRY",
        "UNAUTHORIZED_FALLBACK", "UNAUTHORIZED_PROMPT_MUTATION",
        "CONTAMINATION_CONTRACT_VIOLATION", "POST_CONTACT_GOLD_MUTATION",
        "POST_CONTACT_FIXTURE_MUTATION", "POST_CONTACT_THRESHOLD_MUTATION",
        "CORRUPTED_OR_UNPARSEABLE_JOURNAL", "PROVENANCE_MISMATCH",
    }
    require(set(events["invalid_events"]) == required_invalid, "invalid_event_catalog", checks)
    require(set(events["precontact_blocking_events"]).isdisjoint(required_invalid), "event_catalog_disjoint", checks)
    require(events["abort_event"] == "EXPLICIT_AUTHORIZED_OPERATOR_ABORT", "abort_event", checks)
    require(len(events["incomplete_events"]) == 4, "incomplete_event_catalog", checks)

    result = contract["result_state_machine"]
    verdicts = [row["verdict"] for row in result["first_match_precedence"]]
    require(verdicts == [
        "INVALID", "PRE_CONTACT_BLOCKED", "ABORTED", "INCOMPLETE",
        "NO_PHASE_A_CELL_QUALIFIED", "QUALIFICATION_METHOD_FAILED_VALIDATION",
        "MIXED_TARGETED_REQUALIFICATION_SUPPORTED", "TARGETED_REQUALIFICATION_SUPPORTED",
    ], "result_precedence", checks)
    require([row["precedence"] for row in result["first_match_precedence"]] == list(range(1, 9)), "result_priorities", checks)
    require(all(isinstance(row["predicate"], dict) for row in result["first_match_precedence"]), "structured_result_predicates", checks)
    expected_vectors = {
        "precontact_mismatch": "PRE_CONTACT_BLOCKED",
        "zero_a_qualifiers": "NO_PHASE_A_CELL_QUALIFIED",
        "all_b_fail": "QUALIFICATION_METHOD_FAILED_VALIDATION",
        "mixed_b": "MIXED_TARGETED_REQUALIFICATION_SUPPORTED",
        "all_b_pass": "TARGETED_REQUALIFICATION_SUPPORTED",
        "b_call_missing_with_receipt": "INCOMPLETE",
        "integrity_after_partial": "INVALID",
        "operator_abort": "ABORTED",
        "malformed_limit_every_a_cell": "NO_PHASE_A_CELL_QUALIFIED",
        "provider_failure_with_receipt": "INCOMPLETE",
        "postcontact_gold_defect": "INVALID",
        "unreceipted_omission": "INVALID",
    }
    require({row["id"]: row["expected"] for row in result["deterministic_test_vectors"]} == expected_vectors, "result_test_vectors", checks)
    require(result["post_contact_gold_defect_is"] == "INVALID", "postcontact_gold_invalid", checks)

    baseline = contract["baseline_binding"]
    require(baseline["baseline_behavior_source_commit"] == "0feb1b092bcdb1b934f01a3ce9611c59fcd8fa28", "baseline_source_commit", checks)
    require(baseline["subject_rendered_only_by"] == "g-extract1.operation-definitions.v1", "catalog_only_subject", checks)
    require(baseline["input_object_exact_keys"] == ["schema", "text"], "input_keys", checks)
    for artifact in baseline["existing_behavior_artifacts"]:
        path = ROOT / artifact["path"]
        require(path.is_file(), f"baseline_exists:{artifact['role']}", checks)
        require(sha256(path) == artifact["sha256"], f"baseline_sha256:{artifact['role']}", checks)
        require(git_blob(path) == artifact["git_blob"], f"baseline_git_blob:{artifact['role']}", checks)
    profile = load_json_unique(ROOT / "experiments/G-ROUTE1-candidate/prompt_profiles.json")
    blueprint = load_json_unique(ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json")
    extraction_template = blueprint["templates"]["structured_extraction"]
    require(profile["profiles"]["extraction.v1"] == baseline["system_text"], "system_text_matches_source", checks)
    require(extraction_template["assembled_template"] == baseline["structured_extraction_assembled_template"], "template_matches_source", checks)
    require(extraction_template["absence_sentence"] == operation["historical_absence_sentence"], "absence_sentence_matches_source", checks)
    template_digest = hashlib.sha256(baseline["structured_extraction_assembled_template"].encode("utf-8")).hexdigest()
    require(template_digest == baseline["structured_extraction_assembled_template_sha256"], "template_digest", checks)
    require(baseline["semantic_scorer"]["executable_path"] is None, "scorer_not_implemented", checks)
    require(baseline["exact_value_comparator"]["executable_path"] is None, "comparator_not_implemented", checks)

    models = contract["model_provider"]
    require(models["provider"] == "ollama" and models["provider_version"] == "0.34.3", "provider_binding", checks)
    require([row["model"] for row in models["models"]] == ["qwen2.5:7b", "qwen3:14b", "qwen3.8:27b"], "model_names", checks)
    require(all(re.fullmatch(r"[0-9a-f]{64}", row["blob_sha256"]) for row in models["models"]), "model_blob_hashes", checks)
    require(models["generation_configuration"] == {
        "num_ctx": 8192, "num_predict": 350, "temperature": 0.45, "top_p": 0.9,
        "top_k": 40, "repeat_penalty": 1.1, "think": False, "stream": False,
        "fresh_session_per_call": True, "retry_limit": 0, "repair_calls": 0, "fallback": False,
    }, "generation_configuration", checks)
    sampling = contract["sampling"]
    require(sampling["seed_formula"] == "base + zero_based_fixture_index * 10 + one_based_repeat", "seed_formula", checks)
    require(sampling["legacy_sized_prefix_observations_per_cell"] == 8 and not sampling["legacy_sized_prefix_is_gating"], "legacy_prefix_non_gating", checks)

    gold = contract["gold_adjudication_contract"]
    require(gold["fixtures_gold_reserves_equivalence_and_adjudication_freeze_together"], "gold_joint_freeze", checks)
    require(not gold["post_contact_gold_repair_allowed"], "no_postcontact_gold_repair", checks)
    governance = contract["governance"]
    for field in (
        "separate_blueprint_authorization", "separate_fixture_authoring_authorization",
        "separate_implementation_authorization", "separate_pilot_authorization",
        "separate_execution_freeze_authorization", "separate_phase_a_authorization",
        "separate_conditional_phase_b_authorization",
    ):
        require(governance[field], f"governance:{field}", checks)
    require(governance["g_route4_remains_failed"], "g_route4_failed", checks)
    require(not governance["source_runtime_behavior_changed"], "runtime_unchanged", checks)
    require(not governance["provider_contacted"], "no_provider_contact", checks)
    require(not governance["new_experiment_started"], "no_experiment_started", checks)
    require(governance["belief_effects"] == "none", "governance_belief_none", checks)

    history = contract["historical_binding"]
    closure = ROOT / "experiments/G-ROUTE4-candidate/closure/G_ROUTE4_CLOSURE.json"
    diagnostic = ROOT / "experiments/G-ROUTE4-candidate/closure/PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json"
    require(sha256(closure) == history["closure_sha256"], "historical_closure_unchanged", checks)
    require(sha256(diagnostic) == history["diagnostic_sha256"], "historical_diagnostic_unchanged", checks)

    human_literals = [
        "g-extract1.operation-definitions.v1", "g-extract1.family-assignment.v1",
        "g-extract1.contamination.v1", "g-extract1.ambiguity-scoring.v2",
        "g-extract1.integrity-events.v1", "g-extract1.result-state-machine.v2",
        "provided|not_provided", "10/10", "5/5", "54.8387%",
        "base + zero_based_fixture_index * 10 + one_based_repeat",
        "f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d",
        "not applicable in single-observation Phase B", "does not prove scientific validity",
        "READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_3",
    ]
    for literal in human_literals:
        require(literal in human, f"human_literal:{literal}", checks)
    for template in expected_templates.values():
        require(f"`{template}`" in human, f"human_operation_template:{hashlib.sha256(template.encode()).hexdigest()[:8]}", checks)
    for event in required_invalid:
        readable = event.lower().replace("_", " ")
        require(readable in human.lower() or f"`{event}`" in human, f"human_integrity_event:{event}", checks)

    validation_scope = contract["validation_claim_scope"]
    require(validation_scope["validator_claim"] == "deterministic structural and cross-representation consistency only", "validator_scope", checks)
    require(not validation_scope["scientific_validity_proven"], "no_scientific_validity_claim", checks)
    require(not validation_scope["adversarial_review_replaced"], "review_not_replaced", checks)

    allowed = {
        "DESIGN_CANDIDATE.md", "DESIGN_CANDIDATE.json", "DESIGN_REVISION_CHANGELOG.md",
        "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md", "DESIGN_VALIDATION_REPORT.json",
        "validate_design.py",
    }
    unexpected = sorted(path.name for path in HERE.iterdir() if path.name not in allowed)
    require(not unexpected, "no_fixture_or_runtime_artifacts", checks)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    contract = load_json_unique(MACHINE)
    human = HUMAN.read_text(encoding="utf-8")
    checks = validate(contract, human)
    report = {
        "schema_version": "g-extract1.design-validation-report.v2",
        "verdict": "PASS",
        "validation_scope": "deterministic structural and cross-representation consistency only",
        "scientific_validity_assessed": False,
        "adversarial_review_replaced": False,
        "check_count": len(checks),
        "checks": checks,
        "artifacts": {
            "DESIGN_CANDIDATE.md": sha256(HUMAN),
            "DESIGN_CANDIDATE.json": sha256(MACHINE),
            "DESIGN_REVISION_CHANGELOG.md": sha256(HERE / "DESIGN_REVISION_CHANGELOG.md"),
            "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md": sha256(HERE / "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md"),
            "validate_design.py": sha256(Path(__file__)),
        },
        "provider_generation_calls": 0,
        "scored_fixtures_authored": 0,
        "reserve_fixtures_authored": 0,
        "belief_effects": "none",
    }
    rendered = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if args.write_report:
        REPORT.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
