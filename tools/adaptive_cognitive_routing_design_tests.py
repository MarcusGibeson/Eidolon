from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "qualifications" / "adaptive_cognitive_routing_benchmark_design.json"
DOC_PATH = ROOT / "docs" / "ADAPTIVE_COGNITIVE_ROUTING_BENCHMARK_DESIGN.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    doc = DOC_PATH.read_text(encoding="utf-8")

    require(design["design_id"] == "G-ROUTE1-CANDIDATE", "wrong design identity")
    require(design["status"] == "fixture_validator_frozen_not_execution_frozen", "fixture freeze status drifted")
    require(design["next_phase_status"] == "ready_for_runner_construction", "design is not ready for runner construction")
    require(design["source_checkpoint"] == "8a2c15d35cb1ff36a97e6c91c89920d4529f07f9", "wrong source checkpoint")
    require(design["design_predecessor_commit"] == "d6fde928071c1df31e264576b256111f9921186a", "wrong design predecessor")

    candidates = {row["model"]: row for row in design["installed_candidates"]}
    require(set(candidates) == {"qwen2.5:7b", "qwen3:14b", "qwen3.8:27b"}, "three-tier candidate inventory drifted")
    require(all(row["quantization"] == "Q4_K_M" for row in candidates.values()), "quantization inventory changed")
    require(all(row["execution_freeze_identity"] is False for row in candidates.values()), "short IDs must not become freeze identity")
    require(candidates["qwen3:14b"]["tier"] == "mid", "mid-tier candidate is not bound")
    require(candidates["qwen3:14b"]["parameters"] == "14.8B", "mid-tier parameter identity changed")
    require(candidates["qwen3:14b"]["declared_context"] >= 8192, "mid-tier context cannot support benchmark envelope")
    require(len(candidates["qwen3:14b"]["local_manifest_digest"]) == 64, "mid-tier manifest digest missing")
    require(len(candidates["qwen3:14b"]["model_blob_sha256"]) == 64, "mid-tier model blob digest missing")

    tiers = design["model_tiers"]
    require([row["id"] for row in tiers] == ["small", "mid", "large"], "model tier order must be 7B to 14B to 27B")
    require([row["model"] for row in tiers] == ["qwen2.5:7b", "qwen3:14b", "qwen3.8:27b"], "tier/model binding drifted")

    tasks = {row["id"]: row for row in design["task_taxonomy"]}
    expected_tasks = {
        "deterministic_only",
        "ordinary_conversation",
        "structured_extraction",
        "grounded_research_synthesis",
        "hierarchical_semantic_synthesis",
        "coding_generation_repair",
        "reflective_planning",
    }
    require(set(tasks) == expected_tasks, "task taxonomy incomplete")
    require(tasks["deterministic_only"]["provider_required"] is False, "deterministic work must avoid model calls")
    require(all(tasks[name]["provider_required"] is True for name in expected_tasks - {"deterministic_only"}), "model-backed task mislabeled")

    risks = {row["id"] for row in design["risk_taxonomy"]}
    require(risks == {"R0", "R1", "R2", "R3", "R4"}, "risk taxonomy incomplete")
    require("Task class describes the cognitive contract. Consequence risk is classified independently." in doc, "task/risk separation undocumented")

    plan = design["benchmark_plan"]
    calculated_calls = sum(
        row["fixture_count"] * row["repeats"] * len(candidates)
        for row in tasks.values()
        if row["provider_required"]
    )
    require(calculated_calls == 216 == plan["intended_generation_calls"], "three-tier benchmark denominator mismatch")
    require(plan["candidate_count"] == 3, "benchmark must compare all three tiers")
    require(plan["transport_retry_limit"] == 0, "benchmark must not hide transport retries")
    require(plan["concurrency"] == 1 and plan["one_local_model_research_job_at_a_time"] is True, "single-job constraint missing")
    require(plan["hidden_fallback_allowed"] is False, "hidden fallback must be denied")
    require(plan["same_fixture_prompt_and_config_across_candidates"] is True, "candidate comparison is not symmetric")
    require(plan["candidate_identity_exposed_to_prompt"] is False, "candidate identity would contaminate prompts")
    require(plan["one_fixture_per_task_risk_cell"] is True, "task/risk coverage is not explicit")

    matrix = design["qualification_matrix"]
    model_backed_tasks = expected_tasks - {"deterministic_only"}
    require(set(matrix["task_classes"]) == model_backed_tasks, "qualification matrix task classes incomplete")
    require(set(matrix["consequence_risks"]) == {"R1", "R2", "R3", "R4"}, "qualification matrix risk classes incomplete")
    require(matrix["model_tiers"] == ["small", "mid", "large"], "mid tier missing from qualification matrix")
    expected_cells = len(matrix["task_classes"]) * len(matrix["consequence_risks"]) * len(matrix["model_tiers"])
    require(expected_cells == matrix["required_cell_count"] == 72, "qualification matrix is not the full task/risk/tier product")
    require(matrix["complete_cartesian_evaluation_required"] is True, "qualification matrix permits missing cells")
    require(matrix["global_model_qualification_allowed"] is False, "global qualification would collapse task and risk")
    require(matrix["r4_adaptive_selection_allowed"] is False, "R4 authority boundary weakened")

    ladder = design["routing_ladder"]
    require(ladder["ordered_tiers"] == ["small", "mid", "large"], "routing ladder is not ordered")
    require(ladder["skip_qualified_mid_tier_allowed"] is False, "router may skip a qualified mid tier")
    require(ladder["outcomes"] == ["use_small", "use_mid", "use_large", "no_qualified_model"], "routing outcomes incomplete")
    require(ladder["no_qualified_model_behavior"] == "fail_closed_without_provider_call", "no-qualified-model outcome does not fail closed")
    require(ladder["maximum_runtime_escalations"] == 2, "three-tier escalation bound changed")
    decision_cases = {
        tuple(row["qualified_tiers"]): row["selected_outcome"]
        for row in ladder["required_decision_cases"]
    }
    require(decision_cases[("small", "mid", "large")] == "use_small", "all-qualified case is not cheapest-first")
    require(decision_cases[("mid", "large")] == "use_mid", "qualified mid tier is skipped")
    require(decision_cases[("large",)] == "use_large", "large-only qualification case missing")
    require(decision_cases[()] == "no_qualified_model", "no-qualified-model decision case missing")

    qualification = design["qualification_rule"]
    require(qualification["all_hard_gates_must_pass"] is True, "hard gates weakened")
    require(qualification["false_clean_failure_blocks_class_qualification_when_production_validator_misses_it"] is True, "false-clean failures not protected")
    require(qualification["self_reported_confidence_used"] is False, "self-reported confidence must not route")
    require(qualification["qualification_scope"] == "exact_task_class_consequence_risk_model_tier_cell", "qualification is not per task/risk/model")
    require(qualification["cheapest_qualified_tier_selected"] is True, "selection is not cheapest-qualified")
    require(qualification["qualified_mid_tier_cannot_be_skipped"] is True, "qualified mid tier may be skipped")

    authority = design["authority"]
    require(authority["belief_effects"] == "none", "belief boundary changed")
    require(all(value is False for key, value in authority.items() if key != "belief_effects"), "design grants authority")
    counts = design["observed_counts"]
    require(counts["provider_generation_calls"] == 0, "design work performed a provider generation")
    require(counts["benchmark_launches"] == 0, "design checkpoint falsely reports benchmark execution")
    require(counts["production_router_changes"] == 0, "design checkpoint changed production routing")
    require(counts["operator_authorized_model_installs"] == 1, "authorized mid-tier installation not recorded")

    excluded = {row["path"]: row["reason"] for row in design["excluded_artifacts"]}
    require("qualifications/g_synth1_r2_harness.py" in excluded, "known-bad harness not excluded")
    require("promotion-accounting defect" in excluded["qualifications/g_synth1_r2_harness.py"], "harness defect not named")
    require("The frozen G-SYNTH1-R2 harness is not reusable." in doc, "historical harness boundary missing")

    mapped_files = {
        path
        for surface in design["architecture_map"]
        for path in surface["source_files"]
    }
    must_map = {
        "conscious_agent/local_model.py",
        "conscious_agent/conversation_runtime.py",
        "conscious_agent/governed_public_web_research_adapter.py",
        "conscious_agent/experiment_review.py",
        "conscious_agent/isolated_coding_execution.py",
        "conscious_agent/model_backed_reflective_session.py",
        "conscious_agent/model_training/training_operator.py",
        "conscious_agent/native_conversation_validation.py",
        "tools/g_corrob1_provider.py",
    }
    require(must_map <= mapped_files, "material provider call path omitted from architecture map")
    require("no shared cognitive-routing seam" in doc, "architecture conclusion missing")
    require("7B → 14B → 27B" in doc, "three-tier ladder missing from documentation")
    require("a qualified 14B tier cannot be bypassed" in doc, "mid-tier skip boundary undocumented")
    require("G-ROUTE1 is ready for isolated runner" in doc, "next design phase misstated")
    completed = set(design["completed_prerequisites"])
    require("fresh_fixture_corpus_authored" in completed, "corpus completion not recorded")
    require("independent_corpus_and_gold_audit_clean" in completed, "gold audit completion not recorded")
    require("deterministic_fixture_validators_frozen" in completed, "validator freeze completion not recorded")

    print("adaptive cognitive routing design checks: PASS")
    print(f"task classes: {len(tasks)}; risk tiers: {len(risks)}; model tiers: {len(tiers)}; qualification cells: {expected_cells}")
    print(f"planned generation calls: {calculated_calls}")
    print("provider generation calls performed by this test: 0")


if __name__ == "__main__":
    main()
