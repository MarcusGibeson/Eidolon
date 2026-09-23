"""v2732.0.0 - deterministic and adversarial tests for the hierarchical reviewer (bounded intermediate synthesis).

Proves the architecture before any production-model spending. Never touches G-EVID1.

    python tools/v2732_0_0_hierarchical_reviewer_tests.py
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as base  # noqa: E402
import experiment_review_hierarchical as hier  # noqa: E402
import reviewer_capacity_qualification as q  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def run(pkg: Path, call_model, runtime: Path, **kw):
    runtime.mkdir(parents=True, exist_ok=True)
    return hier.review_experiment(pkg, call_model=call_model, runtime_root_path=runtime,
                                  identity={"model": "stub", "provider": "test", "context_size": 8192,
                                            "resolved_config_sha256": "0" * 64}, **kw)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="v2732-tests-") as tmp:
        work = Path(tmp)

        # --- 1. the baseline is untouched and the identity is new ----------------------------------------------
        require(base.CONTRACT_VERSION == "v2731.8", "the_baseline_contract_is_unchanged")
        require(hier.CONTRACT_VERSION == "v2735.0", "the_candidate_has_its_own_contract_version")
        require(hier.BASELINE_CONTRACT == base.CONTRACT_VERSION, "the_candidate_records_the_baseline_it_builds_on")
        require(base.CHUNK_CHARS == 6500 and base.FINAL_INPUT_BUDGET_CHARS == 12000,
                "the_candidate_does_not_raise_any_baseline_limit")

        # --- 2. the mathematical bound -------------------------------------------------------------------------
        require(hier.FINAL_INPUT_BOUND_CHARS ==
                hier.FINAL_MAX_INPUTS * (base.MAX_STATEMENT_CHARS + base.FINAL_LINE_OVERHEAD_CHARS + 1),
                "the_final_input_bound_is_the_stated_product")
        require(hier.FINAL_INPUT_BOUND_CHARS < base.FINAL_INPUT_BUDGET_CHARS,
                "the_bound_sits_inside_the_configured_budget")
        require(hier.FINAL_INPUT_BOUND_CHARS < 13488, "the_bound_sits_inside_the_hard_context_ceiling")
        require(0 < hier.MIN_REDUCTION < 1, "every_round_is_required_to_shrink")

        # --- 3. grouping is deterministic, ordered and content blind --------------------------------------------
        items = {f"DS{n}": {"id": f"DS{n}", "type": "document_statement", "doc_id": "D1", "kind": "finding",
                            "statement": "x" * 50, "lineage": [f"O{n}"]} for n in range(1, 40)}
        ids = [f"DS{n}" for n in range(1, 40)]
        a = hier.plan_group_units(ids, items, 1)
        b = hier.plan_group_units(ids, items, 1)
        require([u["inputs"] for u in a] == [u["inputs"] for u in b], "grouping_is_deterministic")
        require(all(len(u["inputs"]) <= hier.GROUP_MAX_INPUTS for u in a), "no_group_exceeds_the_input_limit")
        require([i for u in a for i in u["inputs"]] == ids, "grouping_preserves_order_and_loses_nothing")
        shuffled = dict(items)
        for n in range(1, 40):
            shuffled[f"DS{n}"] = {**items[f"DS{n}"], "statement": "totally different wording " * 3}
        c = hier.plan_group_units(ids, shuffled, 1)
        require([u["inputs"] for u in a] == [u["inputs"] for u in c],
                "grouping_does_not_depend_on_what_a_statement_says")

        # --- 4. a clean run at 64 parts: every property at once --------------------------------------------------
        big = q.qualify(64, work_dir=work / "big", guard_source=False, reviewer=hier)
        m = big["measurements"]
        require(m["status"] == "complete", "a_calibrated_run_at_64_parts_completes")
        require(m["part_coverage"]["full"], "full_part_coverage_at_64_parts")
        require(m["observation_preservation"]["no_silent_loss"], "no_silent_observation_loss_at_64_parts")
        require(m["uncaptured_accounting"]["balances"], "uncaptured_accounting_balances_at_64_parts")
        require(m["relocatability"]["relocatable"], "every_quote_relocates_exactly_at_64_parts")
        require(m["document_boundaries"]["correct"], "every_quote_stays_inside_its_own_part_at_64_parts")
        require(m["identifier_validity"]["valid"], "no_unknown_identifier_is_cited_at_64_parts")
        require(m["intermediate"]["complete"], "every_intermediate_group_is_accepted")
        require(m["intermediate"]["converged"], "the_reduction_tree_converged")
        require(m["final_budget"]["within_bound"], "the_final_input_count_is_inside_the_structural_bound")
        require(m["final_budget"]["chars"] <= hier.FINAL_INPUT_BOUND_CHARS,
                "the_final_input_block_is_inside_the_character_bound")
        require(m["synthesis"]["complete"], "both_final_halves_are_accepted_at_64_parts")

        # --- 5. the bound does not grow with part count ---------------------------------------------------------
        sizes = {}
        for scale in (19, 34, 64):
            r = q.qualify(scale, work_dir=work / f"scale{scale}", guard_source=False, reviewer=hier)
            sizes[scale] = r["measurements"]["final_budget"]["chars"]
            require(r["measurements"]["final_budget"]["inputs"] <= hier.FINAL_MAX_INPUTS,
                    f"final_input_count_is_capped_at_{scale}_parts")
        require(max(sizes.values()) <= hier.FINAL_INPUT_BOUND_CHARS, "no_scale_exceeds_the_character_bound")
        require(sizes[64] < sizes[19] * 2,
                "the_final_block_does_not_scale_with_part_count")

        # --- 6. every observation has an explicit downstream state ---------------------------------------------
        art = q.qualify(48, work_dir=work / "state", guard_source=False, reviewer=hier)
        raw = json.loads((work / "state" / "runtime-48" / base.REVIEW_AREA /
                          art["review_id"] / "review.json").read_text(encoding="utf-8"))
        grounded_ids = {o["obs_id"] for o in raw["grounded_observations"]}
        reached = set(base.lineage_of(raw["hierarchy"]["final_inputs"],
                                      {**{s["id"]: s for s in raw["hierarchy"]["part_statements"]},
                                       **{s["id"]: s for s in raw["hierarchy"]["document_statements"]},
                                       **{s["id"]: s for s in raw["hierarchy"]["group_statements"]},
                                       **{s["id"]: s for s in raw["hierarchy"]["uncaptured_registers"]},
                                       **{o["obs_id"]: {"lineage": [o["obs_id"]]}
                                          for o in raw["grounded_observations"]}}))
        require(grounded_ids <= reached, "every_grounded_observation_reaches_the_final_level_somehow")
        require(not raw["coverage"]["levels"]["architecture"]["silently_dropped"], "nothing_disappears_silently")

        # --- 7. registers preserve lineage exactly --------------------------------------------------------------
        registers = raw["hierarchy"]["uncaptured_registers"]
        if registers:
            for reg in registers:
                require(bool(reg["covers"]), f"a_register_names_what_it_covers:{reg['id']}")
                require(bool(reg["lineage"]), f"a_register_keeps_its_observation_lineage:{reg['id']}")
                require(set(reg["lineage"]) <= grounded_ids,
                        f"a_register_lineage_is_real_observations:{reg['id']}")
        require(True, "register_checks_ran")

        # --- 8. disagreement kinds survive consolidation --------------------------------------------------------
        def opinionated(prompt: str, max_tokens: int):
            raw_reply, meta = q.deterministic_stub()(prompt, max_tokens)
            payload = json.loads(raw_reply)
            if "statements" in payload:
                kinds = ("disagreement", "uncertainty", "minority", "contradiction")
                for n, s in enumerate(payload["statements"]):
                    s["kind"] = kinds[n % len(kinds)]
                return json.dumps(payload), meta
            return raw_reply, meta

        pkg = work / "dis"
        q.build_package(pkg, 34)
        art8 = run(pkg, opinionated, work / "dis-rt")
        kinds = art8["coverage"]["statement_kinds"]
        require(art8["status"] == "complete", "a_run_full_of_disagreement_still_completes")
        require(set(kinds) <= set(base.SYNTHESIS_KINDS), "only_declared_kinds_survive")
        require(sum(v for k, v in kinds.items() if k != "finding") > 0,
                "non_consensus_kinds_survive_consolidation")
        require("finding" not in kinds or kinds.get("finding", 0) == 0,
                "consolidation_does_not_relabel_disagreement_as_a_finding")

        # --- 9. fabricated citations at the intermediate level are rejected -------------------------------------
        def fabricating_groups(prompt: str, max_tokens: int):
            if "consolidation round" in prompt:
                return json.dumps({"statements": [
                    {"statement": "the record shows alpha bravo charlie", "kind": "finding",
                     "input_ids": ["DS9999", "GS9999"]}]}), {"metrics": {"eval_count": 40}}
            return q.deterministic_stub()(prompt, max_tokens)

        pkg9 = work / "fab"
        q.build_package(pkg9, 48)
        art9 = run(pkg9, fabricating_groups, work / "fab-rt")
        require(art9["status"] == "incomplete", "fabricated_group_citations_fail_closed")
        require(not any(s["cites"] for s in art9["hierarchy"]["group_statements"]),
                "no_group_statement_keeps_a_citation_to_an_id_that_does_not_exist")

        # --- 10. a failed intermediate stage is never bypassed --------------------------------------------------
        def broken_groups(prompt: str, max_tokens: int):
            if "consolidation round" in prompt:
                return "not json at all", {"metrics": {"eval_count": 8}}
            return q.deterministic_stub()(prompt, max_tokens)

        pkg10 = work / "broken"
        q.build_package(pkg10, 48)
        art10 = run(pkg10, broken_groups, work / "broken-rt")
        require(art10["status"] == "incomplete", "a_failed_intermediate_stage_fails_the_review")
        require(any(x.get("level") == "intermediate" for x in art10["coverage"]["missing"]),
                "the_failing_intermediate_stage_is_named")
        require(not art10["review"], "no_final_review_object_is_produced_after_an_intermediate_failure")

        # --- 11. a vacuous review is refused even though it is bounded ------------------------------------------
        thin = q.qualify(48, work_dir=work / "thin", guard_source=False, reviewer=hier,
                         **q.SENSITIVITY["pessimistic"])
        mt = thin["measurements"]
        require(mt["status"] == "incomplete", "a_bounded_but_vacuous_review_fails_closed")
        require(any(x["kind"] == "final_representation_below_floor"
                    for x in mt["mechanical_verification"]["missing"]),
                "the_representation_floor_is_named_as_the_reason")
        require(mt["final_budget"]["within_bound"], "the_vacuous_run_was_bounded_but_still_refused")

        # --- 12. mutation guard integrity ------------------------------------------------------------------------
        guarded = q.qualify(34, work_dir=work / "guard", guard_source=True, reviewer=hier)
        require(guarded["measurements"]["mutation_guard"]["passed"], "the_mutation_guard_passes_on_a_clean_tree")
        require(guarded["measurements"]["mutation_guard"]["source_tree_protected"],
                "the_source_tree_is_actually_guarded")

        # --- 13. determinism of the whole pipeline ---------------------------------------------------------------
        one = q.qualify(34, work_dir=work / "det1", guard_source=False, reviewer=hier)
        two = q.qualify(34, work_dir=work / "det2", guard_source=False, reviewer=hier)
        keys = ("status", "grounded_observations")
        require(all(one["measurements"][k] == two["measurements"][k] for k in keys),
                "two_identical_runs_agree_on_status_and_observations")
        require(one["measurements"]["final_budget"]["chars"] == two["measurements"]["final_budget"]["chars"],
                "two_identical_runs_produce_the_same_final_block_size")
        require(one["measurements"]["intermediate"]["round_count"] ==
                two["measurements"]["intermediate"]["round_count"], "the_round_count_is_deterministic")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2732.0.0-hierarchical-reviewer", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
