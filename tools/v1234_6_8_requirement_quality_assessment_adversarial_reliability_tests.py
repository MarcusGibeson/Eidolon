from __future__ import annotations

import hashlib
import importlib
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/"conscious_agent",ROOT/"tools"):
    if str(value) not in sys.path: sys.path.insert(0,str(value))

import execution_outcome_reflection_learning_integration as outcomes
import live_execution_monitoring_operator_intervention as monitoring
import requirement_quality_assessment as quality
import resource_concurrency_governance as resource
from v1234_quality_fixture import build_quality_fixture,clone_runtime,evidence_spec,requirement_spec

checks=[]
def check(value): checks.append(bool(value))

def tree_signature():
    rows=[]
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc",".pyo"}:
            rows.append(f"{path.relative_to(ROOT).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(),len(rows)

before=tree_signature()
fixture=build_quality_fixture("v1234-reliability")
base=fixture["runtime"]; ra=fixture["resource_assessment"]; rr=fixture["resource_review"]

def prepare(rt,req=None,ev=None,**kwargs):
    return quality.prepare_requirement_quality_assessment(
        kwargs.pop("resource_assessment_id",ra["assessment_id"]),
        expected_resource_assessment_digest=kwargs.pop("resource_assessment_digest",ra["assessment_digest"]),
        resource_review_id=kwargs.pop("resource_review_id",rr["review_id"]),
        expected_resource_review_digest=kwargs.pop("resource_review_digest",rr["review_digest"]),
        requirements=requirement_spec() if req is None else req,
        evidence=evidence_spec() if ev is None else ev,
        runtime_root=rt,**kwargs,
    )

# Determinism across independent runtime clones.
a=prepare(clone_runtime(base,"v1234-deterministic-a"))
b=prepare(clone_runtime(base,"v1234-deterministic-b"))
check(a.get("ok") and b.get("ok"))
check(a.get("assessment_id")==b.get("assessment_id"))
check(a.get("assessment_digest")==b.get("assessment_digest"))
check(a.get("requirement_spec_digest")==b.get("requirement_spec_digest"))
check(a.get("evidence_spec_digest")==b.get("evidence_spec_digest"))

# Restart-safe replay through module reload.
restart_rt=clone_runtime(base,"v1234-restart")
first=prepare(restart_rt)
importlib.reload(quality)
replayed=prepare(restart_rt)
check(first.get("ok") and replayed.get("ok"))
check(replayed.get("operation_status")=="replayed")
check(replayed.get("assessment_id")==first.get("assessment_id"))

# Assessment tampering closes inspection and review.
tamper_rt=clone_runtime(base,"v1234-assessment-tamper")
assessment=prepare(tamper_rt)
path=quality._assessment_path(assessment["assessment_id"],tamper_rt)
raw=json.loads(path.read_text()); raw["overall_assessment_state"]="requirements_satisfied_pending_operator_review" if raw["overall_assessment_state"]!="requirements_satisfied_pending_operator_review" else "requirements_not_met"; path.write_text(json.dumps(raw,sort_keys=True))
loaded=quality.load_requirement_quality_assessment(assessment["assessment_id"],runtime_root=tamper_rt)
reviewed=quality.review_requirement_quality_assessment(assessment["assessment_id"],expected_assessment_digest=assessment["assessment_digest"],disposition="hold",runtime_root=tamper_rt)
check(loaded.get("ok") is False)
check(loaded.get("status")=="requirement_quality_assessment_integrity_blocked")
check(reviewed.get("ok") is False)
check(reviewed.get("status")=="requirement_quality_review_integrity_blocked")
check(quality.public_requirement_quality_assessments(runtime_root=tamper_rt).get("assessment_count")==0)

# Review tampering closes replay and public listing.
review_tamper_rt=clone_runtime(base,"v1234-review-tamper")
assessment=prepare(review_tamper_rt)
review=quality.review_requirement_quality_assessment(assessment["assessment_id"],expected_assessment_digest=assessment["assessment_digest"],disposition="hold",runtime_root=review_tamper_rt)
path=quality._review_path(review["review_id"],review_tamper_rt)
raw=json.loads(path.read_text()); raw["work_approved"]=True; path.write_text(json.dumps(raw,sort_keys=True))
loaded=quality.load_requirement_quality_assessment_review(review["review_id"],runtime_root=review_tamper_rt)
replay=quality.review_requirement_quality_assessment(assessment["assessment_id"],expected_assessment_digest=assessment["assessment_digest"],disposition="hold",runtime_root=review_tamper_rt)
check(loaded.get("ok") is False)
check(replay.get("ok") is False)
check(replay.get("status")=="requirement_quality_review_history_integrity_blocked")
check(quality.public_requirement_quality_assessment_reviews(runtime_root=review_tamper_rt).get("review_count")==0)

# Resource assessment and review tampering close new assessments and later reviews.
resource_tamper_rt=clone_runtime(base,"v1234-resource-tamper")
path=resource._assessment_path(ra["assessment_id"],resource_tamper_rt)
raw=json.loads(path.read_text()); raw["resource_lease_created"]=True; path.write_text(json.dumps(raw,sort_keys=True))
blocked=prepare(resource_tamper_rt)
check(blocked.get("ok") is False)
check(blocked.get("status")=="requirement_quality_assessment_blocked")

resource_review_tamper_rt=clone_runtime(base,"v1234-resource-review-tamper")
assessment=prepare(resource_review_tamper_rt)
path=resource._review_path(rr["review_id"],resource_review_tamper_rt)
raw=json.loads(path.read_text()); raw["admission_confirmed"]=False; path.write_text(json.dumps(raw,sort_keys=True))
blocked_review=quality.review_requirement_quality_assessment(assessment["assessment_id"],expected_assessment_digest=assessment["assessment_digest"],disposition="hold",runtime_root=resource_review_tamper_rt)
check(blocked_review.get("ok") is False)
check(blocked_review.get("status")=="requirement_quality_review_blocked")

# Current monitor drift blocks active-session assessment rather than accepting stale test evidence.
drift_rt=clone_runtime(base,"v1234-monitor-drift")
progress=monitoring.record_live_execution_progress(
    fixture["launch"]["launch_id"],expected_launch_digest=fixture["launch"]["launch_digest"],
    event_type="progress_updated",current_stage="provider_step_active",completed_units=1,total_units=3,
    blocker_codes=[],risk_codes=["test_coverage_gap"],operator_attention_required=False,runtime_root=drift_rt,
)
check(progress.get("ok"))
blocked=prepare(drift_rt)
check(blocked.get("ok") is False)
check(blocked.get("status")=="requirement_quality_stale_monitor_digest")

# Stale evidence never becomes a full pass even when paired with support.
stale_ev=evidence_spec(); extra=dict(stale_ev[0]); extra["state"]="stale"; extra["evidence_digest"]="d"*64; extra["source_digest"]="e"*64; stale_ev.append(extra)
stale_assessment=prepare(clone_runtime(base,"v1234-stale-evidence"),ev=stale_ev)
check(stale_assessment.get("ok"))
check(stale_assessment.get("overall_assessment_state")=="requirements_partially_verified")
check((stale_assessment.get("classification_counts") or {}).get("partially_satisfied")==1)
check(stale_assessment.get("all_required_requirements_satisfied") is False)

# Contradiction cannot be hidden behind larger supporting evidence volume.
contradict_ev=evidence_spec()
for index in range(4):
    extra=dict(contradict_ev[0]); extra["evidence_type"]="inspection" if index%2 else "static_analysis"; extra["evidence_digest"]=("a" if index<2 else "b")*64; extra["source_digest"]=("c" if index<2 else "d")*64
    if index==3: extra["state"]="contradicts"
    # avoid exact duplicate tuples
    extra["evidence_digest"]=f"{index+6:x}"*64
    contradict_ev.append(extra)
contradiction=prepare(clone_runtime(base,"v1234-volume-contradiction"),ev=contradict_ev)
check(contradiction.get("ok"))
check((contradiction.get("classification_counts") or {}).get("contradictory")==1)
check(contradiction.get("overall_assessment_state")=="requirements_not_met")

# Sealed outcome digest, record integrity, and cross-session lineage are exact.
outcome_rt=clone_runtime(base,"v1234-outcome-reliability")
outcome=outcomes.prepare_execution_outcome(
    fixture["launch"]["launch_id"],outcome_type="inconclusive",
    expected_launch_digest=fixture["launch"]["launch_digest"],expected_monitor_digest=fixture["monitor"]["monitor_digest"],
    expected_control_digest=fixture["control"]["control_digest"],runtime_root=outcome_rt,
)
check(outcome.get("ok"))
stale=prepare(outcome_rt,outcome_id=outcome["outcome_id"],expected_outcome_digest="0"*64)
check(stale.get("ok") is False)
check(stale.get("status")=="requirement_quality_outcome_lineage_blocked")
path=outcomes._outcome_path(outcome["outcome_id"],outcome_rt)
raw=json.loads(path.read_text()); raw["evidence_complete"]=not bool(raw.get("evidence_complete")); path.write_text(json.dumps(raw,sort_keys=True))
tampered=prepare(outcome_rt,outcome_id=outcome["outcome_id"],expected_outcome_digest=outcome["outcome_digest"])
check(tampered.get("ok") is False)
check(tampered.get("status")=="requirement_quality_outcome_lineage_blocked")

other=build_quality_fixture("v1234-other-session")
other_outcome=outcomes.prepare_execution_outcome(
    other["launch"]["launch_id"],outcome_type="inconclusive",
    expected_launch_digest=other["launch"]["launch_digest"],expected_monitor_digest=other["monitor"]["monitor_digest"],
    expected_control_digest=other["control"]["control_digest"],runtime_root=other["runtime"],
)
# Copy foreign sealed outcome into primary runtime to test cross-session closure.
foreign_rt=clone_runtime(base,"v1234-foreign-outcome")
src=outcomes._outcome_path(other_outcome["outcome_id"],other["runtime"]); dst=outcomes._outcome_path(other_outcome["outcome_id"],foreign_rt); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())
foreign=prepare(foreign_rt,outcome_id=other_outcome["outcome_id"],expected_outcome_digest=other_outcome["outcome_digest"])
check(foreign.get("ok") is False)
check(foreign.get("status")=="requirement_quality_cross_session_outcome_blocked")

