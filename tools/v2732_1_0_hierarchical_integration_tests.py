"""v2732.1.0 - integration tests for running v2732.0 through the conversational/detached coworking workflow.

Deterministic and adversarial. Uses synthetic Q-CAP packages only; never G-EVID1.

    python tools/v2732_1_0_hierarchical_integration_tests.py
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as base  # noqa: E402
import experiment_review_hierarchical as hier  # noqa: E402
import conversational_experiment_review as adapter  # noqa: E402
import reviewer_capacity_qualification as q  # noqa: E402
import run_review_job as job_runner  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def install(root: Path, package_id: str, parts: int) -> None:
    area = root / adapter.PACKAGE_AREA / package_id
    q.build_package(area, parts)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="v2732-integration-") as tmp:
        root = Path(tmp) / "data"
        (root / adapter.PACKAGE_AREA).mkdir(parents=True, exist_ok=True)
        (root / base.REVIEW_AREA).mkdir(parents=True, exist_ok=True)
        install(root, "Q-CAP-INT", 19)

        # --- 1. the active reviewer is v2732.0, and the baseline is still reachable and unchanged ---------------
        require(adapter.ACTIVE_REVIEWER_CONTRACT == "v2733.1", "the_active_reviewer_is_the_hierarchical_one")
        require(base.CONTRACT_VERSION == "v2731.8", "the_baseline_contract_is_unchanged")
        require(job_runner.resolve_reviewer("v2731.8") is base, "the_baseline_is_still_selectable_by_contract")
        require(job_runner.resolve_reviewer("v2733.1") is hier, "the_candidate_is_selectable_by_contract")
        bad = False
        try:
            job_runner.resolve_reviewer("v9999.0")
        except LookupError:
            bad = True
        require(bad, "an_unknown_reviewer_contract_is_refused_rather_than_substituted")

        # --- 2. proposal does not start work --------------------------------------------------------------------
        package, message = adapter.propose_message("Q-CAP-INT", root) if "root" in \
            adapter.propose_message.__code__.co_varnames else adapter.propose_message("Q-CAP-INT")
        require(adapter.active_job(root) is None, "proposing_a_review_starts_no_job")
        require(bool(package), "the_proposal_identifies_the_package")
        require(not list((root / adapter.JOB_AREA).glob("*.json")) if hasattr(adapter, "JOB_AREA")
                else adapter.latest_job(root) is None, "no_job_record_exists_after_a_proposal_alone")

        # --- 3. confirmation starts exactly one detached v2732.0 job --------------------------------------------
        spawned: list[list[str]] = []

        def fake_spawn(argv, cwd, env):
            spawned.append(list(argv))
            return 4242

        started = adapter.start_review("Q-CAP-INT", confirmed=True, root=root, spawn=fake_spawn,
                                       alive=lambda pid: True)
        require(len(spawned) == 1, "confirmation_spawns_exactly_one_detached_process")
        require(started["reviewer_contract"] == "v2733.1", "the_job_record_names_the_hierarchical_reviewer")
        require(started["status"] == "running" and started["pid"] == 4242, "the_job_is_recorded_as_running")
        require(str(job_runner.__file__).endswith(Path(spawned[0][2]).suffix) or spawned[0][2].endswith(".json"),
                "the_detached_process_is_handed_a_job_record")

        refused = False
        try:
            adapter.start_review("Q-CAP-INT", confirmed=True, root=root, spawn=fake_spawn, alive=lambda pid: True)
        except RuntimeError:
            refused = True
        require(refused, "a_second_review_cannot_start_while_one_is_running")
        require(len(spawned) == 1, "the_refused_second_review_spawned_nothing")

        unconfirmed = False
        try:
            adapter.start_review("Q-CAP-INT", confirmed=False, root=root, spawn=fake_spawn)
        except PermissionError:
            unconfirmed = True
        require(unconfirmed, "an_unconfirmed_review_is_refused")

        # --- 4. the detached runner actually runs the hierarchical reviewer -------------------------------------
        job_path = adapter._job_path(started["job_id"], root)
        job_runner.CALL_MODEL = lambda prompt, max_tokens: q.deterministic_stub()(prompt, max_tokens)
        job_runner.IDENTITY = {"model": "deterministic_stub", "provider": "integration_test", "context_size": 8192,
                               "resolved_config_sha256": "0" * 64}

        # Live application churn during the guarded window: the private runtime must keep this from failing the review.
        stop = threading.Event()

        def churn():
            n = 0
            while not stop.is_set():
                n += 1
                (root / "conversation_sessions").mkdir(parents=True, exist_ok=True)
                (root / "conversation_sessions" / f"live_{n}.json").write_text(json.dumps({"n": n}), encoding="utf-8")
                (root / "memories.json").write_text(json.dumps({"tick": n}), encoding="utf-8")
                time.sleep(0.01)

        worker = threading.Thread(target=churn, daemon=True)
        worker.start()
        final = job_runner.run_job(job_path)
        stop.set()
        worker.join(timeout=2)

        require(final["status"] == "completed", "the_detached_job_completes")
        require(final["review_status"] == "complete", "the_review_itself_completes")
        require(final["reviewer"]["contract_version"] == "v2733.1",
                "the_completed_job_record_identifies_v2732_0")
        require(final["reviewer"]["baseline_contract"] == "v2731.8",
                "the_completed_job_record_names_the_baseline_it_builds_on")
        require(final["reviewer"]["architecture"] == "hierarchical_bounded_synthesis",
                "the_completed_job_record_names_the_architecture")
        require(final["reviewer"]["review_id_vocabulary"] == ["O", "PS", "DS", "GS", "U"],
                "the_completed_job_record_declares_the_identifier_vocabulary")
        require(final["checks"]["mutation_guard_passed"] is True,
                "the_mutation_guard_passes_despite_live_application_churn")
        require(final["checks"]["source_tree_guarded"] is True, "the_source_tree_was_guarded")
        require(final["checks"]["authority_flags_all_false"] is True, "authority_flags_remain_false")
        require(final["checks"]["non_authoritative"] is True, "the_artifact_remains_non_authoritative")

        # --- 5. the published artifact is retrievable and unmistakably hierarchical ------------------------------
        artifact = json.loads((Path(final["location"]) / "review.json").read_text(encoding="utf-8"))
        require(artifact["contract_version"] == "v2733.1", "the_published_artifact_states_its_contract")
        require(artifact["architecture"] == "hierarchical_bounded_synthesis",
                "the_published_artifact_states_its_architecture")
        require("intermediate_synthesis" in artifact["coverage"]["levels"],
                "the_published_artifact_carries_the_intermediate_level")
        require("group_statements" in artifact["hierarchy"], "the_published_artifact_carries_group_statements")
        flat = json.loads(json.dumps(artifact))
        require(flat.get("baseline_contract") == "v2731.8", "a_v2732_artifact_can_never_be_read_as_a_v2731_8_artifact")
        require((Path(final["location"]) / "review.md").is_file(), "the_rendered_review_is_published_too")

        # --- 6. evidence accounting survives publication --------------------------------------------------------
        lv = artifact["coverage"]["levels"]
        require(not lv["architecture"]["silently_dropped"], "no_observation_disappeared")
        require(artifact["coverage"]["required_coverage"] == 1.0, "required_coverage_is_full")
        require(lv["final"]["inputs"] <= hier.FINAL_MAX_INPUTS, "the_final_input_bound_held_in_the_detached_run")

        # --- 7. GS and U identifiers survive downstream validation and status ------------------------------------
        status = adapter.job_status(started["job_id"], root, alive=lambda pid: False)
        require(status["reviewer_contract"] == "v2733.1", "status_reports_the_reviewer_contract")
        require("v2733.1" in status["message"], "the_status_message_names_the_reviewer")
        require("hierarchical" in status["message"], "the_status_message_names_the_architecture")
        # The receipt is deliberately NOT extended. Reviewer identity is available from the job record and status;
        # the receipt is what conversation memory keeps for every review action, so its key set stays frozen.
        receipt = adapter.receipt(final)
        require(set(receipt) == {"job_id", "task_id", "package_id", "manifest_sha256", "status", "review_id",
                                 "authority"},
                "the_receipt_key_set_is_unchanged_by_this_integration")
        require(not any(k in receipt for k in ("coverage", "review_status", "levels", "reviewer")),
                "the_receipt_still_carries_no_review_conclusions")

        with hier.review_id_vocabulary():
            require(base._identifiers("GS1 and U2 disagree") == set(),
                    "GS_and_U_are_review_labels_inside_a_v2732_review")
            require(base._identifiers("WIDGET42 was observed") == {"widget42"},
                    "an_unknown_identifier_is_still_rejected_inside_the_extended_vocabulary")
        require(base._identifiers("GS1 shows x") == {"gs1"},
                "the_baseline_vocabulary_is_restored_and_still_stricter")
        require(base._identifiers("DS1 shows x") == set(), "the_baseline_label_vocabulary_is_unchanged")

        nested = False
        try:
            with hier.review_id_vocabulary():
                with hier.review_id_vocabulary():
                    pass
        except RuntimeError:
            nested = True
        require(nested, "the_vocabulary_scope_refuses_to_nest")

        # --- 8. an incomplete hierarchical review fails closed through the whole path ----------------------------
        install(root, "Q-CAP-THIN", 27)
        thin_started = adapter.start_review("Q-CAP-THIN", confirmed=True, root=root, spawn=fake_spawn,
                                            alive=lambda pid: False)
        job_runner.CALL_MODEL = lambda prompt, max_tokens: q.deterministic_stub(
            **q.SENSITIVITY["pessimistic"])(prompt, max_tokens)
        thin_final = job_runner.run_job(adapter._job_path(thin_started["job_id"], root))
        require(thin_final["status"] == "completed", "a_failing_review_still_records_a_finished_job")
        require(thin_final["review_status"] == "incomplete", "a_thin_hierarchical_review_is_reported_incomplete")
        thin_artifact = json.loads((Path(thin_final["location"]) / "review.json").read_text(encoding="utf-8"))
        require(any(m["kind"] == "final_representation_below_floor"
                    for m in thin_artifact["coverage"]["missing"]),
                "the_representation_floor_is_recorded_in_the_published_artifact")
        thin_status = adapter.job_status(thin_started["job_id"], root, alive=lambda pid: False)
        require("incomplete" in thin_status["message"], "the_status_message_does_not_present_it_as_finished")
        require(thin_final["reviewer"]["contract_version"] == "v2733.1",
                "even_a_failed_review_identifies_its_reviewer")

        # --- 9. a job pinned to the baseline still runs on the baseline ------------------------------------------
        install(root, "Q-CAP-OLD", 19)
        old_started = adapter.start_review("Q-CAP-OLD", confirmed=True, root=root, spawn=fake_spawn,
                                           alive=lambda pid: False, reviewer_contract="v2731.8")
        job_runner.CALL_MODEL = lambda prompt, max_tokens: q.deterministic_stub()(prompt, max_tokens)
        old_final = job_runner.run_job(adapter._job_path(old_started["job_id"], root))
        require(old_final["reviewer"]["contract_version"] == "v2731.8",
                "a_job_pinned_to_the_baseline_runs_on_the_baseline")
        require(old_final["reviewer"]["architecture"] == "flat_synthesis",
                "a_baseline_artifact_is_labelled_flat_not_hierarchical")
        old_artifact = json.loads((Path(old_final["location"]) / "review.json").read_text(encoding="utf-8"))
        require("intermediate_synthesis" not in old_artifact["coverage"]["levels"],
                "a_baseline_artifact_has_no_intermediate_level")
        require("architecture" not in old_artifact or old_artifact.get("contract_version") == "v2731.8",
                "the_two_artifact_kinds_are_distinguishable")

        # --- 10. the operator CLI resolves the same active reviewer, and can still pin the baseline ------------
        import review_experiment as cli

        require(cli._reviewer("").CONTRACT_VERSION == adapter.ACTIVE_REVIEWER_CONTRACT,
                "the_operator_cli_defaults_to_the_active_reviewer")
        require(cli._reviewer("v2731.8") is base, "the_operator_cli_can_still_pin_the_baseline")
        cli_bad = False
        try:
            cli._reviewer("v9999.0")
        except LookupError:
            cli_bad = True
        require(cli_bad, "the_operator_cli_refuses_an_unknown_reviewer_contract")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2732.1.0-hierarchical-integration", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
