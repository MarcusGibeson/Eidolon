from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from product_quality_judgment import build_product_quality_from_review_packet,build_product_quality_judgment,public_product_quality_judgment,review_packet_quality_evidence
from product_quality_judgment_foundations import DENIED_AUTHORITY,DIMENSIONS
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
def dig(s): return sha256(s.encode()).hexdigest()
def ev(d,t,state='pass',name=None,**kw): return {'dimension':d,'evidence_type':t,'state':state,'evidence_digest':dig(name or f'{d}:{t}:{state}'),'scope_digest':dig('scope'),**kw}
SPECIAL={'coherence':'integration_test','usability':'usability_review','accessibility':'accessibility_review','maintainability':'static_analysis','completeness':'requirements_review','operator_readiness':'operator_walkthrough'}
def full(state_overrides=None):
    state_overrides=state_overrides or {}; return [ev(d,t,state_overrides.get(d,'pass'),f'{d}:{state_overrides.get(d,"pass")}') for d,t in SPECIAL.items()]

narrow=build_product_quality_judgment([ev(d,'deterministic_test',name=f'narrow:{d}') for d in DIMENSIONS],scope_digest=dig('scope'))
req(narrow['contract_version']=='v1289.5','contract')
req(narrow['disposition']=='insufficient_evidence','narrow_tests_insufficient')
req(narrow['deterministic_only_evidence_detected'] is True,'deterministic_only_detected')
req(narrow['narrow_test_success_is_product_readiness'] is False,'narrow_not_readiness')
req(narrow['deterministic_tests_alone_sufficient'] is False,'tests_not_sufficient')
req(narrow['operator_ready_claimed'] is False,'narrow_not_operator_ready')
req(narrow['release_ready_claimed'] is False,'never_release_claim')

ready=build_product_quality_judgment(full(),scope_digest=dig('scope'))
req(ready['disposition']=='operator_ready_candidate','specialized_operator_ready_candidate')
req(ready['operator_ready_claimed'] is True,'operator_ready_claim')
req(all(v=='pass' for v in ready['dimension_states'].values()),'all_dimensions_pass')
req(ready['release_ready_claimed'] is False,'operator_ready_not_release_ready')
req(ready['quality_judgment_is_authorization'] is False,'quality_not_authority')

failed=build_product_quality_judgment(full({'accessibility':'fail'}))
req(failed['disposition']=='needs_revision','accessibility_failure_needs_revision')
warned=build_product_quality_judgment(full({'usability':'warn'}))
req(warned['disposition']=='ready_with_known_gaps','warning_known_gaps')
missing=build_product_quality_judgment([ev('coherence','integration_test')])
req(missing['disposition']=='insufficient_evidence','missing_dimension_insufficient')

# Existing v1268 review packets bridge conservatively: passing verification does not invent UX/a11y/operator evidence.
packet={'review_id':'r1','candidate_manifest_digest':dig('candidate'),'changed_file_count':3,'verification':{'passed':True,'result_digest':dig('verification')},'risks':[]}
rows=review_packet_quality_evidence(packet)
req({r['dimension'] for r in rows}=={'coherence','completeness','maintainability'},'review_bridge_bounded_dimensions')
req(all(r['evidence_type']=='deterministic_test' for r in rows),'review_bridge_test_evidence_only')
bridge=build_product_quality_from_review_packet(packet)
req(bridge['disposition']=='insufficient_evidence','review_packet_not_product_ready')
req(bridge['dimension_states']['usability']=='unknown','review_does_not_invent_usability')
req(bridge['dimension_states']['accessibility']=='unknown','review_does_not_invent_accessibility')
req(bridge['dimension_states']['operator_readiness']=='unknown','review_does_not_invent_operator_ready')

supp=full()
bridged=build_product_quality_from_review_packet(packet,supp)
req(bridged['disposition']=='operator_ready_candidate','supplemental_specialized_can_complete')
req(bridged['release_ready_claimed'] is False,'supplemental_still_no_release')

risk_packet=packet|{'risks':[{'severity':'critical','risk_code':'operator_release_boundary'}]}
risk=build_product_quality_from_review_packet(risk_packet,supp)
req(risk['dimension_states']['operator_readiness']=='warn','critical_operator_risk_preserved')
req(risk['disposition']=='ready_with_known_gaps','critical_risk_prevents_ready_candidate')

pub=public_product_quality_judgment(ready)
req(pub['content_free'] and pub['read_only'],'public_content_free_read_only')
req('dimensions' not in pub,'public_omits_detail_rows')
req(len(pub['judgment_digest'])==64,'judgment_digest')
req(all(pub[k] is False for k in DENIED_AUTHORITY),'public_no_authority')
print(json.dumps({'ok':True,'suite':'v1289.3-v1289.5-product-quality-judgment-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
