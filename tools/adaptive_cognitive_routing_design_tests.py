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
    require(design["status"] == "design_only_not_frozen", "design must not claim an execution freeze")
    require(design["source_checkpoint"] == "8a2c15d35cb1ff36a97e6c91c89920d4529f07f9", "wrong source checkpoint")

    candidates = {row["model"]: row for row in design["installed_candidates"]}
    require(set(candidates) == {"qwen2.5:7b", "qwen3.8:27b"}, "candidate inventory drifted")
    require(all(row["quantization"] == "Q4_K_M" for row in candidates.values()), "quantization inventory changed")
    require(all(row["execution_freeze_identity"] is False for row in candidates.values()), "short IDs must not become freeze identity")

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
    require(calculated_calls == 144 == plan["intended_generation_calls"], "benchmark denominator mismatch")
    require(plan["transport_retry_limit"] == 0, "benchmark must not hide transport retries")
    require(plan["concurrency"] == 1 and plan["one_local_model_research_job_at_a_time"] is True, "single-job constraint missing")
    require(plan["hidden_fallback_allowed"] is False, "hidden fallback must be denied")
    require(plan["same_fixture_prompt_and_config_across_candidates"] is True, "candidate comparison is not symmetric")
    require(plan["candidate_identity_exposed_to_prompt"] is False, "candidate identity would contaminate prompts")

    qualification = design["qualification_rule"]
    require(qualification["all_hard_gates_must_pass"] is True, "hard gates weakened")
    require(qualification["false_clean_failure_blocks_class_qualification_when_production_validator_misses_it"] is True, "false-clean failures not protected")
    require(qualification["self_reported_confidence_used"] is False, "self-reported confidence must not route")

    authority = design["authority"]
    require(authority["belief_effects"] == "none", "belief boundary changed")
    require(all(value is False for key, value in authority.items() if key != "belief_effects"), "design grants authority")
    counts = design["observed_counts"]
    require(all(value == 0 for value in counts.values()), "design checkpoint falsely reports execution")

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

    print("adaptive cognitive routing design checks: PASS")
    print(f"task classes: {len(tasks)}; risk tiers: {len(risks)}; planned generation calls: {calculated_calls}")
    print("provider generation calls performed by this test: 0")


if __name__ == "__main__":
    main()
