"""v2734.1.0 - governed recovery of the required units an incomplete review failed to observe.

G-CORROB1-R2 independent review attempt 3 reached 139 of 140 required parts in nine and three quarter hours and then
failed closed on one unit. Failing closed was correct. Discarding the other 139 units to try again was not a decision
anyone made - it was the absence of any way to continue.

Recovery executes only the failed units, into a new derived artifact, under conditions verified against what the
source review recorded. These tests pin both halves: that it continues valid work, and that it refuses everything it
should refuse. Nothing here relaxes grounding, identifier support, coverage or the mutation guard, and the source
artifact is asserted byte-identical after every operation.

    python tools/v2734_1_0_failed_unit_recovery_tests.py
"""

import copy
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
import review_recovery as rec  # noqa: E402
import reviewer_capacity_qualification as q  # noqa: E402

CHECKS: list[tuple[str, bool]] = []
IDENTITY = {"model": "stub", "provider": "test", "context_size": 8192, "resolved_config_sha256": "0" * 64}


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def refuses(fn, fragment: str, name: str) -> None:
    """The refusal must happen, and say which rule it is."""
    try:
        fn()
    except rec.RecoveryRefused as refused:
        require(fragment in str(refused), name)
        return
    except Exception as other:  # a wrong exception type is still a failure to refuse properly
        require(False, name + f"__raised_{type(other).__name__}")
        return
    require(False, name + "__did_not_refuse")


