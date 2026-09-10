from __future__ import annotations
import json, sys, threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import multi_tool_orchestration as orch
import goal_motivation_work_priority_integration as alignment
from ordinary_chat_development_campaign import _atomic_json
from v1237_orchestration_fixture import build_orchestration_fixture, clone_runtime
checks=[]
def check(v): checks.append(bool(v))
f=build_orchestration_fixture('v1237-adversarial'); base=f['runtime']
def prepare(rt): return orch.prepare_multi_tool_orchestration_plan(f['alignment_assessment']['assessment_id'],expected_alignment_assessment_digest=f['alignment_assessment']['assessment_digest'],alignment_review_id=f['alignment_review']['review_id'],expected_alignment_review_digest=f['alignment_review']['review_digest'],quality_assessment_id=f['quality_assessment']['assessment_id'],expected_quality_assessment_digest=f['quality_assessment']['assessment_digest'],quality_review_id=f['quality_review']['review_id'],expected_quality_review_digest=f['quality_review']['review_digest'],tools=f['tools'],steps=f['steps'],initial_artifact_types=f['initial_artifact_types'],runtime_root=rt)
# Concurrent duplicates converge on one deterministic plan.
rt=clone_runtime(base,'v1237-concurrent'); rows=[]
def worker(): rows.append(prepare(rt))
threads=[threading.Thread(target=worker) for _ in range(4)]
for t in threads:t.start()
for t in threads:t.join()
check(len(rows)==4); check(all(r.get('ok') for r in rows)); check(len({r.get('plan_digest') for r in rows})==1)
p=rows[0]; review=orch.review_multi_tool_orchestration_plan(p['plan_id'],expected_plan_digest=p['plan_digest'],disposition='accept_plan',runtime_root=rt)
check(review.get('ok')); check(review.get('tool_invocation_authorized') is False)
# A downstream result before dependencies fails closed.
step=p['steps'][1]
blocked=orch.record_multi_tool_orchestration_step_result(p['plan_id'],expected_plan_digest=p['plan_digest'],plan_review_id=review['review_id'],expected_plan_review_digest=review['review_digest'],step_id=step['step_id'],tool_id=step['tool_id'],expected_input_binding_digest=step['step_input_binding_digest'],output_digest='d'*64,evidence_digest='e'*64,outcome='completed',runtime_root=rt)
check(blocked.get('ok') is False); check('step_dependency_not_completed' in blocked.get('reason',''))
# Failed first step routes to operator review and never offers a next tool.
first=p['steps'][0]
failed=orch.record_multi_tool_orchestration_step_result(p['plan_id'],expected_plan_digest=p['plan_digest'],plan_review_id=review['review_id'],expected_plan_review_digest=review['review_digest'],step_id=first['step_id'],tool_id=first['tool_id'],expected_input_binding_digest=first['step_input_binding_digest'],output_digest='f'*64,evidence_digest='1'*64,outcome='failed',runtime_root=rt)
check(failed.get('ok')); check(failed.get('failure_route')=='prepare_operator_failure_handoff'); check(failed.get('next_tool_authorized') is False); check(failed.get('hidden_retry_created') is False)
h=orch.prepare_multi_tool_orchestration_handoff(failed['result_id'],expected_result_digest=failed['result_digest'],runtime_root=rt)
check(h.get('ok')); check(h.get('handoff_route')=='operator_failure_review'); check(h.get('eligible_step_ids')==[]); check(h.get('next_tool_authorized') is False)
hr=orch.review_multi_tool_orchestration_handoff(h['handoff_id'],expected_handoff_digest=h['handoff_digest'],disposition='accept_handoff',runtime_root=rt)
check(hr.get('ok')); check(hr.get('next_tool_authorized') is False); check(hr.get('automatic_continuation_created') is False)
# Conflicting result replay is rejected.
conflict=orch.record_multi_tool_orchestration_step_result(p['plan_id'],expected_plan_digest=p['plan_digest'],plan_review_id=review['review_id'],expected_plan_review_digest=review['review_digest'],step_id=first['step_id'],tool_id=first['tool_id'],expected_input_binding_digest=first['step_input_binding_digest'],output_digest='2'*64,evidence_digest='3'*64,outcome='completed',runtime_root=rt)
check(conflict.get('ok') is False); check('conflicting_step_result' in conflict.get('reason',''))
# Tampered plan and review records fail closed.
rt2=clone_runtime(base,'v1237-tamper'); p2=prepare(rt2); path=orch._path('multi_tool_orchestration_plans',p2['plan_id'],rt2); row=json.loads(path.read_text()); row['step_count']=999; _atomic_json(path,row)
tampered=orch.review_multi_tool_orchestration_plan(p2['plan_id'],expected_plan_digest=p2['plan_digest'],disposition='accept_plan',runtime_root=rt2)
check(tampered.get('ok') is False); check('integrity' in tampered.get('reason','') or 'invalid' in tampered.get('reason',''))
# Stale upstream alignment evidence fails on review.
rt3=clone_runtime(base,'v1237-stale-upstream'); p3=prepare(rt3)
apath=alignment._review_path(f['alignment_assessment']['assessment_id'],rt3)
row=json.loads(apath.read_text()); row['disposition']='reject'; row=orch._sealed(row,'goal_motivation_work_priority_review_record_digest'); _atomic_json(apath,row)
stale=orch.review_multi_tool_orchestration_plan(p3['plan_id'],expected_plan_digest=p3['plan_digest'],disposition='accept_plan',runtime_root=rt3)
check(stale.get('ok') is False); check('alignment_review_not_accepted' in stale.get('reason',''))
# Public projections contain no raw content/path/provider output.
for payload in (orch.public_multi_tool_orchestration_plans(runtime_root=rt),orch.public_multi_tool_orchestration_reviews(runtime_root=rt),orch.public_multi_tool_orchestration_results(runtime_root=rt),orch.public_multi_tool_orchestration_handoffs(runtime_root=rt),orch.public_multi_tool_orchestration_handoff_reviews(runtime_root=rt)):
    text=json.dumps(payload,sort_keys=True)
    check('/tmp/' not in text); check('content intentionally' not in text); check(payload.get('raw_provider_output_exposed') is False); check(payload.get('private_content_exposed') is False)
for record in (p,review,failed,h,hr):
    for k,e in orch.AUTHORITY_FLAGS.items(): check(record.get(k) is e)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
