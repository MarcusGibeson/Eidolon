"""v2734.3.0 - a governed recovery is visible and controllable like any other research job.

The first recovery implementation was operator-invoked only, which kept authorization where it belongs but meant a
multi-hour operation ran with no Activity row, no progress, and no Pause button. An operation you cannot see is one
you cannot supervise.

Recovery now starts as an ordinary research job: one Activity, the existing operator control, the same cooperative
pause machinery, and the same work identity across pause and resume. What it does not gain is authority - every
admissibility and compatibility decision is still settled before a job record exists, Eidolon cannot start one, and
the UI cannot invent an acknowledgement.

    python tools/v2734_3_0_recovery_activity_tests.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import activity as act  # noqa: E402
import conversational_experiment_review as adapter  # noqa: E402
import cooperative_pause as pause  # noqa: E402
import experiment_review as base  # noqa: E402
import experiment_review_hierarchical as hier  # noqa: E402
import research_control as rc  # noqa: E402
import review_recovery as rec  # noqa: E402
import reviewer_capacity_qualification as q  # noqa: E402
from review_activity import ReviewActivity  # noqa: E402

CHECKS: list[tuple[str, bool]] = []
IDENTITY = {"model": "stub", "provider": "test", "context_size": 8192, "resolved_config_sha256": "0" * 64}


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def refuses(fn, fragment: str, name: str) -> None:
    try:
        fn()
    except rec.RecoveryRefused as refused:
        require(fragment in str(refused), name)
        return
    except Exception as other:
        require(False, name + f"__raised_{type(other).__name__}")
        return
    require(False, name + "__did_not_refuse")


def failing_stub(fail_calls):
    inner = q.deterministic_stub()
    seen = {"n": 0}

    def call_model(prompt, max_tokens):
        if '"observations"' in prompt and '"open_questions"' in prompt:
            seen["n"] += 1
            if seen["n"] in fail_calls:
                text = json.dumps({"observations": [{"statement": "Unlocatable.",
                                                     "quotes": ["ZZZ absent span ZZZ"]}], "open_questions": []})
                return text, {"metrics": {"prompt_eval_count": 0, "eval_count": 9}}
        return inner(prompt, max_tokens)

    return call_model


def incomplete_source(work: Path):
    pkg = work / "pkg"
    q.build_package(pkg, 6)
    runtime = work / "rt"
    runtime.mkdir(parents=True, exist_ok=True)
    art = hier.review_experiment(pkg, call_model=failing_stub({3, 4}), runtime_root_path=runtime,
                                 identity=IDENTITY, release_model=False)
    return pkg, runtime, art


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="v2734-recact-") as tmp:
        work = Path(tmp)
        pkg, runtime, art = incomplete_source(work)
        source_id = art["review_id"]
        missing = rec.missing_required_units(art)
        require(art["status"] == "incomplete" and len(missing) == 1, "the_fixture_source_is_incomplete")

        # --- 1. authorization is settled before any job record exists ------------------------------------------
        refuses(lambda: rec.start_recovery(source_id, confirmed=False, root=runtime, identity=IDENTITY),
                "recovery_requires_explicit_confirmation", "an_unconfirmed_recovery_creates_no_job")
        require(not list((runtime / adapter.JOB_AREA).glob("job_*.json")) if (runtime / adapter.JOB_AREA).exists()
                else True, "a_refused_recovery_leaves_no_job_behind")

        # --- 2. starting one creates exactly one job and one Activity ------------------------------------------
        spawned = []
        started = rec.start_recovery(source_id, confirmed=True, root=runtime, identity=IDENTITY,
                                     operator_note="deterministic test",
                                     spawn=lambda argv, cwd, env: (spawned.append(list(argv)), os.getpid())[1])
        require(started["kind"] == rec.RECOVERY_KIND, "the_job_declares_it_is_a_recovery")
        require(started["status"] == "running" and started["pid"] == os.getpid(), "the_job_is_live_once_spawned")
        require(len(spawned) == 1 and spawned[0][2].endswith("run_recovery_job.py"),
                "exactly_one_recovery_worker_is_started")
        r = started["recovery"]
        require(r["source_review_id"] == source_id, "the_job_names_its_source_review")
        require(r["units_planned"] == missing, "the_job_names_the_units_it_may_execute")
        require(r["inherited_units"] == len(art["coverage"]["parts"]) - 1, "the_job_records_inherited_units")
        require(r["inherited_grounded_observations"] == len(art["grounded_observations"]),
                "the_job_records_inherited_observations")
        require(started["authority"] == "read_only_non_authoritative", "a_recovery_job_carries_no_extra_authority")
        require(started["chosen_by"] == "operator", "a_recovery_is_recorded_as_operator_chosen")

        # --- 3. one research job at a time ---------------------------------------------------------------------
        refuses(lambda: rec.start_recovery(source_id, confirmed=True, root=runtime, identity=IDENTITY),
                "a_research_job_is_already_running", "a_second_recovery_cannot_start_while_one_runs")

        # --- 4. the Activity shows recovery telemetry and the operator control --------------------------------
        observer = ReviewActivity(started, runtime)
        try:
            record = observer.activity.record
            require(record["type"] == "experiment_review", "a_recovery_uses_the_research_activity_type")
            require("recovery" in record["title"].lower(), "the_title_says_it_is_a_recovery")
            ident = record.get("identities") or {}
            require(ident.get("mode") == "failed_unit_recovery", "the_activity_declares_the_recovery_mode")
            require(ident.get("source_review_id") == source_id, "the_activity_names_the_source_review")
            require(ident.get("derived_review_id") == r["derived_review_id"], "the_activity_names_the_derived_review")
            require(observer.counts["inherited_grounded_observations"] == len(art["grounded_observations"]),
                    "inherited_observations_are_reported_separately")
            require(observer.counts["grounded_observations"] == 0,
                    "inherited_work_is_not_counted_as_this_runs_work")
            require(record["governance"]["belief_effects"] == "none", "belief_effects_remain_none")
            require(record["governance"]["read_only"] is True, "the_recovery_activity_is_read_only")
        finally:
            observer.stopped.set()

        row = {"activity_id": started["job_id"], "type": "experiment_review", "state": "running"}
        control = rc.affordance(row)
        require(control["action"] == "pause" and control["enabled"], "a_running_recovery_offers_pause")
        require(control["visible"], "the_recovery_control_is_visible")

        # --- 5. pause reaches the work, which a recovery names after the review it continues -------------------
        job = rc._job_record(started["job_id"], runtime)
        work_id = rc._work_id(job)
        require(work_id == rec.work_id_for(source_id), "the_control_addresses_the_recovery_work_id")
        require(work_id != started["job_id"], "the_recovery_work_id_is_not_the_job_id")
        controls = rc._controls_root(job, runtime)
        expected = (Path(job["private_runtime_root"]) / hier.REVIEW_AREA /
                    hier.work_review_id(job["manifest_sha256"], work_id))
        require(controls == expected, "the_control_root_matches_where_the_recovery_checkpoints")

        out = rc.control(started["job_id"], "pause", runtime)
        require(out["ok"] and out["status"] == "pause_requested", "an_operator_may_pause_a_recovery")
        require(pause.pending(work_id, controls) == "pause", "the_pause_signal_reaches_the_recovery_work")
        require(pause.pending(started["job_id"], controls) == "",
                "the_signal_is_not_written_under_the_job_id")

        # --- 6. resume restarts the recovery worker, not the package review worker -----------------------------
        adapter.save_job({**job, "status": "paused"}, runtime)
        again = []
        original = adapter.SPAWN
        adapter.SPAWN = lambda argv, cwd, env: (again.append(list(argv)), 77)[1]
        try:
            res = rc.control(started["job_id"], "resume", runtime)
            require(res["ok"] and res["status"] == "resume_requested", "a_paused_recovery_may_be_resumed")
            require(again and again[0][2].endswith("run_recovery_job.py"),
                    "resume_starts_the_recovery_worker_not_the_review_worker")
            require(pause.pending(work_id, controls) == "", "resuming_clears_the_pause_signal")
            live = rc._job_record(started["job_id"], runtime)
            require(live["status"] == "running", "an_accepted_resume_marks_the_recovery_live")
            require(live["recovery"]["derived_review_id"] == r["derived_review_id"],
                    "the_same_derived_review_identity_survives_pause_and_resume")
        finally:
            adapter.SPAWN = original

        # --- 7. a terminal recovery stays terminal -------------------------------------------------------------
        derived_dir = runtime / base.REVIEW_AREA / r["derived_review_id"]
        derived_dir.mkdir(parents=True, exist_ok=True)
        (derived_dir / "review.json").write_text(json.dumps({"status": "incomplete"}), encoding="utf-8")
        adapter.save_job({**rc._job_record(started["job_id"], runtime), "status": "completed"}, runtime)
        refuses(lambda: rec.start_recovery(source_id, confirmed=True, root=runtime, identity=IDENTITY),
                "derived_review_already_exists",
                "a_finished_recovery_needs_a_separately_authorized_new_operation")
        done = {"activity_id": started["job_id"], "type": "experiment_review", "state": "incomplete"}
        require(not rc.affordance(done)["enabled"], "a_terminal_recovery_offers_no_control")
        require("cannot be resumed" in rc.affordance(done)["tip"], "and_says_so_plainly")

    # --- 7b. the worker itself runs, end to end ----------------------------------------------------------------
    # The job layer was tested without ever executing its worker, and a name that did not exist in the worker's
    # setup went unnoticed until a live run: it raised before the guard, so the job sat at "running" forever with
    # no Activity and no failure. This drives the real worker.
    with tempfile.TemporaryDirectory(prefix="v2734-worker-") as tmp:
        import run_recovery_job as worker
        import run_review_job as review_runner

        work = Path(tmp)
        pkg, runtime, art = incomplete_source(work)
        source_id = art["review_id"]
        started = rec.start_recovery(source_id, confirmed=True, root=runtime, identity=IDENTITY,
                                     spawn=lambda argv, cwd, env: os.getpid())
        original_call, original_ident = review_runner.CALL_MODEL, review_runner.IDENTITY
        review_runner.CALL_MODEL, review_runner.IDENTITY = q.deterministic_stub(), IDENTITY
        try:
            done = worker.run_job(adapter._job_path(started["job_id"], runtime))
        finally:
            review_runner.CALL_MODEL, review_runner.IDENTITY = original_call, original_ident

        require(done["status"] == "completed", "the_recovery_worker_runs_to_completion")
        require(not done.get("failure"), "the_worker_records_no_failure")
        require(done["review_id"] == started["recovery"]["derived_review_id"],
                "the_worker_produced_the_planned_derived_review")
        require(done["review_status"] == "complete", "the_recovered_review_is_complete")

        published = Path(done["location"])
        require((published / "review.json").is_file(), "the_derived_artifact_is_published")
        require((published / rec.LINEAGE_NAME).is_file(), "the_lineage_record_is_published_beside_it")
        derived = json.loads((published / "review.json").read_text(encoding="utf-8"))
        require(derived["coverage"]["required_coverage"] == 1.0, "the_merged_review_reached_full_coverage")
        require(derived["mutation_guard"]["passed"] is True, "the_worker_run_passes_the_mutation_guard")
        require(derived["grounded_observations"][:len(art["grounded_observations"])] ==
                art["grounded_observations"], "the_worker_preserved_inherited_observations")

        acts = sorted((runtime / "activities").glob(f"{started['job_id']}*.json"))
        require(len(acts) == 1, "the_worker_created_exactly_one_activity")
        rec_act = json.loads(acts[0].read_text(encoding="utf-8"))
        require("recovery" in rec_act["title"].lower(), "the_activity_it_created_says_recovery")
        require((rec_act.get("identities") or {}).get("source_review_id") == source_id,
                "the_activity_it_created_names_the_source")
        require(int((rec_act.get("metrics") or {}).get("inherited_grounded_observations", 0)) ==
                len(art["grounded_observations"]), "the_activity_reports_inherited_observations")
        require(rec_act["state"] in ("complete", "incomplete"), "the_activity_reaches_a_terminal_state")

        # a setup failure must still be recorded as a failed job, not left running
        bad = adapter.save_job({**adapter._read(adapter._job_path(started["job_id"], runtime)),
                                "status": "running", "recovery": {**started["recovery"],
                                                                  "source_review_digest": "0" * 64}}, runtime)
        outcome = worker.run_job(adapter._job_path(bad["job_id"], runtime))
        require(outcome["status"] == "failed", "a_setup_failure_is_recorded_as_a_failed_job")
        require("digest" in str(outcome.get("failure")), "and_says_what_failed")

    # --- 8. the job layer adds visibility, never authority -----------------------------------------------------
    require(rec.RECOVERY_KIND not in getattr(adapter, "REVIEW_KIND", ""), "recovery_is_its_own_job_kind")
    require("review_recovery" not in (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8"),
            "the_dashboard_cannot_start_a_recovery")
    require("start_recovery" not in (ROOT / "conscious_agent" / "static" / "activity.js").read_text(encoding="utf-8"),
            "the_activity_page_cannot_start_a_recovery")
    require(rc.ACTIONS == ("pause", "resume"), "the_ui_control_still_only_pauses_and_resumes")
    require("paused" not in act.TERMINAL, "pause_remains_non_terminal")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2734.3.0-recovery-activity", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:14]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