def failing_stub(fail_calls: set[int]):
    """The qualification stub, except that named observe calls answer with a quote the document does not contain.

    That is exactly how a real part fails: the reply parses, the quotes do not locate, every observation is refused,
    and the part grounds nothing. No validator is bypassed to produce the failure.
    """
    inner = q.deterministic_stub()
    seen = {"observe": 0}

    def call_model(prompt: str, max_tokens: int):
        if '"observations"' in prompt and '"open_questions"' in prompt:
            seen["observe"] += 1
            if seen["observe"] in fail_calls:
                payload = {"observations": [{"statement": "A statement whose quote is not in this document at all.",
                                             "quotes": ["ZZZ this span appears in no document under review ZZZ"]}],
                           "open_questions": []}
                text = json.dumps(payload)
                return text, {"metrics": {"prompt_eval_count": 0, "eval_count": len(text) // 3}}
        return inner(prompt, max_tokens)

    return call_model


def incomplete_review(work: Path, *, parts: int = 6, fail_calls=(3, 4)):
    """Produce a genuinely incomplete review artifact, the way a real one becomes incomplete."""
    pkg = work / "pkg"
    q.build_package(pkg, parts)
    runtime = work / "rt"
    runtime.mkdir(parents=True, exist_ok=True)
    art = hier.review_experiment(pkg, call_model=failing_stub(set(fail_calls)), runtime_root_path=runtime,
                                 identity=IDENTITY, release_model=False)
    return pkg, runtime, art


def main() -> int:
    # --- 1. a review that fails one unit is incomplete, and names it -------------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2734-rec-") as tmp:
        work = Path(tmp)
        pkg, runtime, art = incomplete_review(work)
        source_id = art["review_id"]
        require(art["status"] == "incomplete", "a_review_that_fails_a_required_unit_is_incomplete")
        missing = rec.missing_required_units(art)
        require(len(missing) == 1, "exactly_one_unit_is_missing")
        require(art["coverage"]["required_coverage"] < 1.0, "coverage_is_reported_as_short")
        require(art["coverage"]["levels"]["final"]["first_half"] == "skipped:earlier_coverage_incomplete",
                "synthesis_was_skipped_because_coverage_was_incomplete")
        source_path = rec.review_area(runtime) / source_id / "review.json"
        source_bytes = source_path.read_bytes()

        # --- 2. the plan names exactly the failed unit and nothing else ----------------------------------------
        p = rec.plan(source_id, root=runtime, package_dir=pkg, identity=IDENTITY)
        require(p["units_to_execute"] == missing, "the_plan_targets_exactly_the_missing_unit")
        require(p["unit_count"] == 1, "the_plan_executes_one_unit")
        require(p["preserved_units"] == len(art["coverage"]["parts"]) - 1, "every_other_unit_is_preserved")
        require(p["preserved_observations"] == len(art["grounded_observations"]),
                "every_grounded_observation_is_preserved")
        require(p["derived_review_id"] != source_id, "recovery_targets_a_new_review_id")
        require(p["expected_provider_calls"]["maximum"] == hier.OBSERVE_GROUNDING_ATTEMPTS,
                "the_provider_call_scope_is_bounded_before_anything_runs")
        require(p["compatibility"]["verdict"] == "identical", "an_unchanged_environment_is_identical")
        require(set(p["compatibility"]["verified"]) == set(rec.EXECUTION_BINDINGS),
                "every_execution_binding_was_actually_compared")

        # --- 3. recovery refuses without explicit confirmation -------------------------------------------------
        refuses(lambda: rec.recover(source_id, root=runtime, package_dir=pkg, identity=IDENTITY),
                "recovery_requires_explicit_confirmation", "recovery_is_not_implicit")
        require(source_path.read_bytes() == source_bytes, "a_refused_recovery_writes_nothing")

        # --- 4. recovery executes only the failed unit and completes -------------------------------------------
        out = rec.recover(source_id, root=runtime, package_dir=pkg, identity=IDENTITY, confirmed=True,
                          call_model=q.deterministic_stub())
        require(out["status"] == "complete", "recovering_the_failed_unit_completes_the_review")
        require(out["units_executed"] == missing, "only_the_failed_unit_was_executed")
        require(out["coverage"]["required_coverage"] == 1.0, "the_derived_review_reaches_full_coverage")
        derived = json.loads((rec.review_area(runtime) / out["derived_review_id"] / "review.json")
                             .read_text(encoding="utf-8"))

        # --- 5. the original is untouched ----------------------------------------------------------------------
        require(source_path.read_bytes() == source_bytes, "the_source_artifact_is_byte_identical_afterwards")
        require(derived["review_id"] != source_id, "the_derived_artifact_is_a_different_review")
        require((rec.review_area(runtime) / source_id / "review.json").is_file(), "the_source_review_still_exists")

        # --- 6. inherited observations are preserved exactly, and recovered ones are distinguishable -----------
        kept = len(art["grounded_observations"])
        require(derived["grounded_observations"][:kept] == art["grounded_observations"],
                "every_inherited_observation_is_preserved_byte_for_byte")
        require(len(derived["grounded_observations"]) > kept, "recovery_produced_new_observations")
        recovered = derived["grounded_observations"][kept:]
        require(all(o["doc_id"] == missing[0].split(":")[1] for o in recovered),
                "the_new_observations_belong_to_the_recovered_unit")
        require(len({o["obs_id"] for o in derived["grounded_observations"]}) ==
                len(derived["grounded_observations"]), "no_observation_id_was_reissued")

        # --- 7. the derived artifact declares its own lineage --------------------------------------------------
        lin = derived["provenance"]["lineage"]
        require(lin and lin["source_review_id"] == source_id, "the_artifact_names_the_review_it_came_from")
        require(lin["source_review_digest"] == base._sha256_file(source_path),
                "the_artifact_pins_the_exact_source_it_continued")
        require(lin["recovered_units"] == missing, "the_artifact_names_which_units_were_re_executed")
        require(lin["observations_above_this_index_are_recovered"] == kept,
                "the_artifact_says_where_inherited_evidence_ends")
        require(lin["compatibility"]["verdict"] == "identical", "the_artifact_records_the_compatibility_verdict")
        side = json.loads((rec.review_area(runtime) / out["derived_review_id"] / rec.LINEAGE_NAME)
                          .read_text(encoding="utf-8"))
        require(side["source_review_id"] == source_id, "a_sidecar_lineage_record_exists_too")

        # --- 8. the mutation guard and authority boundaries survive --------------------------------------------
        require(derived["mutation_guard"]["passed"] is True, "the_derived_review_passes_the_mutation_guard")
        require(derived["authority"] == art["authority"], "authority_is_unchanged")
        require(derived["non_authoritative"] is True, "the_derived_review_remains_non_authoritative")
        require(derived["provenance"]["mutation_authority"] == "none", "recovery_grants_no_mutation_authority")

        # --- 9. recovery cannot be repeated into the same derived review ---------------------------------------
        refuses(lambda: rec.recover(source_id, root=runtime, package_dir=pkg, identity=IDENTITY, confirmed=True,
                                    call_model=q.deterministic_stub()),
                "derived_review_already_exists", "recovery_does_not_silently_run_twice")

        # --- 10. a completed unit may never be re-executed ------------------------------------------------------
        done = [p2["stage"] for p2 in art["coverage"]["parts"] if p2["reviewed"]][0]
        refuses(lambda: rec.plan(source_id, root=runtime, package_dir=pkg, identity=IDENTITY, units=[done]),
                "units_already_completed", "a_successfully_observed_unit_cannot_be_redone")
        refuses(lambda: rec.plan(source_id, root=runtime, package_dir=pkg, identity=IDENTITY,
                                 units=["observe:D99:1"]),
                "units_not_missing_in_source", "a_unit_the_source_never_missed_cannot_be_recovered")

        # --- 11. compatibility refuses every execution-relevant difference -------------------------------------
        package = base.load_package(pkg)
        for field, mutate, label in (
            ("package_documents", lambda a: a["provenance"]["documents"][0].__setitem__("sha256", "f" * 64),
             "a_changed_package_document"),
            ("package_manifest_sha256", lambda a: a["provenance"].__setitem__("manifest_sha256", "f" * 64),
             "a_changed_package_manifest"),
            ("baseline_module_sha256",
             lambda a: a["provenance"]["capability"].__setitem__("baseline_module_sha256", "f" * 64),
             "a_changed_frozen_validator"),
            ("reviewer_contract",
             lambda a: a["provenance"]["capability"].__setitem__("contract_version", "v0.0.0"),
             "a_changed_reviewer_contract"),
            ("prompt_templates_sha256",
             lambda a: a["provenance"]["prompt_templates_sha256"].__setitem__("OBSERVE_PROMPT_V2", "f" * 64),
             "a_changed_observation_prompt"),
            ("limits", lambda a: a["provenance"]["limits"].__setitem__("observe_grounding_attempts", 99),
             "a_changed_limit"),
            ("model", lambda a: a["provenance"]["model"].__setitem__("resolved_config_sha256", "f" * 64),
             "a_changed_model_configuration"),
            ("review_id_vocabulary",
             lambda a: a["provenance"].__setitem__("review_id_vocabulary", ["O"]), "a_changed_id_vocabulary"),
        ):
            doctored = copy.deepcopy(art)
            mutate(doctored)
            verdict = rec.compatibility(doctored, package, IDENTITY)
            require(verdict["verdict"] == "incompatible" and field in verdict["execution_bindings_differing"],
                    f"{label}_makes_recovery_incompatible")

        # --- 12. a reviewer module change is surfaced, never silent, and must be acknowledged exactly ----------
        doctored = copy.deepcopy(art)
        doctored["provenance"]["capability"]["module_sha256"] = "a" * 64
        verdict = rec.compatibility(doctored, package, IDENTITY)
        require(verdict["verdict"] == "execution_equivalent", "a_module_only_change_is_execution_equivalent")
        require(verdict["execution_bindings_differing"] == [], "no_execution_binding_differs_in_that_case")
        require(verdict["detail"]["reviewer_module_sha256"]["source"] == "a" * 64,
                "the_difference_is_reported_with_both_digests")

    # --- 13. an execution-equivalent recovery refuses until acknowledged by exact digest -----------------------
    with tempfile.TemporaryDirectory(prefix="v2734-ack-") as tmp:
        work = Path(tmp)
        pkg, runtime, art = incomplete_review(work)
        source_id = art["review_id"]
        path = rec.review_area(runtime) / source_id / "review.json"
        art2 = json.loads(path.read_text(encoding="utf-8"))
        art2["provenance"]["capability"]["module_sha256"] = "a" * 64
        path.write_text(json.dumps(art2, indent=1, ensure_ascii=False), encoding="utf-8")
        current = base._sha256_file(Path(hier.__file__).resolve())

        refuses(lambda: rec.recover(source_id, root=runtime, package_dir=pkg, identity=IDENTITY, confirmed=True,
                                    call_model=q.deterministic_stub()),
                "reviewer_module_change_not_acknowledged", "an_unacknowledged_module_change_refuses")
        refuses(lambda: rec.recover(source_id, root=runtime, package_dir=pkg, identity=IDENTITY, confirmed=True,
                                    acknowledge_module_change="b" * 64, call_model=q.deterministic_stub()),
                "reviewer_module_change_not_acknowledged", "a_wrong_acknowledgement_refuses")
        out = rec.recover(source_id, root=runtime, package_dir=pkg, identity=IDENTITY, confirmed=True,
                          acknowledge_module_change=current, call_model=q.deterministic_stub())
        require(out["status"] == "complete", "an_acknowledged_module_change_may_proceed")
        derived = json.loads((rec.review_area(runtime) / out["derived_review_id"] / "review.json")
                             .read_text(encoding="utf-8"))
        require(derived["provenance"]["lineage"]["acknowledged_reviewer_module_change"] == current,
                "the_acknowledgement_is_recorded_in_the_artifact")

        # an execution-relevant difference is never acknowledgeable
        path2 = rec.review_area(runtime) / source_id / "review.json"
        art3 = json.loads(path2.read_text(encoding="utf-8"))
        art3["provenance"]["model"]["model"] = "some-other-model"
        path2.write_text(json.dumps(art3, indent=1, ensure_ascii=False), encoding="utf-8")
        refuses(lambda: rec.recover(source_id, root=runtime, package_dir=pkg, identity=IDENTITY, confirmed=True,
                                    acknowledge_module_change=current, call_model=q.deterministic_stub()),
                "execution_conditions_differ", "acknowledgement_cannot_override_an_execution_difference")

    # --- 14. recovery that still grounds nothing fails closed, exactly as the original did ---------------------
    with tempfile.TemporaryDirectory(prefix="v2734-closed-") as tmp:
        work = Path(tmp)
        pkg, runtime, art = incomplete_review(work)
        source_id = art["review_id"]
        calls = {"n": 0}

        def never_grounds(prompt: str, max_tokens: int):
            calls["n"] += 1
            payload = {"observations": [{"statement": "Still not grounded in this document.",
                                         "quotes": ["ZZZ absent span ZZZ"]}], "open_questions": []}
            text = json.dumps(payload)
            return text, {"metrics": {"prompt_eval_count": 0, "eval_count": 9}}

        out = rec.recover(source_id, root=runtime, package_dir=pkg, identity=IDENTITY, confirmed=True,
                          call_model=never_grounds)
        require(out["status"] == "incomplete", "a_recovery_that_grounds_nothing_stays_incomplete")
        require(out["coverage"]["required_coverage"] < 1.0, "it_does_not_claim_coverage_it_did_not_reach")
        require(calls["n"] <= hier.OBSERVE_GROUNDING_ATTEMPTS,
                "a_failed_recovery_never_enters_an_unbounded_retry_loop")
        derived = json.loads((rec.review_area(runtime) / out["derived_review_id"] / "review.json")
                             .read_text(encoding="utf-8"))
        require(derived["coverage"]["levels"]["final"]["first_half"] == "skipped:earlier_coverage_incomplete",
                "synthesis_is_still_withheld_after_a_failed_recovery")
        require(derived["grounded_observations"][:len(art["grounded_observations"])] ==
                art["grounded_observations"], "a_failed_recovery_still_preserves_inherited_evidence")

    # --- 15. a complete review is not a recovery candidate -----------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2734-done-") as tmp:
        work = Path(tmp)
        pkg = work / "pkg"
        q.build_package(pkg, 6)
        runtime = work / "rt"
        runtime.mkdir(parents=True, exist_ok=True)
        done = hier.review_experiment(pkg, call_model=q.deterministic_stub(), runtime_root_path=runtime,
                                      identity=IDENTITY, release_model=False)
        require(done["status"] == "complete", "the_control_review_completed")
        refuses(lambda: rec.plan(done["review_id"], root=runtime, package_dir=pkg, identity=IDENTITY),
                "source_review_is_already_complete", "a_complete_review_cannot_be_recovered")
        refuses(lambda: rec.plan("no_such_review", root=runtime, package_dir=pkg, identity=IDENTITY),
                "source_review_not_found", "an_unknown_review_id_is_refused_cleanly")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2734.1.0-failed-unit-recovery", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:14]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
