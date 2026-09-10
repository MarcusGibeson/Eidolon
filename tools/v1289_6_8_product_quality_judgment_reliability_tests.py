from __future__ import annotations
import copy,json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from product_quality_judgment import build_product_quality_judgment
from product_quality_judgment_foundations import DENIED_AUTHORITY
from product_quality_judgment_reliability import assess_product_quality_reliability
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
def dig(s): return sha256(s.encode()).hexdigest()
SPECIAL={'coherence':'integration_test','usability':'usability_review','accessibility':'accessibility_review','maintainability':'static_analysis','completeness':'requirements_review','operator_readiness':'operator_walkthrough'}
evidence=[{'dimension':d,'evidence_type':t,'state':'pass','evidence_digest':dig(d+t),'scope_digest':dig('scope')} for d,t in SPECIAL.items()]
good=build_product_quality_judgment(evidence)
r=assess_product_quality_reliability([good]);req(r['ok'],'good_reliable');req(r['violation_count']==0,'no_violations')

bad=copy.deepcopy(good);bad['release_ready_claimed']=True
x=assess_product_quality_reliability([bad]);req(not x['ok'] and any('release_claim' in v for v in x['violations']),'release_overclaim_caught')

bad=copy.deepcopy(good);bad['quality_judgment_is_authorization']=True
x=assess_product_quality_reliability([bad]);req(any('authority_claim' in v for v in x['violations']),'authority_claim_caught')

bad=copy.deepcopy(good);bad['deterministic_tests_alone_sufficient']=True
x=assess_product_quality_reliability([bad]);req(any('test_only_readiness' in v for v in x['violations']),'test_only_overclaim_caught')

bad=copy.deepcopy(good);bad['dimension_states']['accessibility']='warn';bad['operator_ready_claimed']=True
x=assess_product_quality_reliability([bad]);req(any('premature_operator_ready' in v for v in x['violations']),'premature_ready_caught')

bad=copy.deepcopy(good);bad['dimension_states'].pop('usability')
x=assess_product_quality_reliability([bad]);req(any('dimension_coverage' in v for v in x['violations']),'coverage_caught')

bad=copy.deepcopy(good);bad['self_update_authorized']=True
x=assess_product_quality_reliability([bad]);req(any('authority_expansion' in v for v in x['violations']),'authority_expansion_caught')

batch=assess_product_quality_reliability([good,good]);req(batch['ok'] and batch['judgment_count']==2,'batch_reliable')
req(batch['multidimensional_quality_preserved'],'multidimensional_preserved')
req(batch['test_success_not_overclaimed'],'test_success_not_overclaimed')
req(batch['release_boundary_preserved'],'release_boundary_preserved')
req(batch['content_free'] and batch['read_only'],'read_only_content_free')
req(all(batch[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1289.6-v1289.8-product-quality-judgment-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
