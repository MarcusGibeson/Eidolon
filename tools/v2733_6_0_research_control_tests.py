"""v2733.6.0 - operator play/pause over governed research work.

The backend cooperative pause path is already live-qualified. These tests cover the control surface that exposes it:
what the operator is offered in each state, that a click becomes exactly one governed request, that repeated clicks
cannot stack, that a terminal review is never offered a resume, and that the browser is never the source of truth.

A companion node suite covers the rendered control itself. Run both:

    python tools/v2733_6_0_research_control_tests.py
    node tools/v2733_6_1_research_control_ui.test.js
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import activity as act  # noqa: E402
import cooperative_pause as pause  # noqa: E402
import research_control as rc  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def activity_row(state: str, kind: str = "experiment_review", activity_id: str = "job_1") -> dict:
    return {"activity_id": activity_id, "type": kind, "state": state}


def main() -> int:
    # --- 1. what the operator is offered, per state ---------------------------------------------------------
    for state in ("running", "preparing", "blocked"):
        a = rc.affordance(activity_row(state))
        require(a["action"] == "pause" and a["enabled"] and not a["pending"],
                f"running_work_offers_an_enabled_pause:{state}")
        require(a["label"] == "Pause research", f"the_pause_label_is_correct:{state}")
        require(a["icon"] == "pause", f"the_pause_icon_is_shown:{state}")

    a = rc.affordance(activity_row("pause_requested"))
    require(a["pending"] and not a["enabled"], "pause_requested_is_pending_and_not_clickable")
    require(a["label"] == "Pausing…", "pause_requested_says_pausing")
    require(a["action"] == "pause", "the_pending_control_still_describes_the_request_in_flight")

    a = rc.affordance(activity_row("paused"))
    require(a["action"] == "resume" and a["enabled"] and not a["pending"], "paused_work_offers_resume")
    require(a["label"] == "Resume research" and a["icon"] == "play", "the_resume_label_and_icon_are_correct")

    for state in ("complete", "incomplete", "failed", "cancelled"):
        a = rc.affordance(activity_row(state))
        require(not a["action"] and not a["enabled"], f"terminal_work_offers_no_action:{state}")
        require(a["icon"] == "none", f"terminal_work_shows_no_play_icon:{state}")
        require("cannot be resumed" in a["tip"], f"terminal_work_says_plainly_it_cannot_resume:{state}")
        require(a["reason"] == f"terminal:{state}", f"the_terminal_reason_is_recorded:{state}")

    a = rc.affordance(activity_row("queued"))
    require(not a["enabled"] and a["reason"] == "not_started", "queued_work_is_not_pausable_yet")

    a = rc.affordance(activity_row("running", kind="chat"))
    require(not a["visible"], "non_research_activities_show_no_research_control")
    require(a["reason"] == "not_research_work", "the_reason_names_why_it_is_hidden")

    # --- 2. the affordance is attached to the API payload ----------------------------------------------------
    payload = rc.decorate({"activities": [activity_row("running"), activity_row("paused", activity_id="job_2")],
                           "activity": activity_row("complete", activity_id="job_3")})
    require(all("control" in row for row in payload["activities"]), "every_listed_activity_carries_its_control")
    require(payload["activity"]["control"]["action"] == "", "the_detail_activity_carries_its_control")
    require(payload["activities"][0]["control"]["action"] == "pause", "the_listed_control_matches_the_state")
    require(payload["activities"][1]["control"]["action"] == "resume", "each_row_gets_its_own_control")

    # --- 3. one click becomes exactly one governed request ---------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2733-control-") as tmp:
        root = Path(tmp)
        import conversational_experiment_review as adapter

        job_id = "job_ctl"
        manifest = "a" * 64
        (root / adapter.JOB_AREA).mkdir(parents=True, exist_ok=True)
        private = root / "research_review_runtimes" / job_id
        job = {"job_id": job_id, "task_id": "t1", "package_id": "Q-CTL", "manifest_sha256": manifest,
               "status": "running", "private_runtime_root": str(private), "runtime_root": str(root),
               "started": "2026-09-21T00:00:00Z"}
        adapter.save_job(job, root)
        controls = rc._controls_root(job, root)

        first = rc.control(job_id, "pause", root)
        require(first["ok"] and first["status"] == "pause_requested", "a_pause_click_requests_a_pause")
        require(first["expect_state"] == "pause_requested", "the_response_says_what_state_to_expect")
        require(pause.pending(job_id, controls) == "pause", "the_governed_pause_signal_is_written")
        history = json.loads(pause.control_path(job_id, controls).read_text(encoding="utf-8"))["history"]
        require(len(history) == 1, "exactly_one_governed_request_was_written")

        second = rc.control(job_id, "pause", root)
        require(second["ok"] and second["status"] == "pause_already_requested",
                "clicking_pause_again_does_not_stack_a_second_request")
        history = json.loads(pause.control_path(job_id, controls).read_text(encoding="utf-8"))["history"]
        require(len(history) == 1, "the_repeat_click_wrote_nothing_new")

        # --- 4. resume restarts the same job, once ------------------------------------------------------------
        refused = rc.control(job_id, "resume", root)
        require(not refused["ok"] and refused["status"] == "job_not_paused",
                "a_job_that_is_not_paused_cannot_be_resumed")

        spawned: list[list[str]] = []
        original_spawn = adapter.SPAWN
        adapter.SPAWN = lambda argv, cwd, env: (spawned.append(list(argv)), 4242)[1]
        try:
            adapter.save_job({**job, "status": "paused"}, root)
            resumed = rc.control(job_id, "resume", root)
            require(resumed["ok"] and resumed["status"] == "resume_requested", "a_play_click_requests_a_resume")
            require(resumed["expect_state"] == "running", "the_resume_response_says_to_expect_running")
            require(len(spawned) == 1, "resume_starts_exactly_one_process")
            require(str(adapter.JOB_RUNNER) in spawned[0][2] or spawned[0][2].endswith(".json"),
                    "resume_hands_the_runner_the_same_job_record")
            require(job_id in spawned[0][-1], "resume_names_the_same_job_id_rather_than_a_new_one")
            require(pause.pending(job_id, controls) == "", "resuming_clears_the_pause_signal")
        finally:
            adapter.SPAWN = original_spawn

        # --- 5. terminal work is refused ----------------------------------------------------------------------
        for terminal in ("completed", "failed", "cancelled"):
            adapter.save_job({**job, "status": terminal}, root)
            out = rc.control(job_id, "resume", root)
            require(not out["ok"] and out["status"] == "job_already_terminal",
                    f"a_{terminal}_job_cannot_be_resumed_from_the_control")
            out = rc.control(job_id, "pause", root)
            require(not out["ok"] and out["status"] == "job_already_terminal",
                    f"a_{terminal}_job_cannot_be_paused_from_the_control")

        # --- 6. refusals are results, not exceptions ----------------------------------------------------------
        require(rc.control("job_that_does_not_exist", "pause", root)["status"] == "job_not_found",
                "an_unknown_job_is_refused_cleanly")
        require(rc.control(job_id, "cancel", root)["status"] == "unknown_action",
                "cancel_is_not_reachable_from_a_play_pause_control")
        require(rc.control(job_id, "", root)["status"] == "unknown_action", "an_empty_action_is_refused")
        require(rc.ACTIONS == ("pause", "resume"), "the_control_offers_only_pause_and_resume")

    # --- 6b. work interrupted without a result is recoverable, and only then ---------------------------------
    with tempfile.TemporaryDirectory(prefix="v2733-recover-") as tmp:
        root = Path(tmp)
        import conversational_experiment_review as adapter

        job_id = "job_crash"
        manifest = "b" * 64
        (root / adapter.JOB_AREA).mkdir(parents=True, exist_ok=True)
        private = root / "research_review_runtimes" / job_id
        job = {"job_id": job_id, "task_id": "t1", "package_id": "Q-REC", "manifest_sha256": manifest,
               "status": "failed", "failure": "job_process_ended_without_result",
               "private_runtime_root": str(private), "runtime_root": str(root),
               "started": "2026-09-22T00:00:00Z"}
        adapter.save_job(job, root)
        controls = rc._controls_root(job, root)

        # no checkpoint yet: nothing to continue
        out = rc.resumable_checkpoint(job, root)
        require(not out["resumable"] and out["reason"] == "no_checkpoint",
                "an_interrupted_job_with_no_checkpoint_is_not_resumable")
        require(not rc.affordance(activity_row("failed"), recoverable=False)["enabled"],
                "without_a_checkpoint_the_control_stays_disabled")

        cp = pause.Checkpointer(job_id, controls, bindings={"package_id": "Q-REC"})
        cp.write(position={"level": "observe"}, completed_units=["observe:D1:1", "observe:D2:1"],
                 next_unit="", state={"review_id": "rev_rec"}, status=pause.RUNNING)
        out = rc.resumable_checkpoint(job, root)
        require(out["resumable"] and out["completed_units"] == 2,
                "an_interrupted_job_with_a_sealed_checkpoint_is_resumable")

        a = rc.affordance(activity_row("failed"), recoverable=True)
        require(a["action"] == "resume" and a["enabled"], "interrupted_work_offers_resume")
        require(a["reason"] == "interrupted_with_checkpoint", "the_reason_says_it_was_interrupted")
        require("interrupted" in a["tip"], "the_tip_says_the_work_was_interrupted_rather_than_finished")

        spawned = []
        original = adapter.SPAWN
        adapter.SPAWN = lambda argv, cwd, env: (spawned.append(list(argv)), 99)[1]
        try:
            res = rc.control(job_id, "resume", root)
            require(res["ok"] and res["status"] == "resume_requested", "an_interrupted_job_can_be_resumed")
            require(res["recovered_from_interruption"] is True, "the_response_says_it_recovered_an_interruption")
            require(res["completed_units"] == 2, "the_response_reports_what_was_already_done")
            require(len(spawned) == 1, "recovery_starts_exactly_one_process")
        finally:
            adapter.SPAWN = original

        # a failure that is not a bare interruption stays terminal
        adapter.save_job({**job, "failure": "ReviewPackageError: package_document_digest_mismatch"}, root)
        out = rc.control(job_id, "resume", root)
        require(not out["ok"] and out["status"] == "job_already_terminal",
                "a_real_failure_is_not_silently_treated_as_recoverable")
        require(out["recovery"] == "failure_is_a_refusal", "the_refusal_names_why")

        # a completed checkpoint is not recoverable either
        adapter.save_job(job, root)
        cp.write(position={"level": "finished"}, completed_units=["observe:D1:1"], next_unit="",
                 state={"review_id": "rev_rec"}, status="complete")
        out = rc.resumable_checkpoint(job, root)
        require(not out["resumable"] and out["reason"] == "checkpoint_not_live:complete",
                "a_finished_checkpoint_is_not_offered_for_resume")

        # An interruption wears whatever message was written last. A second crash shape must not lock the operator
        # out of work the checkpoint says is still live: this exact case cost a real review its resume button.
        cp.write(position={"level": "observe"}, completed_units=["observe:D1:1", "observe:D2:1"],
                 next_unit="", state={"review_id": "rev_rec"}, status=pause.RUNNING)
        adapter.save_job({**job, "failure": "FileExistsError: review directory already exists: " + str(private)},
                         root)
        out = rc.resumable_checkpoint(adapter._read(adapter._job_path(job_id, root)), root)
        require(out["resumable"], "an_unfamiliar_interruption_message_does_not_hide_live_work")

        # ...but a checkpoint that cannot vouch for itself promises something resume would refuse
        target = pause.checkpoint_path(job_id, controls)
        sealed = json.loads(target.read_text(encoding="utf-8"))
        target.write_text(json.dumps({**sealed, "completed_unit_count": 99}), encoding="utf-8")
        out = rc.resumable_checkpoint(adapter._read(adapter._job_path(job_id, root)), root)
        require(not out["resumable"] and out["reason"] == "checkpoint_refused:checkpoint_digest_mismatch",
                "a_checkpoint_whose_seal_does_not_hold_is_not_offered_for_resume")
        target.write_text(json.dumps(sealed), encoding="utf-8")

        # an accepted resume reads as live at once, so a second press cannot start a second worker
        adapter.save_job({**job, "failure": "job_process_ended_without_result"}, root)
        spawned = []
        original = adapter.SPAWN
        adapter.SPAWN = lambda argv, cwd, env: (spawned.append(list(argv)), 4242)[1]
        try:
            require(rc.control(job_id, "resume", root)["ok"], "the_recovered_job_resumes")
            live = adapter._read(adapter._job_path(job_id, root))
            require(live["status"] == "running" and live["pid"] == 4242,
                    "an_accepted_resume_marks_the_work_live")
            require(not live.get("failure") and not live.get("finished"),
                    "the_resumed_job_no_longer_carries_the_interruption")
            second = rc.control(job_id, "resume", root)
            require(not second["ok"] and second["status"] == "job_not_paused",
                    "a_second_press_does_not_start_a_second_worker")
            require(len(spawned) == 1, "exactly_one_worker_was_started")
        finally:
            adapter.SPAWN = original

    # --- 6c. the decorated payload detects recovery from the job records --------------------------------------
    require(rc.decorate({"activities": [activity_row("failed")]}, None)["activities"][0]["control"]["enabled"]
            is False, "without_a_data_root_a_failed_activity_is_not_assumed_recoverable")

    # --- 6c-bis. the row the surfaces actually draw carries the control -------------------------------------
    # Both the desktop panel and the web page render `current`, and running work only ever appears there. An
    # undecorated `current` meant the control was missing from precisely the case it exists for.
    running_row = activity_row("running")
    decorated = rc.decorate({"activities": [running_row], "current": running_row, "activity": running_row}, None)
    for where in ("activities", "current", "activity"):
        got = decorated[where][0] if where == "activities" else decorated[where]
        require((got.get("control") or {}).get("action") == "pause" and got["control"]["enabled"],
                f"running_work_offers_pause_in_{where}")
    require("control" in rc.decorate({"current": activity_row("running")}, None)["current"],
            "a_payload_with_only_a_current_row_is_still_decorated")

    # --- 6d. the runner continues live checkpointed work instead of starting a second review -----------------
    # The control can only offer what the worker will honour. Keying this on the job's status meant a crashed run
    # was restarted from scratch and refused by the reviewer's single-review guard, reaching nothing.
    with tempfile.TemporaryDirectory(prefix="v2733-route-") as tmp:
        root = Path(tmp)
        import experiment_review as frozen
        import experiment_review_hierarchical as hier
        import run_review_job as runner

        job_id, manifest = "job_route", "c" * 64
        private = root / "research_review_runtimes" / job_id
        job = {"job_id": job_id, "manifest_sha256": manifest, "status": "failed",
               "failure": "job_process_ended_without_result", "runtime_root": str(root),
               "private_runtime_root": str(private)}
        controls = hier.control_root_for(private, manifest, job_id)
        require(controls == rc._controls_root(job, root),
                "the_control_and_the_runner_look_for_the_checkpoint_in_the_same_place")

        require(runner._resumable(job, private, hier) is False, "with_no_checkpoint_the_runner_starts_fresh")
        cp = pause.Checkpointer(job_id, controls, bindings={"manifest_sha256": manifest})
        cp.write(position={"level": "observe"}, completed_units=["observe:D1:1"], next_unit="observe:D2:1",
                 state={"review_id": "rev_route"}, status=pause.RUNNING)
        require(runner._resumable(job, private, hier) is True,
                "a_crashed_run_with_live_work_is_routed_to_resume_not_restarted")
        cp.write(position={"level": "observe"}, completed_units=["observe:D1:1"], next_unit="",
                 state={"review_id": "rev_route"}, status=pause.PAUSED)
        require(runner._resumable(job, private, hier) is True, "a_deliberate_pause_still_resumes")
        cp.write(position={"level": "finished"}, completed_units=["observe:D1:1"], next_unit="",
                 state={"review_id": "rev_route"}, status="complete")
        require(runner._resumable(job, private, hier) is False, "finished_work_is_never_resumed")
        require(runner._resumable({**job, "manifest_sha256": ""}, private, hier) is False,
                "work_with_no_package_binding_is_never_resumed")
        require(runner._resumable(job, private, frozen) is False,
                "a_reviewer_without_resume_is_never_asked_to_resume")

    # --- 7. the control changes no contract ------------------------------------------------------------------
    require("paused" not in act.TERMINAL and "pause_requested" not in act.TERMINAL,
            "pause_states_remain_nonterminal")
    require("cancelled" in act.TERMINAL, "cancelled_remains_terminal")
    source = (ROOT / "conscious_agent" / "research_control.py").read_text(encoding="utf-8")
    require("keep_alive" not in source and "call_model" not in source,
            "the_control_never_touches_the_provider_directly")
    require("review_experiment" not in source, "the_control_never_runs_a_review_itself")

    # --- 8. the rendered control, in node ---------------------------------------------------------------------
    ui = subprocess.run([  # noqa: S603,S607 - fixed local test command
        "node", str(ROOT / "tools" / "v2733_6_1_research_control_ui.test.js")],
        capture_output=True, text=True)
    require(ui.returncode == 0, "the_rendered_control_suite_passes")
    if ui.returncode != 0:
        print(ui.stdout[-2000:], ui.stderr[-2000:])
    else:
        summary = json.loads(ui.stdout.strip().splitlines()[-1])
        require(summary["failed"] == [], "the_rendered_control_suite_reports_no_failures")
        print(f"  node ui suite: {summary['passed']}/{summary['checks']} checks")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2733.6.0-research-control", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:12]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
