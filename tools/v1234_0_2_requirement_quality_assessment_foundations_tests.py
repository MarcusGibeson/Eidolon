from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import execution_outcome_reflection_learning_integration as outcomes
import requirement_quality_assessment as quality
import resource_concurrency_governance as resource
from v1234_quality_fixture import build_quality_fixture, clone_runtime, evidence_spec, requirement_spec

checks: list[bool] = []
def check(value): checks.append(bool(value))

def tree_signature():
    rows=[]
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            rows.append(f"{path.relative_to(ROOT).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), len(rows)

before=tree_signature()
fixture=build_quality_fixture("v1234-foundations")
base=fixture["runtime"]
ra=fixture["resource_assessment"]
rr=fixture["resource_review"]

def prepare(rt, req=None, ev=None, **kwargs):
    return quality.prepare_requirement_quality_assessment(
        kwargs.pop("resource_assessment_id", ra["assessment_id"]),
        expected_resource_assessment_digest=kwargs.pop("resource_assessment_digest", ra["assessment_digest"]),
        resource_review_id=kwargs.pop("resource_review_id", rr["review_id"]),
        expected_resource_review_digest=kwargs.pop("resource_review_digest", rr["review_digest"]),
        requirements=requirement_spec() if req is None else req,
        evidence=evidence_spec() if ev is None else ev,
        runtime_root=rt,
        **kwargs,
    )

contract=quality.build_requirement_quality_assessment_contract()
check(contract.get("ok"))
check(contract.get("contract_version")=="v1234.8")
check(contract.get("milestone_name")=="Requirement and Quality Assessment")
check(set(quality.CLASSIFICATIONS)==set(contract.get("classifications") or []))
check(set(quality.REVIEW_DISPOSITIONS)==set(contract.get("review_dispositions") or []))
for key, expected in quality.AUTHORITY_FLAGS.items(): check(contract.get(key) is expected)

# Fully satisfied exact assessment.
rt=clone_runtime(base,"v1234-foundation-satisfied")
row=prepare(rt)
check(row.get("ok"))
check(row.get("status")=="requirement_quality_assessment_ready_for_operator_review")
check(row.get("subject_kind")=="active_or_paused_session")
check(row.get("overall_assessment_state")=="requirements_satisfied_pending_operator_review")
check(row.get("all_required_requirements_satisfied") is True)
check(row.get("classification_counts")=={"satisfied":5})
check(row.get("rollback_expectation_present") is True)
check(row.get("goal_alignment_expectation_present") is True)
check(row.get("remediation_proposal_required") is False)
check(row.get("remaining_quality_risk_count")==0)
check(row.get("assessment_digest") and len(row["assessment_digest"])==64)
check(row.get("requirement_quality_assessment_record_digest") and len(row["requirement_quality_assessment_record_digest"])==64)
check(all("requirement_code" not in item for item in row.get("requirements") or []))
for key, expected in quality.AUTHORITY_FLAGS.items(): check(row.get(key) is expected)
for key in ("provider_contacted","commands_executed","tests_executed","project_modified","queue_modified","schedule_modified","requirements_modified","cognition_written","hidden_retry_created"):
    check(row.get(key) is False)

# Deterministic replay before review.
replay=prepare(rt)
check(replay.get("ok"))
check(replay.get("operation_status")=="replayed")
check(replay.get("assessment_id")==row.get("assessment_id"))
check(replay.get("assessment_digest")==row.get("assessment_digest"))
changed=prepare(rt, ev=evidence_spec({"performance_budget":"partial"}))
check(changed.get("ok") is False)
check(changed.get("status")=="requirement_quality_pending_review")

# Classification matrix.
cases=(
    ({"core_behavior":"partial"}, "requirements_partially_verified", "partially_satisfied", "close_partial_coverage"),
    ({"core_behavior":"contradicts"}, "requirements_not_met", "unsatisfied", "repair_unsatisfied_requirements"),
    ({"core_behavior":"missing"}, "requirements_not_met", "blocked_by_missing_evidence", "collect_missing_evidence"),
    ({"core_behavior":"stale"}, "requirements_not_met", "blocked_by_missing_evidence", "collect_missing_evidence"),
    ({"performance_budget":"missing"}, "requirements_satisfied_pending_operator_review", "unverified", "clarify_or_verify_requirements"),
    ({"performance_budget":"out_of_scope"}, "requirements_satisfied_pending_operator_review", "out_of_scope", None),
)
for index,(states,overall,classification,remediation) in enumerate(cases):
    case=prepare(clone_runtime(base,f"v1234-class-{index}"),ev=evidence_spec(states))
    check(case.get("ok"))
    check(case.get("overall_assessment_state")==overall)
    check((case.get("classification_counts") or {}).get(classification)==1)
    if remediation: check(remediation in (case.get("remediation_proposal_codes") or []))
    else: check(remediation not in (case.get("remediation_proposal_codes") or []))

# Contradictory supporting and contradicting evidence.
ev=evidence_spec()
extra=dict(ev[0]); extra["state"]="contradicts"; extra["evidence_digest"]="b"*64; extra["source_digest"]="c"*64
ev.append(extra)
contradictory=prepare(clone_runtime(base,"v1234-contradictory"),ev=ev)
check(contradictory.get("ok"))
check(contradictory.get("overall_assessment_state")=="requirements_not_met")
check((contradictory.get("classification_counts") or {}).get("contradictory")==1)
check("resolve_contradictory_evidence" in (contradictory.get("remediation_proposal_codes") or []))

# Ambiguous required criterion stays unverified and visible.
ambiguous=prepare(clone_runtime(base,"v1234-ambiguous"),req=requirement_spec(ambiguous=True))
check(ambiguous.get("ok"))
check(ambiguous.get("ambiguous_criterion_count")==1)
check(ambiguous.get("overall_assessment_state")=="requirements_partially_verified")
check((ambiguous.get("classification_counts") or {}).get("unverified")==1)

# Optional sealed outcome lineage is supported without granting outcome authority.
outcome_rt=clone_runtime(base,"v1234-outcome")
outcome=outcomes.prepare_execution_outcome(
    fixture["launch"]["launch_id"], outcome_type="inconclusive",
    expected_launch_digest=fixture["launch"]["launch_digest"],
    expected_monitor_digest=fixture["monitor"]["monitor_digest"],
    expected_control_digest=fixture["control"]["control_digest"], runtime_root=outcome_rt,
)
check(outcome.get("ok"))
outcome_assessment=prepare(outcome_rt,outcome_id=outcome["outcome_id"],expected_outcome_digest=outcome["outcome_digest"])
check(outcome_assessment.get("ok"))
check(outcome_assessment.get("subject_kind")=="sealed_execution_outcome")
check(outcome_assessment.get("outcome_type")=="inconclusive")
check(outcome_assessment.get("outcome_digest")==outcome.get("outcome_digest"))

# Invalid bounded specifications fail closed.
invalid_cases=[]
invalid_cases.append(([], evidence_spec()))
dup=requirement_spec(); dup.append(dict(dup[0])); invalid_cases.append((dup,evidence_spec()))
bad=requirement_spec(); bad[0]={**bad[0],"category":"mystery"}; invalid_cases.append((bad,evidence_spec()))
bad=requirement_spec(); bad[0]={**bad[0],"priority":"critical"}; invalid_cases.append((bad,evidence_spec()))
bad=requirement_spec(); bad[0]={**bad[0],"criterion_state":"unknown"}; invalid_cases.append((bad,evidence_spec()))
bad=requirement_spec(); bad[0]={**bad[0],"criterion_digest":"short"}; invalid_cases.append((bad,evidence_spec()))
bad_ev=evidence_spec(); bad_ev[0]={**bad_ev[0],"requirement_code":"not_declared"}; invalid_cases.append((requirement_spec(),bad_ev))
bad_ev=evidence_spec(); bad_ev[0]={**bad_ev[0],"evidence_type":"shell_output"}; invalid_cases.append((requirement_spec(),bad_ev))
bad_ev=evidence_spec(); bad_ev[0]={**bad_ev[0],"state":"passed"}; invalid_cases.append((requirement_spec(),bad_ev))
bad_ev=evidence_spec(); bad_ev[0]={**bad_ev[0],"evidence_digest":"bad"}; invalid_cases.append((requirement_spec(),bad_ev))
bad_ev=evidence_spec(); bad_ev.append(dict(bad_ev[0])); invalid_cases.append((requirement_spec(),bad_ev))
for index,(reqs,evidence) in enumerate(invalid_cases):
    blocked=prepare(clone_runtime(base,f"v1234-invalid-{index}"),req=reqs,ev=evidence)
    check(blocked.get("ok") is False)
    check(blocked.get("status")=="requirement_quality_assessment_blocked")
    check(blocked.get("test_execution_authorized") is False)

# Exact stale lineage closes.
for index,kwargs in enumerate((
    {"resource_assessment_digest":"0"*64}, {"resource_review_digest":"0"*64},
    {"resource_assessment_id":"resource_assessment_"+"0"*24},
    {"resource_review_id":"resource_review_"+"0"*24},
)):
    blocked=prepare(clone_runtime(base,f"v1234-stale-{index}"),**kwargs)
    check(blocked.get("ok") is False)
    check("blocked" in str(blocked.get("status")))

# Public records suppress raw requirement codes and runtime paths.
public=quality.public_requirement_quality_assessments(runtime_root=rt)
encoded=json.dumps(public,sort_keys=True)
check(public.get("ok"))
check(public.get("assessment_count")==1)
check(str(rt) not in encoded)
check("core_behavior" not in encoded)
check("acceptance_gate" not in encoded)
check(public.get("private_content_exposed") is False)
check(public.get("raw_test_output_exposed") is False)

# Exact prior receipts and source remain immutable.
lineage=(
    resource._assessment_path(ra["assessment_id"], base),
    resource._review_path(rr["review_id"], base),
)
lineage_before={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in lineage}
_ = prepare(clone_runtime(base,"v1234-immutability"))
check(lineage_before=={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in lineage})
check(before==tree_signature())

print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
