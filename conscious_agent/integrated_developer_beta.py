from __future__ import annotations

"""Read-only v1240 Integrated Developer Beta benchmark contract.

The benchmark consolidates the supervised-development evidence chain from
v1230 through v1239. It uses content-free canonical scenarios and retained
checkpoint contracts. It never reads operator runtime records, invokes tools,
runs commands or tests, mutates a project, writes cognition, or grants authority.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping

CONTRACT_VERSION = "v1240.8"
MILESTONE_NAME = "Integrated Developer Beta"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"

AUTHORITY_FLAGS = {
    "benchmark_registry_inspection_authorized": True,
    "benchmark_evidence_authorized": True,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "dependency_installation_authorized": False,
    "runtime_download_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "tool_invocation_authorized": False,
    "launch_authorized": False,
    "pause_authorized": False,
    "resume_authorized": False,
    "cancel_authorized": False,
    "cognition_write_authorized": False,
    "automatic_continuation_authorized": False,
    "automatic_retry_authorized": False,
    "background_execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

RETAINED_CHECKPOINTS = (
    ("mindful_execution", "v1230.9", "mindful-execution-alpha-integration-benchmark-checkpoint", "mindful_execution_alpha_integration_benchmark_checkpoint", "build_mindful_execution_alpha_integration_benchmark_checkpoint"),
    ("plan_revision", "v1231.9", "dynamic-execution-plan-revision-checkpoint", "dynamic_execution_plan_revision_checkpoint", "build_dynamic_execution_plan_revision_checkpoint"),
    ("dependencies", "v1232.9", "dependency-aware-execution-checkpoint", "dependency_aware_execution_checkpoint", "build_dependency_aware_execution_checkpoint"),
    ("resources", "v1233.9", "resource-concurrency-governance-checkpoint", "resource_concurrency_governance_checkpoint", "build_resource_concurrency_governance_checkpoint"),
    ("quality", "v1234.9", "requirement-quality-assessment-checkpoint", "requirement_quality_assessment_checkpoint", "build_requirement_quality_assessment_checkpoint"),
    ("lessons", "v1235.9", "evidence-backed-development-outcome-lessons-checkpoint", "evidence_backed_development_outcome_lessons_checkpoint", "build_evidence_backed_development_outcome_lessons_checkpoint"),
    ("priority", "v1236.9", "goal-motivation-work-priority-integration-checkpoint", "goal_motivation_work_priority_integration_checkpoint", "build_goal_motivation_work_priority_integration_checkpoint"),
    ("orchestration", "v1237.9", "multi-tool-orchestration-checkpoint", "multi_tool_orchestration_checkpoint", "build_multi_tool_orchestration_checkpoint"),
    ("adapters", "v1238.9", "broader-project-language-adapters-checkpoint", "broader_project_language_adapters_checkpoint", "build_broader_project_language_adapters_checkpoint"),
    ("adversarial", "v1239.9", "adversarial-execution-cognitive-boundary-checkpoint", "adversarial_execution_cognitive_boundary_checkpoint", "build_adversarial_execution_cognitive_boundary_checkpoint"),
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _scenario(scenario_id: str, stages: tuple[str, ...], terminal: str, risks: tuple[str, ...]) -> dict[str, Any]:
    row = {
        "scenario_id": scenario_id,
        "required_stages": list(stages),
        "terminal_expectation": terminal,
        "risk_codes": list(risks),
        "content_free": True,
        "operator_authority_required_at_each_mutation": True,
        "automatic_continuation_allowed": False,
        "missing_evidence_is_pass": False,
    }
    row["scenario_digest"] = _digest(row)
    return row


_SCENARIOS = (
    _scenario("canonical_supervised_lifecycle", ("mindful_execution", "plan_revision", "dependencies", "resources", "orchestration", "adapters", "quality", "lessons", "priority"), "operator_reviewed_outcome", ("stale_lineage", "partial_evidence")),
    _scenario("dynamic_revision_after_changed_reality", ("plan_revision", "dependencies", "resources", "orchestration"), "revision_proposal_only", ("scope_expansion", "authority_reuse")),
    _scenario("dependency_blocked_execution", ("dependencies", "resources"), "fail_closed_blocked", ("missing_dependency", "stale_evidence")),
    _scenario("resource_conflict_and_fairness", ("resources", "priority"), "operator_hold_or_preemption_proposal", ("capacity_conflict", "starvation")),
    _scenario("multi_tool_adapter_handoff", ("orchestration", "adapters", "quality"), "fresh_authority_required_per_tool", ("wrong_adapter", "auto_continue")),
    _scenario("quality_gap_and_remediation", ("quality", "plan_revision", "dependencies"), "remediation_proposal_only", ("missing_acceptance_criteria", "false_positive")),
    _scenario("lesson_reconsideration", ("quality", "lessons", "priority"), "operator_reviewed_revisable_lesson", ("contradictory_evidence", "cognition_escalation")),
    _scenario("pause_crash_recovery_resume", ("mindful_execution", "adversarial"), "recovered_to_paused", ("auto_resume", "replay")),
    _scenario("cross_project_lineage_attack", ("plan_revision", "dependencies", "resources", "adversarial"), "lineage_rejected", ("project_swap", "digest_splice")),
    _scenario("privacy_and_provider_injection", ("orchestration", "adapters", "adversarial"), "fail_closed_content_free", ("private_content", "provider_injection")),
)

_SHOW_REGISTRY = re.compile(r"^show integrated developer beta scenario registry[.!?]*$", re.I)
_SHOW_BENCHMARK = re.compile(r"^show integrated developer beta benchmark[.!?]*$", re.I)


def scenario_registry() -> dict[str, Any]:
    counts = {"scenario_count": len(_SCENARIOS), "stage_count": len(RETAINED_CHECKPOINTS)}
    result = {"ok": True, "status": "integrated_developer_beta_scenario_registry_ready", "contract_version": CONTRACT_VERSION, "scenarios": [dict(x) for x in _SCENARIOS], **counts, "content_free": True, "read_only": True, **AUTHORITY_FLAGS}
    result["registry_digest"] = _digest(result)
    return result


def _builders() -> tuple[tuple[str, str, str, Callable[..., dict[str, Any]]], ...]:
    rows = []
    for stage, version, checkpoint_id, module_name, builder_name in RETAINED_CHECKPOINTS:
        try:
            module = __import__(f"conscious_agent.{module_name}", fromlist=[builder_name])
        except ImportError:
            module = __import__(module_name, fromlist=[builder_name])
        rows.append((stage, version, checkpoint_id, getattr(module, builder_name)))
    return tuple(rows)


def build_integrated_developer_beta_contract(*, source_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    stages = []
    for stage_id, expected_version, checkpoint_id, builder in _builders():
        report = builder(source_root=source)
        stages.append({
            "stage_id": stage_id,
            "checkpoint_id": checkpoint_id,
            "expected_contract_version": expected_version,
            "reported_contract_version": str(report.get("contract_version") or ""),
            "ok": report.get("ok") is True,
            "read_only": report.get("read_only") is True,
            "content_free": report.get("content_free") is True,
            "runtime_data_read": report.get("runtime_data_read") is True,
            "runtime_data_written": report.get("runtime_data_written") is True,
            "source_modified": report.get("source_modified") is True,
            "authority_granted": report.get("authority_granted") is True,
            "provider_contacted": report.get("provider_contacted") is True,
            "commands_executed": report.get("commands_executed") is True,
            "tests_executed": report.get("tests_executed") is True,
            "project_modified": report.get("project_modified") is True,
            "cognition_written": report.get("cognition_written") is True,
            "passed_checks": int(report.get("passed") or 0),
        })
    versions_match = all(x["reported_contract_version"] == x["expected_contract_version"] for x in stages)
    retained_ok = all(x["ok"] and x["read_only"] and x["content_free"] and not any(x[k] for k in ("runtime_data_read", "runtime_data_written", "source_modified", "authority_granted", "provider_contacted", "commands_executed", "tests_executed", "project_modified", "cognition_written")) for x in stages)
    registry = scenario_registry()
    complete_order = [x["stage_id"] for x in stages] == [x[0] for x in RETAINED_CHECKPOINTS]
    ok = versions_match and retained_ok and complete_order and registry.get("ok") is True
    result = {
        "ok": ok,
        "status": "integrated_developer_beta_contract_ready" if ok else "integrated_developer_beta_contract_blocked",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "retained_stage_count": len(stages),
        "scenario_count": len(_SCENARIOS),
        "stages": stages,
        "complete_stage_order": complete_order,
        "retained_versions_match": versions_match,
        "retained_checkpoints_pass": retained_ok,
        "scenario_registry_digest": registry["registry_digest"],
        "plan_revision_preserved": True,
        "dependency_readiness_preserved": True,
        "resource_admissibility_preserved": True,
        "quality_assessment_preserved": True,
        "lessons_revisable": True,
        "goal_priority_advisory_only": True,
        "tool_handoffs_require_fresh_authority": True,
        "adapter_selection_is_not_execution": True,
        "adversarial_fail_closed": True,
        "missing_timeout_or_incomplete_evidence_never_passes": True,
        "historical_receipts_remain_immutable": True,
        "os_level_sandbox_not_claimed": True,
        "runtime_data_read": False,
        "runtime_data_written": False,
        "source_modified": False,
        "content_free": True,
        "read_only": True,
        **AUTHORITY_FLAGS,
    }
    result["contract_digest"] = _digest(result)
    return result


def evaluate_integrated_scenario(scenario_id: str, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    scenario = next((x for x in _SCENARIOS if x["scenario_id"] == scenario_id), None)
    base = {"scenario_id": scenario_id, "content_free": True, "read_only": True, **AUTHORITY_FLAGS}
    if scenario is None:
        return {"ok": False, "status": "unknown_scenario", "reason_codes": ["unknown_scenario"], **base}
    supplied = dict(evidence or {})
    required = scenario["required_stages"]
    reported = supplied.get("completed_stages") if isinstance(supplied.get("completed_stages"), list) else []
    digest_ok = supplied.get("scenario_digest") == scenario["scenario_digest"]
    complete = reported == required
    no_missing_pass = supplied.get("missing_evidence_claimed_as_pass") is not True
    no_authority_claim = supplied.get("authority_granted") is not True
    ok = digest_ok and complete and no_missing_pass and no_authority_claim
    reasons = []
    if not digest_ok: reasons.append("stale_or_tampered_scenario_digest")
    if not complete: reasons.append("incomplete_or_reordered_stage_evidence")
    if not no_missing_pass: reasons.append("missing_evidence_cannot_pass")
    if not no_authority_claim: reasons.append("benchmark_evidence_cannot_grant_authority")
    result = {"ok": ok, "status": "scenario_evidence_verified" if ok else "scenario_evidence_blocked", "terminal_expectation": scenario["terminal_expectation"], "reason_codes": reasons, **base}
    result["evaluation_digest"] = _digest(result)
    return result


def canonical_scenario_evidence(scenario_id: str) -> dict[str, Any]:
    scenario = next((x for x in _SCENARIOS if x["scenario_id"] == scenario_id), None)
    if scenario is None: return {}
    return {"scenario_digest": scenario["scenario_digest"], "completed_stages": list(scenario["required_stages"]), "missing_evidence_claimed_as_pass": False, "authority_granted": False}


def integrated_developer_beta_response(row: Mapping[str, Any]) -> str:
    if row.get("status") == "integrated_developer_beta_scenario_registry_ready":
        return f"The Integrated Developer Beta registry contains {row.get('scenario_count')} content-free scenarios. It grants no execution authority."
    if row.get("status") in {"integrated_developer_beta_contract_ready", "integrated_developer_beta_contract_blocked"}:
        return f"Integrated Developer Beta benchmark: {row.get('status')}. Retained stages: {row.get('retained_stage_count')}; scenarios: {row.get('scenario_count')}. No tools or projects were touched."
    return "Integrated Developer Beta inspection is unavailable."


def process_integrated_developer_beta_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    text = str(user_text or "").strip()
    if _SHOW_REGISTRY.fullmatch(text):
        row = scenario_registry()
        return {"active": True, "response": integrated_developer_beta_response(row), "integrated_developer_beta": row}
    if _SHOW_BENCHMARK.fullmatch(text):
        row = build_integrated_developer_beta_contract()
        return {"active": True, "response": integrated_developer_beta_response(row), "integrated_developer_beta": row}
    return {"active": False}
