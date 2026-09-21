"""v2733.4.0 - a paused review must not be reported as a finished one.

The live Q-PAUSE smoke proved the mechanical pause/resume path works and then caught the telemetry lying about it.
The review paused, checkpointed, released Ollama, resumed the same review and completed 11 unique units at 100%
coverage - and Activity recorded state ``incomplete``, event ``job_incomplete``, metrics frozen at the two pre-pause
calls, and no resumed history at all.

Three defects, all here rather than in the reviewer: the observer mapped any non-complete segment result to the
terminal ``incomplete``; ``Activity`` could not reopen a record, so the resumed segment had nowhere to go; and the
reviewer's pause and resume boundaries were never bridged into telemetry.

    python tools/v2733_4_0_activity_pause_tests.py
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
import review_activity as ra  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


def job(job_id: str = "job_test", status: str = "running") -> dict:
    return {"job_id": job_id, "task_id": "task_1", "package_id": "Q-TEST",
            "reviewer_contract": "v2733.0", "status": status, "started": "2026-09-21T00:00:00.000Z"}


def record_for(root: Path, job_id: str = "job_test") -> dict:
    return json.loads((root / act.AREA / f"{job_id}.json").read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="v2733-activity-") as tmp:
        root = Path(tmp)

        # --- 1. pause maps to paused, not incomplete ----------------------------------------------------------
        observer = ra.ReviewActivity(job(), root)
        observer.counts.update({"model_calls": 2, "grounded_observations": 13})
        observer.finish({**job(), "status": "paused", "review_id": "rev1"},
                        {"status": "paused", "checkpoint_digest": "d" * 64, "completed_units": 2})
        rec = record_for(root)
        require(rec["state"] == "paused", "a_paused_segment_reports_paused")
        require(rec["state"] != "incomplete", "a_pause_is_not_reported_as_incomplete")
        require(rec["events"][-1]["event"] == "paused", "the_last_event_is_paused_not_job_incomplete")
        require(not rec.get("result"), "a_paused_review_publishes_no_result")

        # --- 2. paused is nonterminal and keeps checkpoint identity -------------------------------------------
        require("paused" not in act.TERMINAL, "paused_is_not_a_terminal_state")
        require("pause_requested" not in act.TERMINAL, "pause_requested_is_not_a_terminal_state")
        require("cancelled" in act.TERMINAL, "cancelled_is_still_terminal")
        require(rec["identities"].get("checkpoint_digest", "").startswith("d"),
                "the_paused_record_carries_the_checkpoint_digest")
        require(rec["metrics"]["model_calls"] == 2, "the_paused_record_carries_its_metrics")

        # --- 3. resume reuses the same activity id and its metrics ---------------------------------------------
        resumed = ra.ReviewActivity(job(status="paused"), root, resuming=True)
        require(resumed.activity.record["activity_id"] == "job_test", "resume_reuses_the_same_activity_id")
        require(resumed.counts["model_calls"] == 2, "cumulative_model_calls_survive_the_resume")
        require(resumed.counts["grounded_observations"] == 13,
                "cumulative_grounded_observations_survive_the_resume")
        rec = record_for(root)
        require(rec["events"][-1]["event"] == "resume_requested", "the_resume_is_recorded_on_the_same_history")
        require(len([p for p in (root / act.AREA).glob("*.json")]) == 1,
                "resuming_creates_no_second_activity")

        # --- 4. reviewer boundary events reach telemetry -------------------------------------------------------
        for event in ("pause_requested", "model_released", "paused", "checkpoint_integrity_verified", "resumed"):
            resumed.on_reviewer_event(event, {"review_id": "rev1", "checkpoint_digest": "e" * 64,
                                              "unit": "observe:D1:1", "level": "observe"})
        rec = record_for(root)
        seen = [e["event"] for e in rec["events"]]
        for event in ("pause_requested", "model_released", "paused", "checkpoint_integrity_verified", "resumed"):
            require(event in seen, f"the_reviewer_boundary_is_visible_in_telemetry:{event}")
        require(rec["state"] == "running", "the_activity_is_running_again_after_resumed")

        # --- 5. a completed resume ends in the real final state, with cumulative metrics ------------------------
        resumed.counts.update({"model_calls": 11})
        resumed.finish({**job(), "status": "completed", "review_id": "rev1"},
                       {"status": "complete", "mutation_guard": {"passed": True},
                        "coverage": {"required_parts": 3, "reviewed_required_parts": 3,
                                     "required_coverage": 1.0, "grounded_observations": 20, "missing": []},
                        "provenance": {"model": {"provider": "ollama", "model": "qwen3.8:27b"}}})
        rec = record_for(root)
        require(rec["state"] == "complete", "the_final_state_matches_the_real_review_result")
        require(rec["metrics"]["model_calls"] == 11, "final_metrics_are_cumulative_not_just_the_last_segment")
        require(rec["metrics"]["grounded_observations"] == 20, "final_observation_count_is_the_whole_review")
        require(rec["metrics"]["missing_required_parts"] == 0, "missing_parts_come_from_the_artifact_not_one_segment")
        require(rec["metrics"].get("coverage_percent") == 100.0, "coverage_is_reported_truthfully")
        history = [e["event"] for e in rec["events"]]
        require("paused" in history and "resumed" in history,
                "completion_does_not_erase_the_pause_history")
        require(history[-1] == "job_complete", "the_history_ends_at_the_real_terminal_event")

        # --- 6. repeated pause and resume cycles ----------------------------------------------------------------
        cycles = ra.ReviewActivity(job("job_cycles"), root)
        for n in range(3):
            cycles.counts["model_calls"] += 2
            cycles.finish({**job("job_cycles"), "status": "paused"}, {"status": "paused"})
            require(record_for(root, "job_cycles")["state"] == "paused", f"cycle_{n}_pauses")
            cycles = ra.ReviewActivity(job("job_cycles", "paused"), root, resuming=True)
            require(cycles.counts["model_calls"] == 2 * (n + 1), f"cycle_{n}_carries_cumulative_metrics")
        require(len([p for p in (root / act.AREA).glob("job_cycles*.json")]) == 1,
                "many_cycles_still_leave_exactly_one_activity")

        # --- 7. pause then cancel, and pause then a genuine incomplete ------------------------------------------
        cancelled = ra.ReviewActivity(job("job_cancel"), root)
        cancelled.finish({**job("job_cancel"), "status": "paused"}, {"status": "paused"})
        cancelled = ra.ReviewActivity(job("job_cancel", "paused"), root, resuming=True)
        cancelled.finish({**job("job_cancel"), "status": "completed"},
                         {"status": "cancelled", "coverage": {}, "mutation_guard": {}})
        require(record_for(root, "job_cancel")["state"] == "incomplete",
                "a_cancelled_review_after_a_pause_still_reaches_a_terminal_state")

        thin = ra.ReviewActivity(job("job_thin"), root)
        thin.finish({**job("job_thin"), "status": "paused"}, {"status": "paused"})
        thin = ra.ReviewActivity(job("job_thin", "paused"), root, resuming=True)
        thin.finish({**job("job_thin"), "status": "completed"},
                    {"status": "incomplete", "mutation_guard": {"passed": True},
                     "coverage": {"required_parts": 3, "reviewed_required_parts": 2, "required_coverage": 0.667,
                                  "grounded_observations": 9, "missing": [{"kind": "required_part_not_reviewed"}]}})
        rec = record_for(root, "job_thin")
        require(rec["state"] == "incomplete", "a_genuinely_incomplete_review_after_a_pause_is_still_incomplete")
        require(rec["metrics"]["missing_required_parts"] == 1, "the_incomplete_review_reports_its_missing_part")

        # --- 8. duplicate resume and terminal reopen both fail closed -------------------------------------------
        refused = ""
        try:
            act.Activity.reopen("job_thin", root=root)
        except ValueError as exc:
            refused = str(exc)
        require(refused == "activity_already_terminal", "a_terminal_activity_refuses_to_reopen")

        missing = ""
        try:
            act.Activity.reopen("job_never_existed", root=root)
        except FileNotFoundError as exc:
            missing = str(exc)
        require(missing == "activity_not_found", "reopening_an_activity_that_never_existed_refuses")

        # observing_review must drop telemetry rather than fork a second activity
        with ra.observing_review(job("job_thin", "paused"), root, None, resuming=True) as observer2:
            require(observer2 is None, "a_resume_that_cannot_continue_drops_telemetry_instead_of_forking")
        require(len([p for p in (root / act.AREA).glob("job_thin*.json")]) == 1,
                "no_second_activity_file_is_created_for_a_refused_resume")

        # --- 9. an observer restarted while paused continues the same record ------------------------------------
        restarted = ra.ReviewActivity(job("job_cycles", "paused"), root, resuming=True)
        require(restarted.activity.record["activity_id"] == "job_cycles",
                "an_observer_restarted_while_paused_reopens_the_same_activity")
        require(restarted.counts["model_calls"] == 6, "a_restarted_observer_keeps_the_cumulative_metrics")

        # --- 10. no semantic leakage ----------------------------------------------------------------------------
        leaky = ra.ReviewActivity(job("job_leak"), root)
        leaky.on_reviewer_event("paused", {
            "review_id": "rev9", "checkpoint_digest": "f" * 64, "unit": "observe:D1:1", "level": "observe",
            "prompt": "You are Eidolon, reviewing...", "reply": "the model said something",
            "statement": "a semantic claim", "quotes": ["an exact quote"], "disposition": "use",
            "gold": "forbidden", "thinking": "hidden reasoning"})
        blob = json.dumps(record_for(root, "job_leak")).lower()
        for forbidden in ("you are eidolon", "the model said", "a semantic claim", "an exact quote",
                          "disposition", "gold", "hidden reasoning", "thinking"):
            require(forbidden not in blob, f"no_semantic_content_reaches_the_activity_record:{forbidden}")
        rec = record_for(root, "job_leak")
        require(set(rec["identities"]) <= {"job_id", "task_id", "package_id", "reviewer_contract", "review_id",
                                           "checkpoint_digest", "unit", "level", "completed_units",
                                           "from_sequence", "current_document", "current_part", "provider",
                                           "model"},
                "only_operational_identifiers_are_exposed")

        # --- 11. telemetry never changes the reviewed operation ---------------------------------------------------
        broken = ra.ReviewActivity(job("job_broken"), root)
        broken.activity.path = root / act.AREA / "unwritable" / "x.json"
        broken.on_reviewer_event("paused", {"review_id": "rev"})
        broken.finish({**job("job_broken"), "status": "paused"}, {"status": "paused"})
        require(True, "a_failing_activity_write_never_raises_into_the_review")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2733.4.0-activity-pause", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:12]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
