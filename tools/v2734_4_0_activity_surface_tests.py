"""v2734.4.0 - the operator console must describe the review it is watching.

G-CORROB1 Attempt 4 was abandoned deliberately, with 28 units and 193 grounded observations intact, because the
console misreported its state in three ways at once:

* a paused activity was rewritten to ``blocked`` once its heartbeats stopped, so Pause worked every time and Play
  never appeared - which read, from outside, as "pause is broken";
* ``progress.completed`` counted only the segment since the last resume, so a review 28 units in announced 1 / 140;
* the elapsed timer used wall clock until terminal, so it kept climbing through a two hour pause.

None of it corrupted the review. All of it made a multi-hour supervised run impossible to supervise.

These tests pin the repaired contract: intentionally quiescent is distinguished from stale, progress belongs to the
review rather than the process, and the timer measures work rather than time.

    python tools/v2734_4_0_activity_surface_tests.py
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import activity as act  # noqa: E402
import cooperative_pause as pause  # noqa: E402
import experiment_review_hierarchical as hier  # noqa: E402
import research_control as rc  # noqa: E402
import review_activity as ra  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def clocked(root, activity_id, moment, state="running"):
    obj = act.Activity(activity_id, "experiment_review", "Independent experiment review", "PKG",
                       root=root, stages=("Preparing", "Observing"), clock=lambda: moment["t"])
    obj.update("job_started", state=state)
    return obj


def row_of(root, activity_id):
    for row in act.activities(root)["activities"]:
        if row["activity_id"] == activity_id:
            return row
    return {}


def main() -> int:
    # --- 1-4. staleness must not overwrite a deliberate pause ---------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2734-stale-") as tmp:
        root = Path(tmp)
        fresh = {"t": act.now()}
        live = clocked(root, "job_live", fresh)
        require(row_of(root, "job_live")["state"] == "running", "a_running_activity_with_a_fresh_heartbeat_stays_running")

        # a genuinely stale running producer is still reported blocked
        stale_running = clocked(root, "job_stale", {"t": "2020-01-01T00:00:00.000Z"})
        require(row_of(root, "job_stale")["state"] == "blocked", "a_truly_stale_running_activity_still_becomes_blocked")
        require("stale_telemetry" in row_of(root, "job_stale")["warnings"], "and_is_warned_about")

        old = {"t": "2020-01-01T00:00:00.000Z"}
        paused = clocked(root, "job_paused", old)
        paused.update("paused", state="paused")
        require(row_of(root, "job_paused")["state"] == "paused",
                "a_paused_activity_stays_paused_long_past_the_stale_threshold")
        require("stale_telemetry" not in row_of(root, "job_paused")["warnings"],
                "a_paused_activity_is_not_warned_as_stale")

        requested = clocked(root, "job_requested", old)
        requested.update("pause_requested", state="pause_requested")
        require(row_of(root, "job_requested")["state"] == "pause_requested",
                "pause_requested_is_not_rewritten_by_staleness")

        # terminal stays terminal
        done = clocked(root, "job_done", old)
        done.update("job_complete", state="complete")
        require(row_of(root, "job_done")["state"] == "complete", "terminal_states_remain_terminal")

    # --- 5-6, 18-19. the affordance follows authoritative state --------------------------------------------------
    def control(state):
        return rc.affordance({"activity_id": "x", "type": "experiment_review", "state": state})

    require(control("paused")["action"] == "resume" and control("paused")["enabled"],
            "a_paused_activity_offers_resume")
    require(control("running")["action"] == "pause" and control("running")["enabled"],
            "a_running_activity_offers_pause")
    require(control("preparing")["action"] == "pause" and control("preparing")["enabled"],
            "a_preparing_activity_offers_pause")
    require(control("pause_requested")["pending"] and not control("pause_requested")["enabled"],
            "pause_requested_is_pending_and_not_clickable")
    for state in ("complete", "incomplete", "failed", "cancelled"):
        require(not control(state)["enabled"] and not control(state)["action"],
                f"a_{state}_activity_cannot_be_resumed")
    require(rc.ACTIONS == ("pause", "resume"), "no_duplicate_or_extra_control_actions_exist")

    with tempfile.TemporaryDirectory(prefix="v2734-dup-") as tmp:
        import conversational_experiment_review as adapter

        root = Path(tmp)
        (root / adapter.JOB_AREA).mkdir(parents=True, exist_ok=True)
        private = root / "research_review_runtimes" / "job_dup"
        job = {"job_id": "job_dup", "manifest_sha256": "a" * 64, "status": "running",
               "private_runtime_root": str(private), "runtime_root": str(root), "started": "2026-01-01T00:00:00Z"}
        adapter.save_job(job, root)
        controls = rc._controls_root(job, root)
        first = rc.control("job_dup", "pause", root)
        second = rc.control("job_dup", "pause", root)
        require(first["status"] == "pause_requested" and second["status"] == "pause_already_requested",
                "a_repeated_pause_does_not_stack_a_second_request")
        history = json.loads(pause.control_path("job_dup", controls).read_text(encoding="utf-8"))["history"]
        require(len(history) == 1, "only_one_governed_request_is_written")

    # --- 7-9. progress belongs to the review, not to the process -------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2734-progress-") as tmp:
        root = Path(tmp)
        private = root / "rt"
        manifest = "b" * 64
        job = {"job_id": "job_prog", "manifest_sha256": manifest, "private_runtime_root": str(private),
               "runtime_root": str(root)}
        controls = hier.control_root_for(private, manifest, "job_prog")
        cp = pause.Checkpointer("job_prog", controls, bindings={"manifest_sha256": manifest})

        def seal(done_parts, status=pause.PAUSED):
            coverage = [{"stage": f"observe:{d}:{p}", "doc_id": d, "part": p, "reviewed": True} for d, p in done_parts]
            cp.write(position={"level": "observe"}, completed_units=[c["stage"] for c in coverage],
                     next_unit="", state={"review_id": "rev", "parts_coverage": coverage}, status=status)

        require(ra.completed_parts_from_checkpoint(job, root) == set(),
                "with_no_checkpoint_nothing_is_seeded")
        seal([("D1", 1), ("D1", 2), ("D2", 1)])
        seeded = ra.completed_parts_from_checkpoint(job, root)
        require(seeded == {("D1", 1), ("D1", 2), ("D2", 1)},
                "progress_is_seeded_from_the_checkpoints_completed_units")

        # one pause/resume cycle: three done before, one after, shows four
        seen = set(seeded)
        seen.add(("D2", 2))
        require(len(seen) == 4, "progress_survives_one_pause_and_resume")

        # several cycles keep accumulating, and a unit is never double counted
        seal([("D1", 1), ("D1", 2), ("D2", 1), ("D2", 2)])
        again = ra.completed_parts_from_checkpoint(job, root)
        again.add(("D3", 1))
        require(len(again) == 5, "progress_survives_multiple_pause_and_resume_cycles")
        again.add(("D1", 1))
        require(len(again) == 5, "a_unit_already_counted_is_not_counted_twice")

        # unreadable checkpoint state never breaks telemetry
        require(ra.completed_parts_from_checkpoint({"job_id": "x"}, root) == set(),
                "an_unreadable_checkpoint_seeds_nothing_rather_than_raising")

    # --- 10-14. the timer measures work ---------------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="v2734-clock-") as tmp:
        root = Path(tmp)
        moment = {"t": "2026-01-01T00:00:00.000Z"}
        obj = clocked(root, "job_clock", moment)

        moment["t"] = "2026-01-01T02:00:00.000Z"
        obj.update("paused", state="paused")
        require(act.project(obj.record, "2026-01-01T02:00:00.000Z")["elapsed_seconds"] == 7200,
                "the_timer_advances_while_running")
        require(act.project(obj.record, "2026-01-01T05:00:00.000Z")["elapsed_seconds"] == 7200,
                "the_timer_freezes_while_paused")

        moment["t"] = "2026-01-01T05:00:00.000Z"
        obj.update("resumed", state="running")
        require(act.project(obj.record, "2026-01-01T05:30:00.000Z")["elapsed_seconds"] == 9000,
                "the_timer_resumes_from_the_accumulated_active_time")

        moment["t"] = "2026-01-01T06:00:00.000Z"
        final = obj.update("job_complete", state="complete")
        require(final["elapsed_seconds"] == 10800, "several_running_segments_sum_correctly")
        require(final["wall_elapsed_seconds"] == 21600, "wall_clock_remains_available_beside_it")
        require(act.project(obj.record, "2027-01-01T00:00:00.000Z")["elapsed_seconds"] == 10800,
                "terminal_elapsed_never_moves_again")

        legacy = {"contract": act.CONTRACT, "activity_id": "old", "state": "complete",
                  "started": "2026-01-01T00:00:00.000Z", "finished": "2026-01-01T00:02:03.000Z", "updated": ""}
        require(act.project(legacy, "2027-01-01T00:00:00.000Z")["elapsed_seconds"] == 123,
                "records_written_before_active_accounting_keep_their_wall_clock_reading")

    # --- 14b. a duration reads the way a person says one -------------------------------------------------------
    from desktop_activity import human_duration

    for seconds, expected in ((21241, "5 hrs 54 mins 1 sec"), (119, "1 min 59 secs"), (3600, "1 hr"),
                              (3661, "1 hr 1 min 1 sec"), (3605, "1 hr 5 secs"), (7200, "2 hrs"),
                              (1, "1 sec"), (59, "59 secs"), (60, "1 min"), (0, "0 secs"),
                              (86399, "23 hrs 59 mins 59 secs")):
        require(human_duration(seconds) == expected, f"{seconds}s_reads_as_{expected.replace(' ', '_')}")
    require("0 hr" not in human_duration(119) and "0 min" not in human_duration(3605),
            "a_unit_that_is_zero_is_left_out_entirely")
    require(human_duration(3600).endswith("hr") and human_duration(7200).endswith("hrs"),
            "units_are_singular_or_plural_on_their_own_count")

    # --- 15-17. both surfaces read the same projection ------------------------------------------------------------
    desktop = (ROOT / "conscious_agent" / "desktop_activity.py").read_text(encoding="utf-8")
    page = (ROOT / "conscious_agent" / "static" / "activity.js").read_text(encoding="utf-8")
    require('self.client.get("/activities"' in desktop, "the_desktop_reads_the_shared_activities_projection")
    require("data.current || rows[0]" in page, "the_web_page_reads_the_same_current_row")
    for surface, text in (("desktop", desktop), ("web", page)):
        require("elapsed_seconds" in text, f"the_{surface}_renders_the_projected_elapsed_time")
        require("hr" in text and "min" in text and "sec" in text,
                f"the_{surface}_spells_hours_minutes_and_seconds")
        require("control" in text, f"the_{surface}_renders_the_backend_control")
    require("a.control" in page and "control.enabled" in page, "the_web_control_comes_from_the_backend_not_the_browser")
    require("progress" in desktop and "percent" in page, "both_surfaces_render_the_projected_progress")
    require(".title =" not in page, "no_native_title_tooltip_regression")
    require("innerHTML" not in page, "the_page_never_assigns_innerhtml")
    require("data-tip" in page, "tooltips_stay_on_the_accessible_attribute")

    with tempfile.TemporaryDirectory(prefix="v2734-hidden-") as tmp:
        root = Path(tmp)
        moment = {"t": act.now()}
        obj = clocked(root, "job_hidden", moment)
        obj.update("model_call_started")
        obj.update("observations_grounded", metrics={"grounded_observations": 3})
        row = row_of(root, "job_hidden")
        blob = json.dumps(row)
        require("prompt" not in blob and "reply" not in blob, "no_prompt_or_reply_text_appears_in_telemetry")
        longest = max((len(str(v)) for e in row.get("events", []) for v in (e.get("detail") or {}).values()),
                      default=0)
        require(longest <= 200, "no_event_detail_carries_a_long_string")

    # --- 20. recovery activity behaviour is untouched --------------------------------------------------------------
    require(hasattr(ra, "completed_parts_from_checkpoint"), "the_seed_helper_is_part_of_the_review_activity_module")
    require(act.PAUSE_STATES == frozenset({"pause_requested", "paused"}), "the_pause_states_are_unchanged")
    require("paused" not in act.TERMINAL and "cancelled" in act.TERMINAL,
            "pause_is_still_non_terminal_and_cancel_is_still_terminal")
    require(act.ACTIVE_STATES == frozenset({"preparing", "running", "blocked"}),
            "only_genuinely_active_states_advance_the_clock")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2734.4.0-activity-surface", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:14]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
