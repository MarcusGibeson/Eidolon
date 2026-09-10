from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (AGENT, ROOT):
    if str(value) not in os.sys.path:
        os.sys.path.insert(0, str(value))

from endogenous_cognitive_cycle import BoundedCognitiveScheduler, EndogenousCognitiveCycle
from persistent_motivation import MotivationStore, motivation_state_contains_forbidden_authority


def require(condition: bool, detail: Any = "requirement failed") -> None:
    if not condition:
        raise AssertionError(detail)


def fixture() -> tuple[MotivationStore, EndogenousCognitiveCycle, Path]:
    root = Path(tempfile.mkdtemp(prefix="eidolon-v1104-4-")) / "cognition"
    motivation = MotivationStore(root)
    cycle = EndogenousCognitiveCycle(root, motivation_store=motivation)
    return motivation, cycle, root


def add_motivation(store: MotivationStore, event_id: str, *, kind: str, urgency: float, confidence: float = 0.8, valence: float = 0.0) -> str:
    result = store.record_motivation(
        event_id,
        kind=kind,
        summary=f"Fixture subject {event_id}",
        cognitive_state="intention" if "goal" in kind else "desire",
        urgency=urgency,
        confidence=confidence,
        valence=valence,
        origin_type="fixture",
        origin_ref=f"ref-{event_id}",
    )
    return str(result["result"]["motivation_id"])


def test_event_cycle_perceives_updates_models_and_selects_salient_subject() -> None:
    motivation, cycle, _ = fixture()
    low = add_motivation(motivation, "low", kind="curiosity", urgency=0.2)
    high = add_motivation(motivation, "high", kind="concern", urgency=0.95, valence=-0.8)
    result = cycle.run_cycle(
        "cycle-1",
        trigger_type="failure",
        perceived_events=[{"event_type": "failure", "event_ref": "test-failure-1", "motivation_id": high, "outcome": "failure"}],
        provider_available=False,
        now_epoch=1000,
    )
    receipt = result["receipt"]
    require(result["status"] == "completed", result)
    require(receipt["selected_motivation_id"] == high and receipt["selected_motivation_id"] != low, receipt)
    require(receipt["reflection_step_count"] == 1, receipt)
    require("world_model.event_type_counts" in receipt["changed_fields"], receipt)
    require(cycle.inspection_summary()["world_model"]["failure_count"] == 1, cycle.inspection_summary())
    self_model = motivation.snapshot()["self_model"]
    require(self_model["current_focus"] == high, self_model)


def test_intentional_silence_is_valid_when_no_subject_is_salient() -> None:
    motivation, cycle, _ = fixture()
    add_motivation(motivation, "quiet", kind="preference", urgency=0.01, confidence=0.1)
    result = cycle.run_cycle(
        "cycle-silence",
        trigger_type="cadence",
        perceived_events=[{"event_type": "time_change", "event_ref": "minute-1"}],
        provider_available=None,
        now_epoch=2000,
    )
    receipt = result["receipt"]
    require(result["status"] == "completed_with_silence", result)
    require(receipt["selected_motivation_id"] == "", receipt)
    require(receipt["communication_decision"] == "silence", receipt)
    require("deliberately" in receipt["communication_reason"], receipt)


def test_reflection_is_deduplicated_across_restart_retry_and_multiple_workers() -> None:
    motivation, cycle, root = fixture()
    motivation_id = add_motivation(motivation, "dedupe", kind="concern", urgency=0.9)
    first = cycle.run_cycle("same-cycle", trigger_type="event", perceived_events=[{"event_type": "memory_change", "event_ref": "memory-1"}], now_epoch=3000)
    restarted = EndogenousCognitiveCycle(root, motivation_store=MotivationStore(root))
    second = restarted.run_cycle("same-cycle", trigger_type="event", perceived_events=[{"event_type": "memory_change", "event_ref": "memory-1"}], worker_id="other-tab", now_epoch=3001)
    require(first["status"] == "completed", first)
    require(second["status"] == "duplicate_cycle_ignored", second)
    item = next(row for row in MotivationStore(root).snapshot()["motivations"] if row["motivation_id"] == motivation_id)
    attention_events = [row for row in item["update_history"] if row["event"] == "attention_and_reflection"]
    require(len(attention_events) == 1, item["update_history"])
    require(len(restarted.snapshot()["cycle_receipts"]) == 1, restarted.snapshot())


def test_stale_worker_generation_cannot_update_state() -> None:
    motivation, cycle, _ = fixture()
    add_motivation(motivation, "stale", kind="concern", urgency=0.9)
    cycle.set_control("wake-1", action="wake")
    current_generation = cycle.snapshot()["worker_generation"]
    stale = cycle.run_cycle("stale-cycle", trigger_type="event", worker_generation=current_generation - 1, now_epoch=4000)
    require(stale["status"] == "stale_worker_rejected", stale)
    require(stale["receipt"]["reflection_step_count"] == 0, stale)
    require(cycle.inspection_summary()["recent_reflections"] == [], cycle.inspection_summary())


def test_pause_resume_sleep_and_wake_preserve_continuity() -> None:
    motivation, cycle, _ = fixture()
    motivation_id = add_motivation(motivation, "controls", kind="curiosity", urgency=0.9)
    cycle.set_control("pause", action="pause")
    paused = cycle.run_cycle("paused-cycle", trigger_type="event", now_epoch=5000)
    require(paused["status"] == "paused", paused)
    cycle.set_control("resume", action="resume")
    resumed = cycle.run_cycle("resumed-cycle", trigger_type="event", now_epoch=5001)
    require(resumed["status"] == "completed", resumed)
    cycle.set_control("sleep", action="sleep")
    sleeping = cycle.run_cycle("sleep-cycle", trigger_type="event", now_epoch=5002)
    require(sleeping["status"] == "sleeping", sleeping)
    prior_generation = cycle.snapshot()["worker_generation"]
    cycle.set_control("wake", action="wake")
    require(cycle.snapshot()["worker_generation"] == prior_generation + 1, cycle.snapshot())
    require(any(row["motivation_id"] == motivation_id for row in motivation.snapshot()["motivations"]), motivation.snapshot())


