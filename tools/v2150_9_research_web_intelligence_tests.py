from __future__ import annotations
import hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2150-data-')
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION,plan_research,assess_source_candidate,prepare_browser_research_request,validate_download_receipt,validate_document_extraction_receipt,capture_research_evidence,evaluate_claim_support,process_era7_research_control
checks=[]
def req(v,n): checks.append(n); assert v,n
def native_receipt(kind, **values):
    row={'contract_version':NATIVE_RECEIPT_CONTRACT_VERSION,'receipt_kind':kind,'authoritative':True,'terminal':True,'operation_digest':'8'*64,'terminal_result_digest':'9'*64,**values}
    row['receipt_digest']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    return row
plan=plan_research('What changed in project X and what evidence supports it?',freshness='versioned',private_context_present=True)
req(plan['ok'] and plan['subquestions'],'research_plan_decomposes_question')
req(plan['question_text_persisted'] is False and plan['private_context_may_not_enter_public_query'] is True,'research_plan_privacy_boundary')
req(plan['citation_required_for_current_claims'] and plan['contradiction_review_required'],'research_requires_citations_and_contradiction_review')
local=assess_source_candidate(url='http://127.0.0.1/private',plan_digest=plan['plan_digest'])
req(local['status']=='private_network_target_rejected','private_network_browser_target_rejected')
secret=assess_source_candidate(url='https://example.com/?api_key=supersecret',plan_digest=plan['plan_digest'])
req(secret['ok'] is False,'credential_like_url_rejected')
source=assess_source_candidate(url='https://docs.example.com/current?user=private',source_kind='primary_official',freshness_policy='stable',plan_digest=plan['plan_digest'])
req(source['ok'] and source['public_url']=='https://docs.example.com/current','public_source_candidate_sanitizes_query')
req(source['source_observed'] is False and source['network_contacted'] is False,'source_assessment_does_not_browse')
request=prepare_browser_research_request(plan=plan,source_candidates=[source],operation_id='research-1')
req(request['ok'] and request['request']['source_count']==1,'governed_browser_request_prepared')
req(request['request']['browser_execution_admitted'] is False and request['browser_contacted'] is False,'browser_request_nonexecuting')
small_receipt=native_receipt('download',mime_type='application/pdf',size_bytes=1000,content_digest='f'*64)
small=validate_download_receipt(small_receipt)
req(small['ok'] and small['extraction_authorized'],'bounded_download_receipt_accepted')
large=validate_download_receipt(native_receipt('download',mime_type='application/pdf',size_bytes=100_000_000,content_digest='f'*64))
req(not large['ok'],'oversized_download_rejected')
malformed=validate_download_receipt(native_receipt('download',mime_type='application/pdf',size_bytes='not-a-number',content_digest='f'*64))
req(not malformed['ok'],'malformed_download_size_fails_closed')
extract=validate_document_extraction_receipt(small_receipt,native_receipt('document_extraction',source_content_digest='f'*64,extracted_text_digest='6'*64,structure_digest='7'*64,page_count=4,extractor_code='pdf_text'))
req(extract['ok'] and extract['page_count']==4 and extract['raw_text_included'] is False,'document_extraction_receipt_bound_to_download')
bad_extract=validate_document_extraction_receipt(small_receipt,native_receipt('document_extraction',source_content_digest='0'*64,extracted_text_digest='6'*64,page_count=4))
req(not bad_extract['ok'],'mismatched_document_extraction_rejected')
obs=[
 native_receipt('source_observation',plan_digest=plan['plan_digest'],source_observed=True,source_candidate_digest=source['source_candidate_digest'],claim_code='claim-a',stance='supports',evidence_digest='1'*64,citation_id='c1',source_kind='primary_official',quality_score=1,freshness_known=True,fresh_enough=True),
 native_receipt('source_observation',plan_digest=plan['plan_digest'],source_observed=True,source_candidate_digest='2'*64,claim_code='claim-a',stance='refutes',evidence_digest='3'*64,citation_id='c2',source_kind='reputable_secondary',quality_score=.8,freshness_known=True,fresh_enough=True),
]
untrusted=capture_research_evidence(plan_digest=plan['plan_digest'],observations=[{'authoritative':True,'source_observed':True,'source_candidate_digest':'4'*64,'claim_code':'fake','stance':'supports','evidence_digest':'5'*64,'citation_id':'fake'}])
req(untrusted['evidence_count']==0,'generated_or_unreceipted_observation_not_research_evidence')
tampered=dict(obs[0]); tampered['stance']='refutes'
req(capture_research_evidence(plan_digest=plan['plan_digest'],observations=[tampered])['evidence_count']==0,'tampered_research_receipt_rejected')
bundle=capture_research_evidence(plan_digest=plan['plan_digest'],observations=obs)
req(bundle['ok'] and bundle['contradicted_claim_codes']==['claim-a'],'contradictory_research_evidence_preserved')
req(bundle['raw_quotes_persisted'] is False and len(bundle['citations'])==2,'citation_capture_content_minimized')
claim=evaluate_claim_support(bundle,'claim-a',current_claim=True)
req(claim['support_state']=='conflicted','conflicting_current_claim_remains_conflicted')
req(claim['generated_prose_is_evidence'] is False and claim['internal_knowledge_is_current_evidence'] is False,'current_research_evidence_boundary')
ctrl=process_era7_research_control('inspect research and web intelligence contract')
req(ctrl['active'] and ctrl['governed_browser_required'],'research_operator_contract')
blocked=process_era7_research_control('inspect research and web intelligence contract and browse now')
req(blocked['status']=='era7_research_read_only_scope_expansion_rejected','compound_research_scope_rejected')
print(json.dumps({'suite':'v2150.9-research-web-intelligence','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
