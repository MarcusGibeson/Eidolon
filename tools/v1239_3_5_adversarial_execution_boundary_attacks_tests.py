from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import adversarial_execution_cognitive_boundary as a
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from conscious_agent.api_server import handle_api_get, dispatch_api
checks=[]
def check(v): checks.append(bool(v))
rt=tempfile.mkdtemp(prefix='eidolon-v1239-exec-')
execution=[row for row in a.attack_registry().get('attack_cases') or [] if row.get('category')=='execution_boundary']
check(len(execution)==12)
assessments=[]
for index,case in enumerate(execution):
    row=a.prepare_adversarial_boundary_assessment('project_'+hashlib.sha256(f'exec{index}'.encode()).hexdigest()[:16],attack_case_id=case['attack_case_id'],evidence_digest=hashlib.sha256(case['attack_case_id'].encode()).hexdigest(),lineage_digests={'session':hashlib.sha256(f's{index}'.encode()).hexdigest()},runtime_root=rt)
    assessments.append(row); check(row.get('ok')); check(row.get('category')=='execution_boundary'); check(row.get('assessment_state')=='attack_blocked'); check(row.get('launch_authorized') is False); check(row.get('resume_authorized') is False); check(row.get('automatic_retry_authorized') is False)
first=assessments[0]
for decision in sorted(a.REVIEW_DISPOSITIONS):
    phrase=f"review adversarial boundary {decision} for assessment {first['assessment_id']} digest {first['assessment_record_digest']}"
    turn=process_ordinary_chat_development_turn(phrase,runtime_root=rt)
    row=turn.get('adversarial_execution_cognitive_boundary') or {}
    check(turn.get('active')); check(row.get('ok')); check(row.get('disposition')==decision); check(row.get('review_effect')=='interpretation_only_no_authority'); check(row.get('attack_execution_authorized') is False); check(row.get('command_execution_authorized') is False); check(row.get('test_execution_authorized') is False)
    replay=process_ordinary_chat_development_turn(phrase,runtime_root=rt).get('adversarial_execution_cognitive_boundary') or {}
    check(replay.get('review_id')==row.get('review_id')); check(replay.get('review_record_digest')==row.get('review_record_digest'))
for text in ('show adversarial boundary attack registry','show adversarial boundary assessments','show adversarial boundary reviews',f"show adversarial boundary assessment {first['assessment_id']}"):
    out=process_ordinary_chat_development_turn(text,runtime_root=rt); check(out.get('active')); check((out.get('adversarial_execution_cognitive_boundary') or {}).get('ok'))
# stale and malformed exact controls fail closed
bad=a.review_adversarial_boundary_assessment(first['assessment_id'],expected_assessment_digest='0'*64,disposition='hold',runtime_root=rt); check(not bad.get('ok')); check(bad.get('reason')=='stale_assessment_digest')
wrong=f"review adversarial boundary hold for assessment {first['assessment_id']} digest {'0'*64}"
out=process_ordinary_chat_development_turn(wrong,runtime_root=rt).get('adversarial_execution_cognitive_boundary') or {}; check(not out.get('ok'))
for text in ('It would be nice to run the attack.','Maybe reuse the approval.','"review adversarial boundary acknowledge_blocked"'):
    out=a.process_adversarial_execution_cognitive_boundary_control(text,runtime_root=rt); check(out.get('active') is False)
# Tamper one assessment and prove load/review block.
path=Path(rt)/'development_campaigns'/'adversarial_boundary_assessments'/f"{assessments[1]['assessment_id']}.json"
data=json.loads(path.read_text()); data['boundary_decision']='allow'; path.write_text(json.dumps(data),encoding='utf-8')
loaded=a.load_adversarial_boundary_assessment(assessments[1]['assessment_id'],runtime_root=rt); check(not loaded.get('ok')); check(loaded.get('status')=='adversarial_boundary_record_tampered')
# CLI inspection
for command,key in [('adversarial-boundary-attack-registry','attack_case_count'),('adversarial-boundary-assessments','assessments_count'),('adversarial-boundary-reviews','reviews_count')]:
    args=[sys.executable,str(ROOT/'eidolon.py'),command]
    if command!='adversarial-boundary-attack-registry': args+=['--runtime-root',rt]
    proc=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    check(proc.returncode==0)
    try: payload=json.loads(proc.stdout.strip().splitlines()[-1]); check(payload.get('ok')); check(key in payload)
    except Exception: check(False); check(False)
# GET only API
for route in ('adversarial-boundary-attack-registry','adversarial-boundary-assessments','adversarial-boundary-reviews'):
    code,payload=handle_api_get('/api/cognition/'+route); check(code==200); check(payload.get('ok')); check((payload.get('data') or {}).get('content_free') is True)
code,payload=dispatch_api('POST','/api/cognition/adversarial-boundary-assessments',body={}); check(code in {404,405}); check(not payload.get('ok'))
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
