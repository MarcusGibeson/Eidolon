from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import multi_tool_orchestration as orch
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1237_orchestration_fixture import build_orchestration_fixture, clone_runtime
checks=[]
def check(v): checks.append(bool(v))
f=build_orchestration_fixture('v1237-operator'); rt=clone_runtime(f['runtime'],'v1237-operator-runtime')
p=orch.prepare_multi_tool_orchestration_plan(f['alignment_assessment']['assessment_id'],expected_alignment_assessment_digest=f['alignment_assessment']['assessment_digest'],alignment_review_id=f['alignment_review']['review_id'],expected_alignment_review_digest=f['alignment_review']['review_digest'],quality_assessment_id=f['quality_assessment']['assessment_id'],expected_quality_assessment_digest=f['quality_assessment']['assessment_digest'],quality_review_id=f['quality_review']['review_id'],expected_quality_review_digest=f['quality_review']['review_digest'],tools=f['tools'],steps=f['steps'],initial_artifact_types=f['initial_artifact_types'],runtime_root=rt)
turn=process_ordinary_chat_development_turn(f"Review multi tool orchestration accept_plan for plan {p['plan_id']} digest {p['plan_digest']}.",runtime_root=rt)
r=turn.get('multi_tool_orchestration') or {}
for v in (turn.get('active') is True,r.get('ok'),r.get('disposition')=='accept_plan',r.get('plan_interpretation_accepted') is True,r.get('step_authority_created') is False,r.get('next_tool_authorized') is False): check(v)
step=p['steps'][0]
text=(f"Record multi tool orchestration result completed for plan {p['plan_id']} digest {p['plan_digest']} review {r['review_id']} digest {r['review_digest']} step {step['step_id']} tool {step['tool_id']} input {step['step_input_binding_digest']} output {'b'*64} evidence {'c'*64}.")
result_turn=process_ordinary_chat_development_turn(text,runtime_root=rt); result=result_turn.get('multi_tool_orchestration') or {}
for v in (result_turn.get('active') is True,result.get('ok'),result.get('outcome')=='completed',result.get('tool_executed_by_orchestration') is False,result.get('next_tool_authorized') is False,result.get('automatic_continuation_created') is False): check(v)
handoff_turn=process_ordinary_chat_development_turn(f"Prepare multi tool orchestration handoff for result {result['result_id']} digest {result['result_digest']}.",runtime_root=rt); handoff=handoff_turn.get('multi_tool_orchestration') or {}
for v in (handoff_turn.get('active') is True,handoff.get('ok'),handoff.get('eligible_step_ids')==['step_edit'],handoff.get('fresh_step_authority_required') is True,handoff.get('next_tool_authorized') is False): check(v)
hr_turn=process_ordinary_chat_development_turn(f"Review multi tool orchestration handoff accept_handoff for handoff {handoff['handoff_id']} digest {handoff['handoff_digest']}.",runtime_root=rt); hr=hr_turn.get('multi_tool_orchestration') or {}
for v in (hr_turn.get('active') is True,hr.get('ok'),hr.get('disposition')=='accept_handoff',hr.get('handoff_interpretation_accepted') is True,hr.get('next_tool_authorized') is False,hr.get('fresh_step_authority_still_required') is True): check(v)
# Deterministic replay and conflicts.
replay=orch.review_multi_tool_orchestration_plan(p['plan_id'],expected_plan_digest=p['plan_digest'],disposition='accept_plan',runtime_root=rt)
check(replay.get('ok')); check(replay.get('operation_status')=='replayed')
conflict=orch.review_multi_tool_orchestration_plan(p['plan_id'],expected_plan_digest=p['plan_digest'],disposition='reject',runtime_root=rt)
check(conflict.get('ok') is False); check('conflicting_orchestration_review' in conflict.get('reason',''))
# Inspection surfaces stay content-free.
for phrase,key,count in (
    ('Show multi tool orchestration plans.','plans',1),('Show multi tool orchestration reviews.','reviews',1),
    ('Show multi tool orchestration results.','results',1),('Show multi tool orchestration handoffs.','handoffs',1),
    ('Show multi tool orchestration handoff reviews.','handoff_reviews',1),
):
    row=(process_ordinary_chat_development_turn(phrase,runtime_root=rt).get('multi_tool_orchestration') or {})
    check(row.get('ok')); check(row.get(f'{key[:-1]}_count')==count); check(row.get('private_content_exposed') is False)
show=process_ordinary_chat_development_turn(f"Show multi tool orchestration plan {p['plan_id']}.",runtime_root=rt)
check(show.get('active') is True); check((show.get('multi_tool_orchestration') or {}).get('plan_id')==p['plan_id'])
# Casual, quoted, hypothetical, and incomplete language remains inert.
for text in ('It would be nice to orchestrate several tools.','The guide says "review multi tool orchestration accept_plan".','Could you run the next tool later?','Review multi tool orchestration accept_plan.'):
    check(process_ordinary_chat_development_turn(text,runtime_root=rt).get('multi_tool_orchestration') is None)
# CLI list surfaces.
commands=(('multi-tool-orchestration-plans','plan_count'),('multi-tool-orchestration-reviews','review_count'),('multi-tool-orchestration-results','result_count'),('multi-tool-orchestration-handoffs','handoff_count'),('multi-tool-orchestration-handoff-reviews','handoff_review_count'))
for command,count_key in commands:
    proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),command,'--runtime-root',str(rt)],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    check(proc.returncode==0)
    try: data=json.loads(proc.stdout.strip().splitlines()[-1]); check(data.get('ok')); check(data.get(count_key)==1)
    except Exception: check(False); check(False)
# GET-only API and absent mutation route.
code='''\nimport json\nfrom conscious_agent.api_server import handle_api_get,dispatch_api\nroutes=["multi-tool-orchestration-plans","multi-tool-orchestration-reviews","multi-tool-orchestration-results","multi-tool-orchestration-handoffs","multi-tool-orchestration-handoff-reviews"]\nrows=[]\nfor route in routes: rows.append(handle_api_get("/api/cognition/"+route))\npost=dispatch_api("POST","/api/cognition/multi-tool-orchestration-plans",body={})\nprint(json.dumps({"rows":rows,"post":post},sort_keys=True))\n'''
proc=subprocess.run([sys.executable,'-c',code],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'EIDOLON_DATA_DIR':str(rt),'PYTHONPATH':f"{ROOT}:{ROOT/'conscious_agent'}:{ROOT/'tools'}",'PYTHONDONTWRITEBYTECODE':'1'})
check(proc.returncode==0)
try:
    data=json.loads(proc.stdout.strip().splitlines()[-1]); check(all(row[0]==200 and row[1].get('ok') for row in data['rows'])); check(data['post'][0] in {404,405})
except Exception: check(False); check(False)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
