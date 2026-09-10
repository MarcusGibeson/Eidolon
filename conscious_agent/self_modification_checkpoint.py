from __future__ import annotations
"""v1390 consolidated bounded self-modification checkpoint contract."""
import hashlib,json,re
from typing import Any,Mapping
CONTRACT_VERSION='v1390.8';DIGEST=re.compile(r'^[a-f0-9]{64}$')
DENIED={'automatic_self_modification_authorized':False,'unreviewed_source_mutation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _sealed(rec:Mapping[str,Any],field:str,expected:str)->bool:
 row=dict(rec or {});sup=str(row.pop(field,''));return bool(DIGEST.fullmatch(expected or '') and sup==expected and sup==_d(row))
def build_self_modification_checkpoint(*,self_model:Mapping[str,Any],self_model_digest:str,self_improvement_backlog:Mapping[str,Any],backlog_digest:str,self_change_workspace:Mapping[str,Any],protected_scope:Mapping[str,Any],dogfood_verification:Mapping[str,Any],shadow_execution:Mapping[str,Any],canary_self_update:Mapping[str,Any],self_update_transaction:Mapping[str,Any],update_lineage:Mapping[str,Any])->dict[str,Any]:
 checks={
  'self_model_sealed':_sealed(self_model,'self_model_digest',self_model_digest),
  'backlog_sealed':_sealed(self_improvement_backlog,'backlog_digest',backlog_digest),
  'protected_scope_sealed':_sealed(protected_scope,'scope_digest',str(protected_scope.get('scope_digest') or '')),
  'dogfood_sealed':_sealed(dogfood_verification,'verification_digest',str(dogfood_verification.get('verification_digest') or '')),
  'shadow_sealed':_sealed(shadow_execution,'shadow_digest',str(shadow_execution.get('shadow_digest') or '')),
  'canary_sealed':_sealed(canary_self_update,'canary_digest',str(canary_self_update.get('canary_digest') or '')),
  'transaction_sealed':_sealed(self_update_transaction,'transaction_digest',str(self_update_transaction.get('transaction_digest') or '')),
  'lineage_sealed':_sealed(update_lineage,'lineage_digest',str(update_lineage.get('lineage_digest') or '')),
 }
 cid=str(self_change_workspace.get('candidate_id') or '')
 checks.update({
  'backlog_bound_to_self_model':self_improvement_backlog.get('self_model_digest')==self_model_digest,
  'workspace_bound_to_self_model':self_change_workspace.get('self_model_digest')==self_model_digest,
  'candidate_lineage_consistent':bool(cid) and dogfood_verification.get('candidate_id')==cid and shadow_execution.get('candidate_id')==cid and canary_self_update.get('candidate_id')==cid and update_lineage.get('candidate_id')==cid,
  'dogfood_passed':int(dogfood_verification.get('failed') or 0)==0 and bool(dogfood_verification.get('candidate_installable')),
  'shadow_no_regressions':int(shadow_execution.get('regression_count') or 0)==0 and bool(shadow_execution.get('shadow_only')),
  'canary_passed':bool(canary_self_update.get('canary_passed')),
  'transaction_safe':bool(self_update_transaction.get('health_passed')) or bool(self_update_transaction.get('rollback_verified')),
  'transaction_lineage_bound':update_lineage.get('transaction_digest')==self_update_transaction.get('transaction_digest'),
  'canary_lineage_bound':update_lineage.get('canary_digest')==canary_self_update.get('canary_digest'),
  'protected_apply_not_automatic':not bool(protected_scope.get('automatic_apply_allowed')),
 })
 ok=all(checks.values());core={'contract_version':CONTRACT_VERSION,'candidate_id':cid,'self_model_digest':self_model_digest,'backlog_digest':backlog_digest,'workspace_lineage_digest':self_change_workspace.get('lineage_digest'),'scope_digest':protected_scope.get('scope_digest'),'dogfood_digest':dogfood_verification.get('verification_digest'),'shadow_digest':shadow_execution.get('shadow_digest'),'canary_digest':canary_self_update.get('canary_digest'),'transaction_digest':self_update_transaction.get('transaction_digest'),'update_lineage_digest':update_lineage.get('lineage_digest'),'checks':checks,'passed':sum(bool(x) for x in checks.values()),'total':len(checks),'self_modification_checkpoint_passed':ok,'successful_update_observed':bool(self_update_transaction.get('health_passed')),'safe_rollback_observed':bool(self_update_transaction.get('rollback_verified')),'operator_supervision_required':True,'content_free':True,'action_executed':False,**DENIED};core['checkpoint_digest']=_d(core)
 return {'ok':ok,'status':'self_modification_checkpoint_passed' if ok else 'self_modification_checkpoint_blocked','self_modification_checkpoint':core,'action_executed':False,**DENIED}
def process_self_modification_checkpoint_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show self modification checkpoint','inspect self modification checkpoint','show self modification status'}:return {'active':False}
 rec=dict((project_state or {}).get('self_modification_checkpoint') or {});return {'active':True,'ok':bool(rec),'status':'self_modification_checkpoint_found' if rec else 'self_modification_checkpoint_missing','self_modification_checkpoint':rec,'action_executed':False,**DENIED}