# Bounded limits close before writing records.
too_many=requirement_spec()*7
blocked=prepare(clone_runtime(base,"v1234-too-many-requirements"),req=too_many)
check(blocked.get("ok") is False)
check(blocked.get("status")=="requirement_quality_assessment_blocked")
too_much=evidence_spec()*20
blocked=prepare(clone_runtime(base,"v1234-too-much-evidence"),ev=too_much)
check(blocked.get("ok") is False)
check(blocked.get("status")=="requirement_quality_assessment_blocked")

# Old stale lock is recovered, but creates no background retry or authority.
lock_rt=clone_runtime(base,"v1234-stale-lock")
lock=quality._root(lock_rt)/"locks"/"requirement-quality-assessment.lock"; lock.mkdir(parents=True,exist_ok=True); (lock/"owner").write_text("999999"); old=time.time()-120; import os; os.utime(lock,(old,old))
recovered=prepare(lock_rt)
check(recovered.get("ok"))
check(not lock.exists())
check(recovered.get("hidden_retry_created") is False)
check(recovered.get("background_execution_authorized") is False)

# Review after session evidence changes remains historical interpretation only.
historical_rt=clone_runtime(base,"v1234-historical-review")
historical=prepare(historical_rt)
_ = monitoring.record_live_execution_progress(
    fixture["launch"]["launch_id"],expected_launch_digest=fixture["launch"]["launch_digest"],event_type="progress_reported",
    current_stage="testing",completed_units=2,total_units=3,blocker_codes=[],risk_codes=[],operator_attention_required=False,runtime_root=historical_rt,
)
historical_review=quality.review_requirement_quality_assessment(historical["assessment_id"],expected_assessment_digest=historical["assessment_digest"],disposition="accept_assessment",runtime_root=historical_rt)
check(historical_review.get("ok"))
check(historical_review.get("work_approved") is False)
check(historical_review.get("assessment_is_execution_authority") is False)
check(historical_review.get("test_execution_authorized") is False)

