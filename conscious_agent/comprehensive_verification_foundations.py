from __future__ import annotations
"""v1295.0-v1295.2 coherent verification evidence foundations.

This layer consumes evidence produced by existing verifiers.  It deliberately
executes nothing and never upgrades missing/native-pending evidence into a pass.
"""
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

CONTRACT_VERSION="v1295.2"
EVIDENCE_DOMAINS=(
 "focused_tests","affected_regressions","python_parse","frozen_source_immutability",
 "fresh_extraction_parity","source_only_package","privacy_security","release_metadata",
 "checkpoint_registry","clean_environment","native_windows",
)
VALID_STATES=frozenset({"passed","failed","blocked","unavailable","pending"})
DENIED_AUTHORITY={
 "verification_execution_authorized":False,"test_execution_authorized":False,"provider_contact_authorized":False,
 "tool_invocation_authorized":False,"command_execution_authorized":False,"project_mutation_authorized":False,
 "source_mutation_authorized":False,"package_mutation_authorized":False,"source_application_authorized":False,
 "self_update_authorized":False,"rollback_authorized":False,"installation_authorized":False,
 "promotion_authorized":False,"certification_authorized":False,"release_authorized":False,
 "standing_authority_granted":False,
}
ARCHITECTURE_LINEAGE={"verification_evidence":"retained","segmented_release_verifier":"v1250","hermetic_runtime":"v1250.2","release_metadata":"v1250.3","checkpoint_registry":"v1250.4","privacy_security":"v1247.9","source_immutability":"v1278","candidate_evaluation":"v1294"}
def digest(v:Any)->str:return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def valid_digest(v:Any)->bool:
 t=str(v or '').lower().strip();return len(t)==64 and all(c in '0123456789abcdef' for c in t)
def evidence_record(domain:str,*,status:str,source_tree_digest:str,candidate_digest:str,evidence_digest:str|None=None,required:bool=True,fresh:bool=True,native:bool=False,native_attested:bool=False,platform_name:str='',summary:Mapping[str,Any]|None=None)->dict[str,Any]:
 domain=str(domain);status=str(status)
 if domain not in EVIDENCE_DOMAINS:raise ValueError('known_verification_domain_required')
 if status not in VALID_STATES:raise ValueError('valid_evidence_state_required')
 if not valid_digest(source_tree_digest) or not valid_digest(candidate_digest):raise ValueError('source_and_candidate_digest_required')
 if status=='passed' and not fresh:raise ValueError('stale_evidence_cannot_pass')
 if domain=='native_windows':
  native=True
  if status=='passed' and (str(platform_name).lower()!='windows' or not native_attested):raise ValueError('native_windows_pass_requires_windows_attestation')
 body={'domain':domain,'status':status,'source_tree_digest':source_tree_digest,'candidate_digest':candidate_digest,'required':bool(required),'fresh':bool(fresh),'native':bool(native),'native_attested':bool(native_attested),'platform_name':str(platform_name).lower(),'summary':dict(summary or {}),'content_free':True}
 supplied=str(evidence_digest or '').lower().strip();body['evidence_digest']=supplied if valid_digest(supplied) else digest(body)
 return body|DENIED_AUTHORITY
def native_windows_pending_evidence(*,source_tree_digest:str,candidate_digest:str,platform_name:str)->dict[str,Any]:
 platform=str(platform_name or '').lower()
 status='pending' if platform!='windows' else 'unavailable'
 return evidence_record('native_windows',status=status,source_tree_digest=source_tree_digest,candidate_digest=candidate_digest,platform_name=platform,native=True,native_attested=False,summary={'native_verification_required':True,'native_pass_claimed':False})
