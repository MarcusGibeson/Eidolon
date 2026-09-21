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
