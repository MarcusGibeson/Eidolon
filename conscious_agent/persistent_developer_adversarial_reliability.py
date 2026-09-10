from __future__ import annotations
"""v1189.6-v1189.8 adversarial reliability and bounded readiness evidence."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1189.8';SCHEMA_VERSION='1';MAX_BYTES=262144
DIGEST_RE=re.compile(r'^[0-9a-f]{64}$');ID_RE=re.compile(r'^[A-Za-z0-9._:-]{8,128}$')
ALLOWED_STATES=frozenset({'active','paused','interrupted','provider_outage','restart_pending','completed','failed','blocked'})
ALLOWED_ACTIONS=frozenset({'hold','resume_review','restart_review','abandon'})
FORBIDDEN=frozenset({'raw_source','raw_patch','stdout','stderr','prompt','conversation','memory','secret','provider_payload','private_reasoning','release_authority','authorization'})
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,'')).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode())<=MAX_BYTES
def _forbidden(v:object)->bool:
 if isinstance(v,Mapping):return any(str(k).lower() in FORBIDDEN or _forbidden(x) for k,x in v.items())
 if isinstance(v,(list,tuple)):return any(_forbidden(x) for x in v)
 return False

def assess_persistent_developer_reliability(*,hardening_receipt:Mapping[str,Any],long_session_evidence:Mapping[str,Any],nonce_registration:Mapping[str,Any],current_source_digest:str,expected_source_digest:str,current_nonce_generation:int,expected_nonce_generation:int,session_state:str,interruption_count:int,privacy_findings:Sequence[str]=(),authority_claims:Sequence[str]=())->dict[str,Any]:
 h,e,n=dict(hardening_receipt),dict(long_session_evidence),dict(nonce_registration);errors=[]
 hd,hok=_verify(h,'hardening_receipt_digest');ed,eok=_verify(e,'long_session_evidence_digest')
 if not hok:errors.append('tampered_hardening_receipt')
 if not eok:errors.append('tampered_long_session_evidence')
 if e.get('hardening_receipt_digest')!=hd:errors.append('long_session_lineage_mismatch')
 if n.get('status')!='registered' or not DIGEST_RE.fullmatch(str(n.get('nonce_ledger_digest','')).lower()):errors.append('invalid_nonce_registration')
 if n.get('review_nonce')!=h.get('review_nonce'):errors.append('nonce_lineage_mismatch')
 cur,exp=str(current_source_digest).lower(),str(expected_source_digest).lower()
 if not DIGEST_RE.fullmatch(cur) or not DIGEST_RE.fullmatch(exp):errors.append('invalid_source_digest')
 source_stale=cur!=exp
 if not isinstance(current_nonce_generation,int) or not isinstance(expected_nonce_generation,int) or min(current_nonce_generation,expected_nonce_generation)<0:errors.append('invalid_nonce_generation')
 replay_or_stale=current_nonce_generation!=expected_nonce_generation
 if replay_or_stale:errors.append('stale_or_replayed_nonce_generation')
 if session_state not in ALLOWED_STATES:errors.append('unsupported_session_state')
 if not isinstance(interruption_count,int) or interruption_count<0:errors.append('invalid_interruption_count')
 if privacy_findings:errors.append('privacy_findings_present')
 if authority_claims:errors.append('authority_claims_present')
 if _forbidden([h,e,n]):errors.append('private_or_authority_content_present')
 if not _bounded([h,e,n,list(privacy_findings),list(authority_claims)]):errors.append('oversized_contract')
 errors=sorted(set(errors));out={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'reliability_id':'persistent-developer-adversarial-reliability:v1189.8','campaign_id':h.get('campaign_id',''),'work_item_id':h.get('work_item_id',''),'hardening_receipt_digest':hd,'long_session_evidence_digest':ed,'nonce_ledger_digest':n.get('nonce_ledger_digest',''),'current_source_digest':cur,'expected_source_digest':exp,'source_stale':source_stale,'current_nonce_generation':current_nonce_generation,'expected_nonce_generation':expected_nonce_generation,'session_state':session_state,'interruption_count':interruption_count,'privacy_finding_count':len(privacy_findings),'authority_claim_count':len(authority_claims),'status':'operator_review_required' if not errors else 'blocked','errors':errors,'error_count':len(errors),'content_free':True,'automatic_resume':False,'automatic_retry':False,'execution_invoked':False,'provider_contacted':False,'model_contacted':False,'policy_modified':False,'future_work_selection_modified':False,'authority_granted':False}
 out['adversarial_reliability_digest']=_digest(out);return out

def create_reliability_review(*,assessment:Mapping[str,Any],decision:str,action:str,operator_review_digest:str)->dict[str,Any]:
 a=dict(assessment);errors=[];ad,aok=_verify(a,'adversarial_reliability_digest')
 if not aok:errors.append('tampered_assessment')
 if a.get('status')!='operator_review_required':errors.append('assessment_not_reviewable')
 if decision not in {'approve','reject','defer'}:errors.append('unsupported_decision')
 if action not in ALLOWED_ACTIONS:errors.append('unsupported_action')
 if decision!='approve' and action!='hold':errors.append('inactive_decision_requires_hold')
 od=str(operator_review_digest).lower()
 if not DIGEST_RE.fullmatch(od):errors.append('invalid_operator_review_digest')
 errors=sorted(set(errors));out={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'review_id':'persistent-developer-reliability-review:v1189.8','campaign_id':a.get('campaign_id',''),'adversarial_reliability_digest':ad,'decision':decision,'action':action,'operator_review_digest':od,'status':'approved_not_executed' if decision=='approve' and not errors else ('recorded' if not errors else 'blocked'),'errors':errors,'error_count':len(errors),'content_free':True,'recovery_executed':False,'automatic_resume':False,'execution_invoked':False,'authority_granted':False}
 out['reliability_review_digest']=_digest(out);return out

def public_summary(row:Mapping[str,Any])->dict[str,Any]:return {'contract_version':CONTRACT_VERSION,'campaign_id':row.get('campaign_id',''),'status':row.get('status',''),'source_stale':bool(row.get('source_stale')),'session_state':row.get('session_state',''),'error_count':int(row.get('error_count',0) or 0),'content_free':True,'authority_granted':False}
