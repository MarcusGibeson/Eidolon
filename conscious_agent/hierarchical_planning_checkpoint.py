from __future__ import annotations

"""Strictly read-only v1171.9 Hierarchical Planning checkpoint."""

from copy import deepcopy
import hashlib, json, os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from hierarchical_planning_runtime import CONTRACT_VERSION as PLANNING_CONTRACT_VERSION, REVIEW_CONTRACT_VERSION, RELIABILITY_CONTRACT_VERSION, MAX_COMPONENT_BYTES, MAX_PRIOR_RECEIPTS, MAX_MILESTONES, MAX_DEPENDENCIES, MAX_REVIEW_PROMPT_CHARS, MAX_RELIABILITY_FAULTS, build_hierarchical_planning_projection, build_hierarchical_planning_review_handoff, build_hierarchical_planning_review_projection, build_hierarchical_planning_reliability, validate_prior_hierarchical_planning_receipts, verify_hierarchical_planning_review_handoff, verify_hierarchical_planning_review_state, verify_hierarchical_planning_review_packet, verify_hierarchical_planning_diagnostics_strict, verify_hierarchical_planning_reliability
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1171.9"
_CHECKPOINT_ID = "hierarchical-planning:v1171.9"
_EXCLUDED = {"data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports"}
_FORBIDDEN = ("PLAN_PRIVATE_CANARY", "GOAL_PRIVATE_CANARY", "<system>", "approve and execute", "private reasoning")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _tree_signature(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    paths=[]
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _EXCLUDED]
        for name in files:
            p=Path(base)/name
            if p.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(p)
    for p in sorted(paths):
        try:
            rel=p.relative_to(root).as_posix(); data=p.read_bytes()
        except OSError:
            continue
        h.update(rel.encode()); h.update(b"\0"); h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def _goal(candidate_type: str = "reliability_improvement", evidence_count: int = 2) -> tuple[dict[str, Any], dict[str, Any]]:
    return ({
        "policy": {"candidate_available": True, "operator_review_required": True, "goal_activation_permitted": False, "plan_creation_permitted": False},
        "candidate": {"candidate_type": candidate_type, "scope_band": "system"},
        "evidence": {"candidate_evidence_count": evidence_count},
    }, {"reliability_posture": "goal_candidate_context_reliable", "candidate_available": True})


def _projection(*, candidate_type: str = "reliability_improvement", evidence_count: int = 2, prior: object = (), constraints: object = None) -> dict[str, Any]:
    goal, rel = _goal(candidate_type, evidence_count)
    kwargs={"prior_planning_receipts": prior}
    if constraints is not None:
        kwargs["protected_operator_constraints"] = constraints
    return build_hierarchical_planning_projection(goal, rel, **kwargs)


def _case_summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    policy=projection.get("policy") if isinstance(projection.get("policy"), Mapping) else {}
    hierarchy=projection.get("hierarchy") if isinstance(projection.get("hierarchy"), Mapping) else {}
    diagnostics=projection.get("diagnostics") if isinstance(projection.get("diagnostics"), Mapping) else {}
    return {
        "planning_posture": str(policy.get("planning_posture") or ""),
        "candidate_type": str(hierarchy.get("candidate_type") or "none"),
        "plan_candidate_available": bool(hierarchy.get("plan_candidate_available")),
        "hierarchy_depth": int(hierarchy.get("hierarchy_depth") or 0),
        "milestone_count": int(hierarchy.get("milestone_count") or 0),
        "dependency_count": int(hierarchy.get("dependency_count") or 0),
        "stopping_condition_count": int(hierarchy.get("stopping_condition_count") or 0),
        "policy_recovered": bool(policy.get("policy_recovered")),
        "diagnostics_valid": verify_hierarchical_planning_diagnostics_strict(diagnostics),
        "authority": str(policy.get("authority") or ""),
        "content_free": bool(policy.get("content_free")),
    }