# Privacy suppression is retained under unusual evidence combinations.
privacy_rt=clone_runtime(base,"v1234-privacy")
privacy=prepare(privacy_rt,ev=evidence_spec({"core_behavior":"contradicts","performance_budget":"out_of_scope"}))
public=quality.public_requirement_quality_assessments(runtime_root=privacy_rt)
encoded=json.dumps(public,sort_keys=True)
check(privacy.get("ok"))
check(str(privacy_rt) not in encoded)
for raw_code in ("core_behavior","acceptance_gate","rollback_safety","goal_fit","performance_budget"):
    check(raw_code not in encoded)
for key in ("private_request_exposed","private_path_exposed","private_content_exposed","project_name_exposed","raw_provider_output_exposed","raw_test_output_exposed"):
    check(public.get(key) is False)

# No test or mutation side effects are ever inferred from evidence states.
for states in (
    {"core_behavior":"supports"},{"core_behavior":"partial"},{"core_behavior":"contradicts"},
    {"core_behavior":"missing"},{"core_behavior":"stale"},{"core_behavior":"inconclusive"},
):
    row=prepare(clone_runtime(base,"v1234-authority-"+states["core_behavior"]),ev=evidence_spec(states))
    check(row.get("ok"))
    for key in ("tests_executed","commands_executed","provider_contacted","project_modified","requirements_modified","queue_modified","schedule_modified","cognition_written"):
        check(row.get(key) is False)
    for key in ("test_execution_authorized","command_execution_authorized","project_mutation_authorized","requirement_mutation_authorized","acceptance_authorized","apply_authorized","old_authority_reusable"):
        check(row.get(key) is False)

check(before==tree_signature())
print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
