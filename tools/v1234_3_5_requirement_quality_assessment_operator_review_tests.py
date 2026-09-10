from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import execution_session_pause_resume_cancel_recovery as control
import requirement_quality_assessment as quality
from conscious_agent.api_server import handle_api_get
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1234_quality_fixture import build_quality_fixture, clone_runtime, evidence_spec, requirement_spec

checks=[]
def check(value): checks.append(bool(value))

def req_text(reqs):
    return ";".join(f"{r['code']}:{r['category']}:{r['priority']}:{r['criterion_state']}:{r['criterion_digest']}" for r in reqs)

def ev_text(rows):
    return ";".join(f"{r['requirement_code']}:{r['evidence_type']}:{r['state']}:{r['evidence_digest']}:{r['source_digest']}" for r in rows)

def exact_prepare(rt, *, reqs=None, evidence=None):
    reqs=reqs or requirement_spec(); evidence=evidence or evidence_spec()
    text=(
        f"Prepare requirement and quality assessment for resource assessment {ra['assessment_id']} digest {ra['assessment_digest']} "
        f"resource review {rr['review_id']} digest {rr['review_digest']} with requirements {req_text(reqs)} and evidence {ev_text(evidence)}."
    )
    return text, process_ordinary_chat_development_turn(text,runtime_root=rt)

fixture=build_quality_fixture("v1234-review")
base=fixture["runtime"]; ra=fixture["resource_assessment"]; rr=fixture["resource_review"]
launch=fixture["launch"]

# Exact ordinary-chat preparation and acceptance.
rt=clone_runtime(base,"v1234-review-chat")
text,turn=exact_prepare(rt)
row=turn.get("requirement_quality_assessment") or {}
check(turn.get("active") is True)
check(row.get("ok"))
check(row.get("overall_assessment_state")=="requirements_satisfied_pending_operator_review")
check("grants no work approval or execution authority" in turn.get("response","").lower())
state_before=control.inspect_execution_session_control(launch["launch_id"],runtime_root=rt,reconcile_runtime=False)
review_text=f"Review requirement and quality assessment accept assessment for assessment {row['assessment_id']} digest {row['assessment_digest']}."
review_turn=process_ordinary_chat_development_turn(review_text,runtime_root=rt)
review=review_turn.get("requirement_quality_assessment") or {}
state_after=control.inspect_execution_session_control(launch["launch_id"],runtime_root=rt,reconcile_runtime=False)
check(review_turn.get("active") is True)
check(review.get("ok"))
check(review.get("disposition")=="accept_assessment")
check(review.get("assessment_accepted_as_operator_interpretation") is True)
check(review.get("work_approved") is False)
check(review.get("project_change_applied") is False)
check(review.get("new_test_run_started") is False)
check(state_before.get("control_digest")==state_after.get("control_digest"))
check(state_after.get("session_state")=="active")
for key, expected in quality.AUTHORITY_FLAGS.items(): check(review.get(key) is expected)

# Review replay, conflict and stale digest closure.
replay=process_ordinary_chat_development_turn(review_text,runtime_root=rt).get("requirement_quality_assessment") or {}
check(replay.get("ok"))
check(replay.get("operation_status")=="replayed")
check(replay.get("review_id")==review.get("review_id"))
conflict=quality.review_requirement_quality_assessment(row["assessment_id"],expected_assessment_digest=row["assessment_digest"],disposition="hold",runtime_root=rt)
check(conflict.get("ok") is False)
check(conflict.get("status")=="requirement_quality_conflicting_review")
stale=quality.review_requirement_quality_assessment(row["assessment_id"],expected_assessment_digest="0"*64,disposition="accept_assessment",runtime_root=rt)
check(stale.get("ok") is False)
check(stale.get("status")=="requirement_quality_review_stale_assessment_digest")

# Independent exact review dispositions.
for index,decision in enumerate(("hold","reject","request_remediation","request_changes")):
    decision_rt=clone_runtime(base,f"v1234-review-{decision}")
    states={"core_behavior":"partial"} if decision=="request_remediation" else {}
    _,prepared=exact_prepare(decision_rt,evidence=evidence_spec(states))
    assessment=prepared.get("requirement_quality_assessment") or {}
    command=f"Review requirement and quality assessment {decision.replace('_',' ')} for assessment {assessment['assessment_id']} digest {assessment['assessment_digest']}."
    outcome=process_ordinary_chat_development_turn(command,runtime_root=decision_rt)
    reviewed=outcome.get("requirement_quality_assessment") or {}
    check(outcome.get("active") is True)
    check(reviewed.get("ok"))
    check(reviewed.get("disposition")==decision)
    check(reviewed.get("work_approved") is False)
    check(reviewed.get("test_execution_authorized") is False)
    check(reviewed.get("project_mutation_authorized") is False)
    check(reviewed.get("requirements_modified") is False)