def build_hierarchical_planning_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime=Path(runtime_root or source/"data").resolve()
    source_before=_tree_signature(source); runtime_before=_tree_signature(runtime)
    checks: list[bool]=[]
    def require(value: object) -> None: checks.append(bool(value))

    no_plan=build_hierarchical_planning_projection({}, {})
    emerging=_projection()
    capability=_projection(candidate_type="capability_improvement", evidence_count=1)
    handoff=build_hierarchical_planning_review_handoff(emerging, provider_completed=True, assistant_memory_committed=True)
    stable=_projection(prior=[{"hierarchical_planning_review_handoff": handoff}])
    replay=_projection(prior=[{"hierarchical_planning_review_handoff": handoff}]*3)
    tampered=deepcopy(handoff); tampered["milestone_count"] += 1
    recovered=_projection(prior=[{"hierarchical_planning_review_handoff": tampered}])
    missing_constraints=_projection(constraints=("literal_current_request_precedence",))

    projection_cases={k:_case_summary(v) for k,v in {
        "no_plan":no_plan, "emerging":emerging, "capability":capability,
        "stable":stable, "replay":replay, "tampered_recovery":recovered,
        "missing_constraints":missing_constraints,
    }.items()}
    for row in projection_cases.values():
        require(row["authority"] in {"none", ""}); require(row["content_free"] or not row["plan_candidate_available"])
        require(row["milestone_count"] <= MAX_MILESTONES); require(row["dependency_count"] <= MAX_DEPENDENCIES)
    require(not projection_cases["no_plan"]["plan_candidate_available"])
    require(projection_cases["emerging"]["plan_candidate_available"])
    require(projection_cases["stable"]["plan_candidate_available"])
    require(projection_cases["tampered_recovery"]["policy_recovered"])
    require(not projection_cases["tampered_recovery"]["plan_candidate_available"])
    require(projection_cases["missing_constraints"]["policy_recovered"])

    reviews={name:build_hierarchical_planning_review_projection(value) for name,value in {
        "emerging":emerging,"stable":stable,"replay":replay,"recovered":recovered,"none":no_plan,
    }.items()}
    review_summaries={}
    for name, value in reviews.items():
        state=value["state"]; packet=value["review_packet"]
        valid_state=verify_hierarchical_planning_review_state(state); valid_packet=verify_hierarchical_planning_review_packet(packet)
        review_summaries[name]={
            "state_valid":valid_state,"packet_valid":valid_packet,
            "review_disposition":state.get("review_disposition"),
            "candidate_available":packet.get("plan_candidate_available"),
            "verified_prior_receipt_count":state.get("verified_prior_receipt_count"),
            "replayed_prior_receipt_count":state.get("replayed_prior_receipt_count"),
        }
        require(valid_state); require(valid_packet); require(packet.get("authority")=="none"); require(packet.get("content_free") is True)
        require(all(packet.get(k) is False for k in ("plan_activated","plan_persisted","schedule_created","tool_routed","action_executed","source_edited","autonomous_work_started")))
    require(review_summaries["stable"]["review_disposition"]=="stable_plan_review")
    require(review_summaries["replay"]["verified_prior_receipt_count"]==1)
    require(review_summaries["replay"]["replayed_prior_receipt_count"]==2)
    require(not review_summaries["recovered"]["candidate_available"])

    handoffs={
        "before_provider":build_hierarchical_planning_review_handoff(emerging,provider_completed=False,assistant_memory_committed=False),
        "before_memory":build_hierarchical_planning_review_handoff(emerging,provider_completed=True,assistant_memory_committed=False),
        "completed":handoff,
    }
    handoff_summaries={}
    for name,row in handoffs.items():
        valid=verify_hierarchical_planning_review_handoff(row)
        handoff_summaries[name]={"valid":valid,"eligible":bool(row.get("eligible_for_review_continuity"))}
        require(valid); require(row.get("plan_activated") is False); require(row.get("action_executed") is False)
    require(not handoff_summaries["before_provider"]["eligible"]); require(not handoff_summaries["before_memory"]["eligible"]); require(handoff_summaries["completed"]["eligible"])

    reliabilities={
        "reliable":build_hierarchical_planning_reliability(emerging,reviews["emerging"]),
        "replayed":build_hierarchical_planning_reliability(replay,reviews["replay"],prior_planning_receipts=[{"hierarchical_planning_review_handoff":handoff}]*3),
        "tampered":build_hierarchical_planning_reliability(recovered,reviews["recovered"]),
        "flood":build_hierarchical_planning_reliability(emerging,reviews["emerging"],prior_planning_receipts=[{"hierarchical_planning_review_handoff":{"x":str(i)}} for i in range(MAX_PRIOR_RECEIPTS+1)]),
    }
    reliability_summaries={}
    for name,value in reliabilities.items():
        report=value["report"]; valid=verify_hierarchical_planning_reliability(report)
        reliability_summaries[name]={"valid":valid,"ready":report.get("ordinary_conversation_ready"),"fault_count":report.get("fault_count"),"receipt_budget_exceeded":report.get("receipt_budget_exceeded"),"review_available":report.get("review_available")}
        require(valid); require(report.get("authority")=="none"); require(report.get("content_free") is True); require(report.get("fault_count",99)<=MAX_RELIABILITY_FAULTS)
    require(reliability_summaries["reliable"]["ready"])
    require(reliability_summaries["replayed"]["ready"])
    require(not reliability_summaries["tampered"]["ready"])
    require(reliability_summaries["flood"]["receipt_budget_exceeded"])
    require(not reliability_summaries["flood"]["review_available"])

    receipt_summary=validate_prior_hierarchical_planning_receipts([{"hierarchical_planning_review_handoff":handoff}]*2)
    require(receipt_summary["verified_receipt_count"]==1); require(receipt_summary["replayed_receipt_count"]==1)
    require(verify_hierarchical_planning_review_handoff(handoff)); require(not verify_hierarchical_planning_review_handoff(tampered))

    forged=deepcopy(reviews["emerging"]["review_packet"]); forged["approved"]=True; forged.pop("review_packet_digest",None); forged["review_packet_digest"]=_digest(forged)
    require(not verify_hierarchical_planning_review_packet(forged))
    bad_diag=deepcopy(emerging["diagnostics"]); bad_diag["approved"]=True
    require(not verify_hierarchical_planning_diagnostics_strict(bad_diag))
    bad_rel=deepcopy(reliabilities["reliable"]["report"]); bad_rel["plan_activated"]=True; bad_rel["reliability_digest"]=_digest({k:v for k,v in bad_rel.items() if k!="reliability_digest"})
    require(not verify_hierarchical_planning_reliability(bad_rel))

    registry=inspect_checkpoint_registry(source_root=source)
    privacy=package_privacy_summary_for_root(source)
    require(not registry.get("duplicate_checkpoint_ids")); require(not registry.get("duplicate_builder_targets"))
    require(privacy.get("forbidden_entry_count",0)==0); require(privacy.get("private_content_finding_count",0)==0)
    require(source_before==_tree_signature(source)); require(runtime_before==_tree_signature(runtime))

    evidence={"projection_summaries":projection_cases,"review_summaries":review_summaries,"handoff_summaries":handoff_summaries,"reliability_summaries":reliability_summaries,"receipt_summary":receipt_summary}
    text=json.dumps(evidence,sort_keys=True,default=str)
    forbidden_count=sum(text.count(token) for token in _FORBIDDEN)
    require(forbidden_count==0)

    report={
        "contract_version":CONTRACT_VERSION,"checkpoint_id":_CHECKPOINT_ID,
        "ok":all(checks),"passed":sum(checks),"total":len(checks),"read_only":True,"post_available":False,
        "content_free":forbidden_count==0,"authority_preserved":True,"operator_promotion_required":True,
        "desktop_verification_deferred_until_v1200":True,"hierarchical_planning_checkpoint_completed":True,
        "hierarchy_review_continuity_and_reliability_consolidated":True,"historical_v1134_planning_governance_preserved":True,
        "literal_current_request_precedence_preserved":True,"goal_activation_not_started":True,
        "plan_activation_not_started":True,"plan_persistence_not_started":True,"plan_execution_not_started":True,
        "simulation_and_risk_comparison_not_started":True,"tools_and_actions_not_started":True,
        "uncontrolled_self_training_not_started":True,"model_training_not_started":True,"model_weights_unchanged":True,
        "automatic_memory_mutation_not_started":True,"automatic_lesson_commit_not_started":True,
        "goal_created":False,"goal_activated":False,"plan_created":False,"plan_activated":False,"plan_persisted":False,
        "schedule_created":False,"tool_routed":False,"tool_executed":False,"action_executed":False,"source_edit_performed":False,
        "approval_granted":False,"memory_mutated":False,"lesson_committed":False,"model_training_performed":False,
        "model_weights_changed":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,
        "provider_contacted":False,"proactive_turn_created":False,"forbidden_report_value_count":forbidden_count,
        "summary":{
            "synthetic_contract_check_count":len(checks),"projection_case_count":len(projection_cases),"review_case_count":len(reviews),
            "handoff_case_count":len(handoffs),"reliability_case_count":len(reliabilities),"receipt_case_count":2,
            "registered_checkpoint_count":registry.get("checkpoint_count",0),"component_maximum_bytes":MAX_COMPONENT_BYTES,
            "prior_receipt_maximum_count":MAX_PRIOR_RECEIPTS,"milestone_maximum_count":MAX_MILESTONES,
            "dependency_maximum_count":MAX_DEPENDENCIES,"review_prompt_maximum_chars":MAX_REVIEW_PROMPT_CHARS,
            "reliability_fault_maximum_count":MAX_RELIABILITY_FAULTS,"authoritative_conversation_path_count":2,
            "open_limitation_count":6,"privacy_forbidden_entry_count":privacy.get("forbidden_entry_count",0),
            "privacy_content_finding_count":privacy.get("private_content_finding_count",0),
        },
        "evidence":{"synthetic_contracts":evidence},
        "source_modified":False,"runtime_mutated":False,
        "planning_contract_version":PLANNING_CONTRACT_VERSION,"review_contract_version":REVIEW_CONTRACT_VERSION,
        "reliability_contract_version":RELIABILITY_CONTRACT_VERSION,
    }
    report["structural_digest"]=_digest(report)
    return report
