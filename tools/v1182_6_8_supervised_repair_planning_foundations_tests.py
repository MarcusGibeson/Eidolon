from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.supervised_repair_planning import review_repair_diagnosis,build_supervised_repair_plan,repair_plan_public_summary
checks=[]
def req(v):checks.append(bool(v))
def dg(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def diagnosis(code='python_compile_failure_observed',candidates=True):
 d={'schema_version':'1','contract_version':'v1182.5','content_free':True,'diagnosis_status':'complete','diagnosis_posture':'diagnosis_candidates_require_review','diagnosis_candidates':([{'diagnosis_code':code,'confidence':'high_observation_low_root_cause','supported_conclusion':'observed','unknowns':['required_repair'],'suggested_next_step':'operator_review_before_repair_planning'}] if candidates else []),'root_cause_proven':False,'repair_authorized':False,'retest_authorized':False}
 d['diagnosis_digest']=dg({k:v for k,v in d.items() if k!='diagnosis_digest'}); d['diagnosis_receipt_digest']=dg(d); return d
d=diagnosis(); r=review_repair_diagnosis(d,'confirm','operator'); req(r['review_status']=='confirmed_for_repair_planning')
p=build_supervised_repair_plan(d,r); req(p['planning_status']=='candidate' and p['repair_step_count']==1)
req(p['repair_steps'][0]['minimal_change_required'] and p['repair_steps'][0]['sandbox_only_required'])
req(not p['repair_authorized'] and not p['retest_authorized'] and not p['root_cause_proven'])
for code in ['sandbox_test_timeout_observed','sandbox_test_execution_blocked']:
 x=diagnosis(code); y=review_repair_diagnosis(x,'confirm','operator'); req(build_supervised_repair_plan(x,y)['planning_status']=='candidate')
req(review_repair_diagnosis(d,'reject','operator')['review_status']=='rejected')
req(review_repair_diagnosis(d,'defer','operator')['review_status']=='deferred')
req(review_repair_diagnosis(d,'approve','operator')['block_reason']=='invalid_diagnosis_review_binding')
req(review_repair_diagnosis(d,'confirm','')['block_reason']=='invalid_diagnosis_review_binding')
req(review_repair_diagnosis(diagnosis(candidates=False),'confirm','operator')['block_reason']=='no_failure_diagnosis_to_confirm')
t={**d,'diagnosis_digest':'0'*64}; req(review_repair_diagnosis(t,'confirm','operator')['block_reason']=='invalid_diagnosis_review_binding')
req(build_supervised_repair_plan(d,review_repair_diagnosis(d,'reject','operator'))['block_reason']=='invalid_confirmed_diagnosis_binding')
x=diagnosis('invented'); y=review_repair_diagnosis(x,'confirm','operator'); req(build_supervised_repair_plan(x,y)['block_reason']=='unsupported_diagnosis_code')
s=repair_plan_public_summary(p); blob=json.dumps(s).lower(); req(s['content_free'] and not s['source_modified'] and not s['patch_created'])
req('stdout' not in blob and 'stderr' not in blob and 'source_text' not in blob)
req(not s['tool_invoked'] and not s['provider_contacted'] and not s['model_contacted'])
req(not s['approval_granted'] and not s['release_authorized'])
source=(ROOT/'conscious_agent/supervised_repair_planning.py').read_text(); req('subprocess' not in source and 'open(' not in source and 'write_' not in source)
req('repair_authorized\':False' in source and 'retest_authorized\':False' in source)
print(json.dumps({'ok':all(checks),'suite':'v1182.6-v1182.8-supervised-repair-planning-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
if not all(checks):print([i+1 for i,v in enumerate(checks) if not v]);raise SystemExit(1)
