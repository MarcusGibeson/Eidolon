from __future__ import annotations
"""v1365 bounded iterative repair loop inside an existing disposable workspace."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
from structured_file_operations import patch_candidate_file
from integration_test_verification import run_integration_verification
CONTRACT_VERSION='v1365.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'application_authorized':False}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def run_iterative_repair_loop(workspace_id:str,*,attempts:Sequence[Mapping[str,Any]],active_grant:Mapping[str,Any],file_precondition_record_id:str,shell_precondition_record_id:str,runtime_root=None,now_unix:int|None=None,max_attempts:int=3)->dict[str,Any]:
 try:limit=int(max_attempts)
 except Exception:return {'ok':False,'status':'repair_attempt_budget_invalid','action_executed':False,**DENIED}
 if limit<1 or limit>5 or not attempts or len(attempts)>limit:return {'ok':False,'status':'repair_attempt_budget_invalid','action_executed':False,**DENIED}
 rows=[];seen=set();stop='attempts_exhausted';success=False
 for idx,raw in enumerate(attempts,1):
  strategy=str(raw.get('strategy_digest') or '')
  if not re.fullmatch(r'[a-f0-9]{64}',strategy):stop='strategy_evidence_invalid';break
  if strategy in seen:stop='repeated_strategy_blocked';break
  if raw.get('evidence_supports_attempt') is not True:stop='evidence_exhausted';break
  seen.add(strategy)
  path=str(raw.get('relative_path') or '');expected=str(raw.get('expected_content_digest') or '');patches=list(raw.get('patches') or []);argv=list(raw.get('test_argv') or [])
  if not path or not re.fullmatch(r'[a-f0-9]{64}',expected) or not patches or not argv:stop='repair_attempt_invalid';break
  patched=patch_candidate_file(workspace_id,path,expected_content_digest=expected,patches=patches,active_grant=active_grant,precondition_record_id=file_precondition_record_id,runtime_root=runtime_root,now_unix=now_unix)
  if not patched.get('ok'):
   rows.append({'attempt':idx,'strategy_digest':strategy,'patch_applied':False,'verification_passed':False,'status':'patch_failed'});stop='patch_failed';break
  verified=run_integration_verification(workspace_id,argv,active_grant=active_grant,precondition_record_id=shell_precondition_record_id,expected_artifacts=list(raw.get('expected_artifacts') or []),runtime_root=runtime_root,now_unix=now_unix,timeout_seconds=float(raw.get('timeout_seconds') or 20))
  passed=verified.get('ok') is True
  rows.append({'attempt':idx,'strategy_digest':strategy,'patch_applied':True,'file_operation_id':(patched.get('file_operation') or {}).get('operation_id'),'verification_id':(verified.get('integration_verification') or {}).get('integration_verification_id'),'verification_passed':passed,'status':'passed' if passed else 'failed'})
  if passed:success=True;stop='repair_succeeded';break
 rec={'contract_version':CONTRACT_VERSION,'workspace_id':workspace_id,'attempt_count':len(rows),'max_attempts':limit,'attempts':rows,'repair_succeeded':success,'stop_reason':stop,'distinct_strategy_count':len(seen),'selected_source_modified':False,'candidate_only_mutation':True,'automatic_source_application':False,'content_free':True,'action_executed':bool(rows),**DENIED};rec['record_digest']=_d(rec)
 return {'ok':success,'status':stop,'iterative_repair_loop':rec,'action_executed':bool(rows),**DENIED}
def process_iterative_repair_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show iterative repair','inspect repair loop','show repair loop'}:return {'active':False}
 rec=dict((project_state or {}).get('iterative_repair_loop') or {});return {'active':True,'ok':bool(rec),'status':'iterative_repair_loop_found' if rec else 'iterative_repair_loop_missing','iterative_repair_loop':rec,'action_executed':False,**DENIED}
