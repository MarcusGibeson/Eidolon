from __future__ import annotations
import copy,json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from competing_candidate_evaluation_foundations import comparison_trigger,seal_candidate_identity,DENIED_AUTHORITY,digest
from competing_candidate_evaluation import evaluate_competing_candidates
from competing_candidate_evaluation_reliability import assess_competing_candidate_evaluation_reliability
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
def e(name,score=90):
 i=seal_candidate_identity(campaign_id='c',baseline_digest=d('base'),approach_digest=d('a'+name),workspace_digest=d('w'+name),changed_path_digests=[d('p'+name)])
 return i|{'verification_run_digest':d('run'+name),'focused_verification_passed':True,'regression_verification_passed':True,'scope_conforming':True,'evidence_fresh':True,'private_evidence':False,'quality_disposition':'operator_ready_candidate','quality_score':score,'risk':20,'cost':20,'reversibility':90,'residual_uncertainty':10}
r=evaluate_competing_candidates([e('1',95),e('2',80)],comparison_context=comparison_trigger(uncertainty=70,viable_approach_count=2));req(r['disposition']=='recommend_candidate_for_operator_review','good_result');req(assess_competing_candidate_evaluation_reliability([r])['ok'],'good_reliability')
def mutate(fn):
 x=copy.deepcopy(r);fn(x);return assess_competing_candidate_evaluation_reliability([x])['violations']
req(any('authority' in v for v in mutate(lambda x:x.__setitem__('release_authorized',True))),'authority')
req(any('application' in v for v in mutate(lambda x:x.__setitem__('selection_is_application',True))),'application')
req(any('missing_operator' in v for v in mutate(lambda x:x.__setitem__('operator_review_required',False))),'operator')
req(any('blocked_candidate' in v for v in mutate(lambda x:next(a for a in x['assessments'] if a['candidate_id']==x['recommended_candidate_id']).__setitem__('blocked',True))),'blocked_selected')
req(any('integrity_failure' in v for v in mutate(lambda x:x.__setitem__('integrity_violations',['workspace']))),'integrity_selected')
req(any('duplicate_candidate' in v for v in mutate(lambda x:x['assessments'].append(copy.deepcopy(x['assessments'][0])))),'duplicate_assessment')
req(any('invalid_evaluation_digest' in v for v in mutate(lambda x:x.__setitem__('evaluation_digest','bad'))),'digest')
b=assess_competing_candidate_evaluation_reliability([r,r]);req(b['ok'] and b['evaluation_count']==2,'batch');req(b['native_windows_candidate_isolation_validation_pending'],'native');req(all(b[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1294.6-v1294.8-competing-candidate-evaluation-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
