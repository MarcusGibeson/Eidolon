from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

from context_budget_management import ContextBudgetLedger, build_context_budget_plan, context_budget_contains_private_fields
from conversation_context import build_conversation_prompt


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_plan_allocates_only_within_discretionary_budget() -> None:
    plan = build_context_budget_plan(
        input_budget_tokens=1000, essential_tokens=300,
        lane_candidates={"active_thread": 1, "recent_conversation": 6, "mood": 1, "important_moments": 2, "curated_memory": 4, "optional_context": 2},
    )
    allocated = sum(lane.allocated_tokens for lane in plan.lanes)
    require(allocated + plan.shared_reserve_tokens == plan.discretionary_tokens, "lane allocations exceed discretionary budget")
    require(plan.current_turn_protected and plan.correction_evidence_protected, "protected lanes missing")


def test_recent_history_and_memory_receive_distinct_budgets() -> None:
    plan = build_context_budget_plan(
        input_budget_tokens=1400, essential_tokens=300,
        lane_candidates={"recent_conversation": 6, "curated_memory": 6, "optional_context": 2},
    )
    require(plan.allocation("recent_conversation") > 0, "recent history has no budget")
    require(plan.allocation("curated_memory") > 0, "curated memory has no budget")
    require(plan.allocation("recent_conversation") != plan.discretionary_tokens, "one lane consumed all context")


def test_ledger_records_lane_exhaustion_without_partial_admission() -> None:
    plan = build_context_budget_plan(
        input_budget_tokens=500, essential_tokens=200,
        lane_candidates={"recent_conversation": 1, "curated_memory": 1, "optional_context": 1},
    )
    ledger = ContextBudgetLedger(plan)
    too_large = plan.allocation("curated_memory") + plan.shared_reserve_tokens + 1
    require(not ledger.admit("curated_memory", too_large, global_remaining=300), "oversized record was partially admitted")
    summary = ledger.public_summary()
    require(summary["omission_reasons"].get("lane_budget_exhausted") == 1, "lane exhaustion reason missing")
    require(summary["used_tokens"]["curated_memory"] == 0, "failed record consumed partial budget")


def test_prompt_preserves_whole_records_and_reports_omissions() -> None:
    memories = [
        {"id": f"m-{index}", "type": "fact", "content": f"UNIQUE_RECORD_{index}: Complete bounded memory record {index} " + ("detail " * 45), "importance": "medium", "state": "active"}
        for index in range(8)
    ]
    packet = build_conversation_prompt(
        user_message="Discuss the bounded memory records.", self_model={"name": "Eidolon"}, desires={}, memories=memories,
        project_context="", goal_context="", task_context="", conversation_history=[], context_size=1500, max_tokens=256,
    )
    metrics = packet.metrics.to_dict()
    require(metrics["memories_omitted"] > 0, "tight budget did not record omitted memories")
    require(metrics["context_budget_omissions_by_lane"].get("curated_memory", 0) > 0, "memory lane omission evidence absent")
    require(not metrics["context_budget_silent_truncation_allowed"], "silent truncation was enabled")
    for memory in memories:
        prefix = memory["content"][:16]
        if prefix in packet.prompt:
            require(" ".join(memory["content"].split()) in packet.prompt, "partial memory record entered prompt")


def test_explicit_correction_remains_protected_under_tight_budget() -> None:
    history = [{"user_message": "Where is the office?", "assistant_response": "The office is in Dayton."}]
    packet = build_conversation_prompt(
        user_message="Actually, the office is in Columbus.", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=history, context_size=1400, max_tokens=256,
    )
    require("Acknowledge the explicit correction" in packet.prompt, "correction guidance was displaced")
    require(packet.metrics.conversation_correction_acknowledge_once, "correction protection not recorded")


def test_budget_metrics_are_content_free_provider_free_and_read_only() -> None:
    packet = build_conversation_prompt(
        user_message="Discuss private garden planning.", self_model={"name": "Eidolon"}, desires={},
        memories=[{"type": "preference", "content": "Private garden planning detail.", "importance": "high", "state": "active"}],
        project_context="", goal_context="", task_context="", conversation_history=[], context_size=4096, max_tokens=256,
    )
    metrics = packet.metrics.to_dict()
    budget = {
        "allocated_tokens": metrics["context_budget_allocated_tokens"],
        "used_tokens": metrics["context_budget_used_tokens"],
        "omissions": metrics["context_budget_omissions_by_lane"],
        "reasons": metrics["context_budget_omission_reasons"],
    }
    require("private garden" not in json.dumps(budget).lower(), "budget evidence leaked content")
    require(not context_budget_contains_private_fields(budget), "budget evidence contains private fields")


def test_budget_allocation_is_deterministic() -> None:
    args = dict(input_budget_tokens=2048, essential_tokens=420, lane_candidates={"active_thread": 1, "recent_conversation": 4, "curated_memory": 5, "optional_context": 2})
    first = build_context_budget_plan(**args).public_summary()
    second = build_context_budget_plan(**args).public_summary()
    require(first == second, "budget allocation changed across equivalent runs")


TESTS = [
    ("plan_allocates_only_within_discretionary_budget", test_plan_allocates_only_within_discretionary_budget),
    ("recent_history_and_memory_receive_distinct_budgets", test_recent_history_and_memory_receive_distinct_budgets),
    ("ledger_records_lane_exhaustion_without_partial_admission", test_ledger_records_lane_exhaustion_without_partial_admission),
    ("prompt_preserves_whole_records_and_reports_omissions", test_prompt_preserves_whole_records_and_reports_omissions),
    ("explicit_correction_remains_protected_under_tight_budget", test_explicit_correction_remains_protected_under_tight_budget),
    ("budget_metrics_are_content_free_provider_free_and_read_only", test_budget_metrics_are_content_free_provider_free_and_read_only),
    ("budget_allocation_is_deterministic", test_budget_allocation_is_deterministic),
]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
    checks, passed = [], 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1085.4-context-budget-management", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