def test_hourly_and_cadence_budgets_bound_idle_operation() -> None:
    motivation, cycle, _ = fixture()
    add_motivation(motivation, "budget", kind="concern", urgency=0.9)
    cycle.set_control("budget", action="adjust_budget", cadence_seconds=60, max_cycles_per_hour=1, max_cycles_per_day=2)
    first = cycle.run_due_cadence(now_epoch=6000)
    second = cycle.run_due_cadence(now_epoch=6001)
    another_event = cycle.run_cycle("event-after-budget", trigger_type="event", now_epoch=6002)
    require(first["status"] == "completed", first)
    require(second["status"] == "duplicate_cycle_ignored" or second["status"] == "hourly_budget_exhausted", second)
    require(another_event["status"] == "hourly_budget_exhausted", another_event)
    require(len(cycle.inspection_summary()["recent_reflections"]) == 1, cycle.inspection_summary())


def test_completed_failure_memory_and_unresolved_events_change_structural_world_model() -> None:
    motivation, cycle, _ = fixture()
    add_motivation(motivation, "world", kind="unresolved_subject", urgency=0.85)
    result = cycle.run_cycle(
        "world-cycle",
        trigger_type="event",
        perceived_events=[
            {"event_type": "completed_work", "event_ref": "work-1"},
            {"event_type": "failure", "event_ref": "failure-1"},
            {"event_type": "memory_change", "event_ref": "memory-1"},
            {"event_type": "unresolved_conversation", "event_ref": "conversation-1"},
        ],
        now_epoch=7000,
    )
    world = cycle.inspection_summary()["world_model"]
    require(result["status"] == "completed", result)
    require(world["completed_work_count"] == 1 and world["failure_count"] == 1, world)
    require(world["memory_change_count"] == 1 and world["unresolved_conversation_count"] == 1, world)
    text = json.dumps(result["receipt"])
    require("work-1" not in text and "conversation-1" not in text, text)


def test_provider_unavailable_remains_safe_and_never_manages_models() -> None:
    motivation, cycle, _ = fixture()
    add_motivation(motivation, "offline", kind="curiosity", urgency=0.9)
    result = cycle.run_cycle("offline-cycle", trigger_type="provider_state_change", provider_available=False, now_epoch=8000)
    receipt = result["receipt"]
    require(receipt["provider_contacted"] is False and receipt["provider_call_count"] == 0, receipt)
    require(all(receipt[key] is False for key in ("model_installed", "model_pulled", "model_replaced", "model_deleted")), receipt)
    require("provider_free" in receipt["reflection_mode"], receipt)


def test_success_failure_correction_and_new_evidence_update_motivation() -> None:
    motivation, cycle, _ = fixture()
    success_id = add_motivation(motivation, "success", kind="temporary_goal", urgency=0.8, confidence=0.5)
    failure_id = add_motivation(motivation, "failure", kind="concern", urgency=0.5, confidence=0.8)
    correction_id = add_motivation(motivation, "correction", kind="preference", urgency=0.7, confidence=0.9)
    evidence_id = add_motivation(motivation, "evidence", kind="curiosity", urgency=0.6, confidence=0.2)
    cycle.run_cycle(
        "updates-cycle",
        trigger_type="event",
        perceived_events=[
            {"event_type": "completed_work", "event_ref": "success-ref", "motivation_id": success_id, "outcome": "success"},
            {"event_type": "failure", "event_ref": "failure-ref", "motivation_id": failure_id, "outcome": "failure"},
            {"event_type": "memory_change", "event_ref": "correction-ref", "motivation_id": correction_id, "outcome": "correction", "explicit_retraction": True},
            {"event_type": "memory_change", "event_ref": "evidence-ref", "motivation_id": evidence_id, "outcome": "new_evidence", "confidence": 0.75},
        ],
        now_epoch=9000,
    )
    by_id = {row["motivation_id"]: row for row in motivation.snapshot()["motivations"]}
    require(by_id[success_id]["lifecycle_state"] == "resolved", by_id[success_id])
    require(by_id[failure_id]["urgency"] > 0.5 and by_id[failure_id]["confidence"] < 0.8, by_id[failure_id])
    require(by_id[correction_id]["lifecycle_state"] == "retracted", by_id[correction_id])
    require(by_id[evidence_id]["confidence"] == 0.75, by_id[evidence_id])


def test_scheduler_tick_is_bounded_and_cycle_cannot_authorize_actions() -> None:
    motivation, cycle, _ = fixture()
    add_motivation(motivation, "scheduler", kind="concern", urgency=0.9)
    scheduler = BoundedCognitiveScheduler(cycle, poll_seconds=1)
    result = scheduler.tick(now_epoch=10000)
    require(result["status"] == "completed", result)
    receipt = result["receipt"]
    require(receipt["authorizes_action"] is False and receipt["executes_action"] is False and receipt["creates_approval"] is False, receipt)
    require(motivation_state_contains_forbidden_authority(motivation.snapshot()) is False, motivation.snapshot())
    summary = cycle.inspection_summary()
    require(summary["authority_boundary"]["can_authorize_action"] is False, summary)
    require(summary["controls"]["max_provider_calls_per_cycle"] == 0, summary)


TESTS = [(name.removeprefix("test_"), function) for name, function in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1104.4-endogenous-attention-reflection-cycle",
        "ok": passed == len(TESTS),
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