# Incomplete evidence cannot be accepted, but remediation can be requested.
blocked_rt=clone_runtime(base,"v1234-review-blocked")
_,blocked_turn=exact_prepare(blocked_rt,evidence=evidence_spec({"core_behavior":"missing"}))
blocked=blocked_turn.get("requirement_quality_assessment") or {}
accept=quality.review_requirement_quality_assessment(blocked["assessment_id"],expected_assessment_digest=blocked["assessment_digest"],disposition="accept_assessment",runtime_root=blocked_rt)
check(blocked.get("overall_assessment_state")=="requirements_not_met")
check(accept.get("ok") is False)
check(accept.get("status")=="requirement_quality_acceptance_blocked")
remediate=quality.review_requirement_quality_assessment(blocked["assessment_id"],expected_assessment_digest=blocked["assessment_digest"],disposition="request_remediation",runtime_root=blocked_rt)
check(remediate.get("ok"))
check(remediate.get("remediation_requested") is True)
check("collect_missing_evidence" in (remediate.get("remediation_proposal_codes") or []))
check(remediate.get("remediation_proposal_is_execution_authority") is False)

# Fresh evidence after a completed review creates an append-only later generation.
fresh_rt=clone_runtime(base,"v1234-review-fresh")
_,first_turn=exact_prepare(fresh_rt,evidence=evidence_spec({"performance_budget":"missing"}))
first=first_turn.get("requirement_quality_assessment") or {}
held=quality.review_requirement_quality_assessment(first["assessment_id"],expected_assessment_digest=first["assessment_digest"],disposition="hold",runtime_root=fresh_rt)
check(held.get("ok"))
_,second_turn=exact_prepare(fresh_rt,evidence=evidence_spec({"performance_budget":"supports"}))
second=second_turn.get("requirement_quality_assessment") or {}
check(second.get("ok"))
check(second.get("generation")==2)
check(second.get("previous_assessment_id")==first.get("assessment_id"))
check(second.get("previous_assessment_digest")==first.get("assessment_digest"))
check(second.get("assessment_id")!=first.get("assessment_id"))

# Inspection, listings, CLI, and GET-only API return content-free projections.
inspect_rt=clone_runtime(base,"v1234-review-inspect")
_,inspect_turn=exact_prepare(inspect_rt)
assessment=inspect_turn.get("requirement_quality_assessment") or {}
show=process_ordinary_chat_development_turn(f"Show requirement and quality assessment {assessment['assessment_id']}.",runtime_root=inspect_rt)
check(show.get("active") is True)
check((show.get("requirement_quality_assessment") or {}).get("assessment_id")==assessment.get("assessment_id"))
listed=process_ordinary_chat_development_turn("Show requirement and quality assessments.",runtime_root=inspect_rt).get("requirement_quality_assessment") or {}
check(listed.get("ok"))
check(listed.get("assessment_count")==1)
quality.review_requirement_quality_assessment(assessment["assessment_id"],expected_assessment_digest=assessment["assessment_digest"],disposition="hold",runtime_root=inspect_rt)
reviews=process_ordinary_chat_development_turn("Show requirement and quality assessment reviews.",runtime_root=inspect_rt).get("requirement_quality_assessment") or {}
check(reviews.get("ok"))
check(reviews.get("review_count")==1)
for command,key in (("requirement-quality-assessments","assessment_count"),("requirement-quality-assessment-reviews","review_count")):
    proc=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),command,"--runtime-root",str(inspect_rt)],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
    check(proc.returncode==0)
    try:
        payload=json.loads(proc.stdout.strip().splitlines()[-1]); check(payload.get("ok") is True); check(payload.get(key)==1)
    except Exception:
        check(False); check(False)

old=os.environ.get("EIDOLON_DATA_DIR")
os.environ["EIDOLON_DATA_DIR"]=str(inspect_rt)
try:
    for route,key in (("/api/cognition/requirement-quality-assessments","assessment_count"),("/api/cognition/requirement-quality-assessment-reviews","review_count")):
        status,payload=handle_api_get(route)
        check(status==200); check(payload.get("ok") is True); check((payload.get("data") or {}).get("content_free") is True)
finally:
    if old is None: os.environ.pop("EIDOLON_DATA_DIR",None)
    else: os.environ["EIDOLON_DATA_DIR"]=old

# Casual language, wishes, hypotheticals, quotations, and hidden execution remain inert.
for utterance in (
    "It would be nice to know whether the requirements are met.",
    "Maybe assess quality later.",
    "Suppose every test passed.",
    'The guide says "prepare requirement and quality assessment".',
    "Accept the assessment and apply it automatically.",
    "Run missing tests and approve the work.",
    "Review requirement and quality assessment accept assessment.",
):
    inert=quality.process_requirement_quality_assessment_control(utterance,runtime_root=inspect_rt)
    check(inert.get("active") is False)

# Public projections expose no raw requirement codes, criterion text, or runtime path.
public=quality.public_requirement_quality_assessments(runtime_root=inspect_rt)
public_reviews=quality.public_requirement_quality_assessment_reviews(runtime_root=inspect_rt)
encoded=json.dumps({"a":public,"r":public_reviews},sort_keys=True)
check(str(inspect_rt) not in encoded)
check("core_behavior" not in encoded)
check("acceptance_gate" not in encoded)
for key in ("private_request_exposed","private_path_exposed","private_content_exposed","raw_provider_output_exposed","raw_test_output_exposed"):
    check(public.get(key) is False); check(public_reviews.get(key) is False)

print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
