from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from competing_candidate_evaluation_foundations import comparison_trigger,seal_candidate_identity,DENIED_AUTHORITY,digest
from competing_candidate_evaluation import evaluate_competing_candidates
from v1294_test_support import build_two_candidates,d
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
x=build_two_candidates();req(x['a_focused']['passed'] and not x['a_regression']['passed'],'candidate_a_partial');req(x['b_focused']['passed'] and x['b_regression']['passed'],'candidate_b_passes');req(x['a']!=x['b'] and x['a_tree']!=x['b_tree'],'isolated_distinct_workspaces')
campaign='campaign-benchmark';base=x['baseline_digest']
aid=seal_candidate_identity(campaign_id=campaign,baseline_digest=base,approach_digest=d('partial'),workspace_digest=d(str(x['a'])),changed_path_digests=[d('invoice/parse.py')]);bid=seal_candidate_identity(campaign_id=campaign,baseline_digest=base,approach_digest=d('complete'),workspace_digest=d(str(x['b'])),changed_path_digests=[d('invoice/parse.py'),d('invoice/report.py')])
def evidence(i,focused,regression,quality,score,risk,cost,rev,u):return i|{'verification_run_digest':digest([focused['run_digest'],regression['run_digest']]),'focused_verification_passed':focused['passed'],'regression_verification_passed':regression['passed'],'scope_conforming':True,'evidence_fresh':True,'private_evidence':False,'quality_disposition':quality,'quality_score':score,'risk':risk,'cost':cost,'reversibility':rev,'residual_uncertainty':u}
ea=evidence(aid,x['a_focused'],x['a_regression'],'needs_revision',55,20,15,95,40);eb=evidence(bid,x['b_focused'],x['b_regression'],'operator_ready_candidate',92,25,35,85,12)
ctx=comparison_trigger(uncertainty=70,viable_approach_count=2,competing_hypothesis_count=2);r=evaluate_competing_candidates([ea,eb],comparison_context=ctx);req(r['disposition']=='recommend_candidate_for_operator_review','recommend');req(r['recommended_candidate_id']==bid['candidate_id'],'correct_candidate');req(any(a['candidate_id']==aid['candidate_id'] and a['blocked'] for a in r['assessments']),'failed_candidate_blocked');req(r['comparisons'] and r['operator_review_required'],'explainable_operator_review');req(not r['selection_is_application'] and not r['selection_is_update'],'not_apply_update');req(all(r[k] is False for k in DENIED_AUTHORITY),'no_authority')
# Comparison is not mandatory when evidence does not justify it.
no=evaluate_competing_candidates([eb],comparison_context=comparison_trigger(uncertainty=10,viable_approach_count=1));req(no['disposition']=='comparison_not_warranted','comparison_not_warranted')
# Independent isolation is a hard integrity gate.
bad=dict(eb);bad['workspace_digest']=ea['workspace_digest'];bad['verification_run_digest']=d('independent-other-run');z=evaluate_competing_candidates([ea,bad],comparison_context=ctx);req(z['disposition']=='reject_comparison_integrity_failure' and 'candidate_workspace_not_isolated' in z['integrity_violations'],'shared_workspace_rejected')
# All failed candidates may be rejected.
allbad=evaluate_competing_candidates([ea,dict(ea,candidate_id='other',candidate_identity_digest=d('other'),workspace_digest=d('other-w'),approach_digest=d('other-a'),verification_run_digest=d('other-r'))],comparison_context=ctx);req(allbad['disposition']=='reject_all_candidates','reject_all')
# Near-equal viable candidates under uncertainty can defer.
b2=dict(eb,candidate_id='b2',candidate_identity_digest=d('b2'),workspace_digest=d('b2w'),approach_digest=d('b2a'),verification_run_digest=d('b2r'),quality_score=91,residual_uncertainty=55);b1=dict(eb,residual_uncertainty=55);amb=evaluate_competing_candidates([b1,b2],comparison_context=ctx,ambiguity_margin=5);req(amb['disposition']=='defer_ambiguous_candidates','ambiguous_defer')
print(json.dumps({'ok':True,'suite':'v1294.3-v1294.5-competing-candidate-evaluation-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
