from __future__ import annotations
"""v1300.3-v1300.5 portable evidence reducer for supervised self-development beta."""
from typing import Any,Iterable,Mapping
from supervised_self_development_beta_foundations import ARCHITECTURE_LINEAGE,BETA_STAGES,DENIED_AUTHORITY,digest,valid_digest
CONTRACT_VERSION='v1300.5'

def _seal_payload(row:Mapping[str,Any],field:str)->dict[str,Any]:return {k:v for k,v in dict(row).items() if k!=field and k not in DENIED_AUTHORITY}

def evaluate_supervised_self_development_beta(identity:Mapping[str,Any],steps:Iterable[Mapping[str,Any]],*,update_evidence:Mapping[str,Any],recovery_evidence:Mapping[str,Any],native_windows_status:str='pending')->dict[str,Any]:
 ident=dict(identity);rows=[dict(x) for x in steps];viol=[];prior='';seen=set()
 if not valid_digest(ident.get('identity_digest')) or not str(ident.get('beta_id') or '').startswith('selfdevbeta_'):viol.append('invalid_beta_identity')
 if any(bool(ident.get(k)) for k in DENIED_AUTHORITY):viol.append('identity_authority_expansion')
 for row in rows:
  seq=int(row.get('sequence') or 0);stage=str(row.get('stage') or '')
  if seq in seen:viol.append(f'duplicate_sequence:{seq}')
  seen.add(seq)
  expected=BETA_STAGES[seq-1] if 1<=seq<=len(BETA_STAGES) else ''
  if stage!=expected:viol.append(f'stage_sequence_mismatch:{seq}:{stage}')
  if row.get('beta_id')!=ident.get('beta_id') or row.get('identity_digest')!=ident.get('identity_digest'):viol.append(f'step_identity_mismatch:{seq}')
  if row.get('step_digest')!=digest(_seal_payload(row,'step_digest')):viol.append(f'step_digest_mismatch:{seq}')
  if str(row.get('prior_step_digest') or '')!=prior:viol.append(f'step_chain_mismatch:{seq}')
  if any(bool(row.get(k)) for k in DENIED_AUTHORITY):viol.append(f'step_authority_expansion:{seq}')
  if stage in {'inspect','propose','deliberate','plan'} and row.get('source_digest')!=ident.get('baseline_source_digest'):viol.append(f'baseline_lineage_mismatch:{stage}')
  if stage in {'compare_candidates','isolated_build','verify','diagnose','repair','reverify','review','authorization_request','governed_update'} and row.get('source_digest')!=ident.get('candidate_source_digest'):viol.append(f'candidate_lineage_mismatch:{stage}')
  if stage=='post_update_recovery' and row.get('source_digest')!=ident.get('baseline_source_digest'):viol.append('recovery_baseline_lineage_mismatch')
  prior=str(row.get('step_digest') or '')
 if len(rows)!=len(BETA_STAGES):viol.append('incomplete_beta_stage_set')
 u=dict(update_evidence);r=dict(recovery_evidence)
 required_update={
  'disposable_source_fixture':True,'generic_authorization_rejected':True,'exact_authorization_consumed':True,
  'governed_update_verified':True,'candidate_installed_before_recovery':True,'release_authorized':False,
  'standing_authority_granted':False,
 }
 for k,v in required_update.items():
  if u.get(k) is not v:viol.append(f'update_evidence_invalid:{k}')
 if not valid_digest(u.get('update_result_digest')):viol.append('update_result_digest_missing')
 required_recovery={
  'defined_failure_triggered':True,'automatic_recovery_completed':True,'baseline_restored':True,
  'new_update_authorization_consumed':False,'general_rollback_authorized':False,'release_authorized':False,
 }
 for k,v in required_recovery.items():
  if r.get(k) is not v:viol.append(f'recovery_evidence_invalid:{k}')
 if not valid_digest(r.get('recovery_result_digest')):viol.append('recovery_result_digest_missing')
 native=str(native_windows_status or 'pending')
 if native not in {'pending','unavailable'}:viol.append('portable_beta_cannot_self_attest_native_windows')
 ready=not viol
 out={'contract_version':CONTRACT_VERSION,'ok':ready,'status':'supervised_self_development_beta_portable_ready_native_pending' if ready else 'supervised_self_development_beta_blocked','beta_id':ident.get('beta_id',''),'stage_count':len(rows),'stage_sequence':[x.get('stage') for x in rows],'update_evidence':{k:u.get(k) for k in required_update}|{'update_result_digest':u.get('update_result_digest','')},'recovery_evidence':{k:r.get(k) for k in required_recovery}|{'recovery_result_digest':r.get('recovery_result_digest','')},'integrity_violations':viol,'native_windows_status':native,'native_windows_certified':False,'active_installed_eidolon_modified':False,'exact_authorization_was_fixture_bound':True,'generic_authorization_phrase_is_sufficient':False,'rollback_remains_separately_governed_for_successful_operator_rollback':True,'roadmap_complete_through_v1300':ready,'architecture_lineage':dict(ARCHITECTURE_LINEAGE),'content_free':True,'read_only':True,**DENIED_AUTHORITY};out['beta_digest']=digest(out);return out
