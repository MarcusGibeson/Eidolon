from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_to_candidate_planner import build_evidence_to_candidate_plans, evidence_to_candidate_response
from initiative_evidence_intake import build_initiative_evidence_intake
from operator_development_findings import list_operator_development_findings, record_operator_development_finding


checks: list[str] = []


def require(value: bool, label: str) -> None:
    if not value:
        raise AssertionError(label)
    checks.append(label)


def signature(paths: list[Path]) -> str:
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


tracked = [
    ROOT / "conscious_agent" / "evidence_to_candidate_planner.py",
    ROOT / "conscious_agent" / "v1489_product_capability_integration.py",
]
before = signature(tracked)

conversation = {
    "evidence_id": "initev_conversation",
    "evidence_digest": "a" * 64,
    "evidence_class": "conversation_quality_finding",
    "issue_domain": "model_quality",
    "impact_score": 0.91,
    "confidence": 0.94,
    "freshness": "current",
    "acceptance_criteria": ["current_question_answered"],
    "structural_only": False,
}
structural = {
    "evidence_id": "initev_structural",
    "evidence_digest": "b" * 64,
    "evidence_class": "structural_debt",
    "issue_domain": "structural",
    "impact_score": 0.4,
    "confidence": 1.0,
    "freshness": "current_source_snapshot",
    "structural_only": True,
}

ready = build_evidence_to_candidate_plans({"records": [structural, conversation]}, source_root=ROOT)
require(ready["ok"] and ready["status"] == "bounded_product_candidate_plan_ready", "product_evidence_binds_to_plan")
require(ready["plan_count"] == 1 and ready["ready_count"] == 1, "structural_evidence_is_excluded")
plan = ready["plans"][0]
require(plan["candidate_plan_id"].startswith("devplan_"), "plan_identity_is_stable")
require(plan["target_files"] and all(path.startswith("conscious_agent/") for path in plan["target_files"]), "target_scope_is_confined")
require("conscious_agent/conversation_context.py" in plan["target_files"], "model_quality_scope_includes_conversation_context")
require(plan["test_files"] and all(path.startswith("tools/") for path in plan["test_files"]), "attributable_tests_are_bound")
require("current_question_answered" in plan["acceptance_criteria"], "operator_acceptance_is_preserved")
require("review-only plan" in evidence_to_candidate_response(ready), "response_preserves_review_boundary")

stale = build_evidence_to_candidate_plans({"records": [{**conversation, "freshness": "stale"}]}, source_root=ROOT)
require(not stale["ok"] and stale["plans"][0]["planning_state"] == "scope_binding_required", "stale_evidence_cannot_be_implementation_ready")

unknown = build_evidence_to_candidate_plans({"records": [{**conversation, "issue_domain": "unknown"}]}, source_root=ROOT)
require(not unknown["ok"] and not unknown["plans"][0]["target_files"], "unknown_surface_stops_without_guessing")
require("could not bind" in evidence_to_candidate_response(unknown), "unknown_surface_explains_scope_stop")

explicit = build_evidence_to_candidate_plans({"records": [{**conversation, "source_module": "conscious_agent/conversation_context.py"}]}, source_root=ROOT)
require(explicit["ok"] and explicit["plans"][0]["target_files"][0] == "conscious_agent/conversation_context.py", "attributable_explicit_source_is_preferred")

traversal = build_evidence_to_candidate_plans({"records": [{**conversation, "source_module": "../private.py", "issue_domain": "unknown"}]}, source_root=ROOT)
require(not traversal["ok"] and not traversal["plans"][0]["target_files"], "path_traversal_is_rejected")

again = build_evidence_to_candidate_plans({"records": [conversation]}, source_root=ROOT)
require(again["planning_digest"] == ready["planning_digest"], "planning_is_deterministic")
require(not ready["provider_contacted"] and not ready["proposal_created"] and not ready["workspace_prepared"], "planning_creates_no_development_authority")
require(not ready["tests_executed"] and not ready["source_modified"] and not ready["authority_granted"], "planning_executes_nothing")
require(ready["content_free"] and not ready["private_content_inspected"], "planning_projection_is_content_free")

with tempfile.TemporaryDirectory() as td:
    recorded = record_operator_development_finding(
        "Record development finding: Chat responses sometimes lose the current conversational target.",
        runtime_root=td,
    )
    require(recorded["ok"] and recorded["runtime_mutated"], "explicit_operator_finding_is_recorded")
    require(recorded["development_finding"]["private_description_returned"] is False, "operator_finding_response_is_redacted")
    duplicate = record_operator_development_finding(
        "Record development finding: Chat responses sometimes lose the current conversational target.",
        runtime_root=td,
    )
    require(duplicate["ok"] and not duplicate["runtime_mutated"], "operator_finding_replay_is_idempotent")
    public_findings = list_operator_development_findings(runtime_root=td)
    intake = build_initiative_evidence_intake(conversation_findings=public_findings)
    from_intake = build_evidence_to_candidate_plans(intake, source_root=ROOT)
    require(from_intake["ok"] and from_intake["ready_count"] == 1, "recorded_finding_flows_into_product_plan")
    require(not from_intake["private_content_inspected"], "private_operator_description_never_enters_planner")
require(before == signature(tracked), "planner_preserves_source")

with tempfile.TemporaryDirectory() as td:
    research_finding = record_operator_development_finding(
        "Record development finding: Bounded research now calibrates recommendation language correctly, but "
        "candidate-specific source discovery often fails to obtain credible independent evidence for demand, "
        "competition, and free-tier feasibility. Evidence matrices are also repeated unnecessarily in the final report.",
        runtime_root=td,
    )
    public = research_finding["development_finding"]
    require(public["evidence_class"] == "operator_reported_defect", "research_finding_uses_product_defect_class")
    require(public["issue_domain"] == "bounded_research", "research_finding_routes_to_bounded_research")
    require(public["evidence_class"] != "conversation_quality_finding", "repeated_does_not_trigger_repeat_substring")
    research_intake = build_initiative_evidence_intake(operator_findings=[public])
    research_planning = build_evidence_to_candidate_plans(research_intake, source_root=ROOT)
    research_plan = research_planning["plans"][0]
    require(research_plan["implementation_ready"], "research_finding_binds_to_implementable_plan")
    require(
        research_plan["target_files"] == [
            "conscious_agent/bounded_research_reasoning.py",
            "conscious_agent/bounded_autonomous_web_research.py",
        ],
        "research_finding_uses_research_owners",
    )
    require(
        "tools/v2503_4_evidence_language_consistency_source_quality_tests.py" in research_plan["test_files"],
        "research_finding_binds_current_focused_suite",
    )

print(json.dumps({"ok": True, "suite": "evidence-to-candidate-planner", "passed": len(checks), "failed": 0, "checks": checks}, indent=2))
