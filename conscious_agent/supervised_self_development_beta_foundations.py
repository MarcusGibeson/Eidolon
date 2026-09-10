from __future__ import annotations
"""v1300.0-v1300.2 foundations for the supervised self-development beta.

This is a consolidation contract over established supervised-development
capabilities.  The contract itself never executes an update or grants standing
self-development authority.
"""
from hashlib import sha256
import json
from typing import Any, Mapping

CONTRACT_VERSION="v1300.2"
BETA_STAGES=(
 "inspect","propose","deliberate","plan","compare_candidates","isolated_build","verify",
 "diagnose","repair","reverify","review","authorization_request","governed_update","post_update_recovery",
)
DENIED_AUTHORITY={
 "provider_contact_authorized":False,"command_execution_authorized":False,"test_execution_authorized":False,
 "repair_execution_authorized":False,"project_mutation_authorized":False,"source_mutation_authorized":False,
 "source_application_authorized":False,"self_update_authorized":False,"rollback_authorized":False,
 "installation_authorized":False,"promotion_authorized":False,"certification_authorized":False,
 "release_authorized":False,"standing_authority_granted":False,"permanent_authority_granted":False,
 "autonomous_authority_granted":False,
}
ARCHITECTURE_LINEAGE={
 "inspection":"v1261","proposal":"v1291","deliberation":"v1292","planning":"v1285-v1286",
 "campaign":"v1293","candidate_comparison":"v1294","verification":"v1295","canary":"v1296",
 "recovery":"v1297","repeated_cycles":"v1298","final_rehearsal":"v1299","operator_review":"v1268",
 "governed_update":"v1269",
}

def digest(v:Any)->str:
 return sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()

def valid_digest(v:Any)->bool:
 t=str(v or '').strip().lower();return len(t)==64 and all(c in '0123456789abcdef' for c in t)

def seal_beta_identity(*,objective_digest:str,baseline_source_digest:str,candidate_source_digest:str,
 proposal_digest:str,deliberation_digest:str,plan_digest:str,candidate_evaluation_digest:str,
 verification_digest:str,review_digest:str,rehearsal_digest:str)->dict[str,Any]:
 values=(objective_digest,baseline_source_digest,candidate_source_digest,proposal_digest,deliberation_digest,plan_digest,candidate_evaluation_digest,verification_digest,review_digest,rehearsal_digest)
 if not all(valid_digest(x) for x in values):raise ValueError('sealed_beta_lineage_required')
 if baseline_source_digest==candidate_source_digest:raise ValueError('changed_candidate_required')
 body={'contract_version':CONTRACT_VERSION,'objective_digest':objective_digest,'baseline_source_digest':baseline_source_digest,'candidate_source_digest':candidate_source_digest,'proposal_digest':proposal_digest,'deliberation_digest':deliberation_digest,'plan_digest':plan_digest,'candidate_evaluation_digest':candidate_evaluation_digest,'verification_digest':verification_digest,'review_digest':review_digest,'rehearsal_digest':rehearsal_digest,'architecture_lineage':dict(ARCHITECTURE_LINEAGE),'active_installation_is_disposable_fixture':False,'content_free':True}
 body['beta_id']='selfdevbeta_'+digest(body)[:24];body['identity_digest']=digest(body);return body|DENIED_AUTHORITY

def beta_step(identity:Mapping[str,Any],*,sequence:int,stage:str,evidence_digest:str,source_digest:str,prior_step_digest:str='',result:str='recorded')->dict[str,Any]:
 stage=str(stage);seq=int(sequence)
 if stage not in BETA_STAGES or seq<1 or seq>len(BETA_STAGES):raise ValueError('known_bounded_beta_stage_required')
 if not valid_digest(identity.get('identity_digest')) or not valid_digest(evidence_digest) or not valid_digest(source_digest):raise ValueError('sealed_beta_step_required')
 if prior_step_digest and not valid_digest(prior_step_digest):raise ValueError('valid_prior_step_digest_required')
 row={'contract_version':CONTRACT_VERSION,'beta_id':identity.get('beta_id'),'identity_digest':identity.get('identity_digest'),'sequence':seq,'stage':stage,'evidence_digest':evidence_digest,'source_digest':source_digest,'prior_step_digest':str(prior_step_digest or ''),'result':str(result),'content_free':True};row['step_digest']=digest(row);return row|DENIED_AUTHORITY
