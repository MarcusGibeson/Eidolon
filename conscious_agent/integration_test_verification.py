from __future__ import annotations
"""v1354 real-boundary integration verification in disposable workspaces."""
import hashlib,json,re,time
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Sequence
from cognitive_coding_foundations import digest
from ordinary_chat_development_campaign import _atomic_json,_read_json,_store_root
from typed_process_operations import start_candidate_process,monitor_candidate_process,stop_candidate_process
from workspace_isolation import _record_path as _workspace_record_path
CONTRACT_VERSION='v1354.8';TERMINAL={'completed','failed','cancelled','interrupted','uncertain'}
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False}
def _root(r=None):p=_store_root(r)/'phase6_integration_verification';p.mkdir(parents=True,exist_ok=True);return p
def _path(i,r=None):
 if not re.fullmatch(r'intv_[a-f0-9]{24}',str(i or '')):raise ValueError('invalid_integration_verification_id')
 return _root(r)/(i+'.json')
def _safe_rel(v:str)->str:
 p=PurePosixPath(str(v or '').replace('\\','/'))
 if p.is_absolute() or not p.parts or any(x in {'','..'} for x in p.parts):raise ValueError('unsafe_artifact_path')
 return p.as_posix()
def _workspace(i,r=None):
 try:x=_read_json(_workspace_record_path(i,r))
 except Exception:return {}
 if not x or x.get('record_digest')!=digest({k:v for k,v in x.items() if k!='record_digest'}) or x.get('cleaned') or not x.get('workspace_created'):return {}
 return x
def run_integration_verification(workspace_id:str,argv:Sequence[str],*,active_grant:Mapping[str,Any],precondition_record_id:str,expected_artifacts:Sequence[Mapping[str,Any]]=(),runtime_root=None,now_unix:int|None=None,timeout_seconds:float=20)->dict[str,Any]:
 ws=_workspace(workspace_id,runtime_root)
 if not ws:return {'ok':False,'status':'integration_workspace_required','action_executed':False,**DENIED}
 try:
  expected=[]
  for raw in expected_artifacts:
   rel=_safe_rel(str(raw.get('relative_path') or ''));sha=str(raw.get('sha256') or '')
   if sha and not re.fullmatch(r'[a-f0-9]{64}',sha):raise ValueError('artifact_digest_invalid')
   expected.append({'relative_path_digest':hashlib.sha256(rel.encode()).hexdigest(),'relative_path':rel,'sha256':sha,'must_exist':raw.get('must_exist',True) is not False})
  timeout=float(timeout_seconds)
  if timeout<=0 or timeout>120:raise ValueError('integration_timeout_invalid')
 except (TypeError,ValueError) as exc:return {'ok':False,'status':str(exc),'action_executed':False,**DENIED}
 material={'contract':CONTRACT_VERSION,'workspace':workspace_id,'argv':[hashlib.sha256(str(x).encode()).hexdigest() for x in argv],'expected':[{'path':x['relative_path_digest'],'sha256':x['sha256'],'must_exist':x['must_exist']} for x in expected],'precondition':precondition_record_id}
 iid='intv_'+digest(material)[:24]
 try:existing=_read_json(_path(iid,runtime_root))
 except Exception:existing={}
 if existing and existing.get('record_digest')==digest({k:v for k,v in existing.items() if k!='record_digest'}):return {'ok':existing.get('verification_passed') is True,'status':'integration_verification_already_exists','integration_verification':_public(existing),'action_executed':False,**DENIED}
 env={'EIDOLON_RUNTIME_ROOT':str(ws.get('runtime_data_private_path') or '')}
 started=start_candidate_process(workspace_id,argv,active_grant=active_grant,precondition_record_id=precondition_record_id,environment=env,timeout_seconds=timeout,runtime_root=runtime_root,now_unix=now_unix,invocation_discriminator=f'v1354:{iid}')
 if not started.get('ok'):return {'ok':False,'status':'integration_process_start_failed','action_executed':False,**DENIED}
 op=str((started.get('process_operation') or {}).get('process_operation_id') or '');deadline=time.monotonic()+timeout+5;observed={}
 while time.monotonic()<deadline:
  observed=monitor_candidate_process(op,runtime_root=runtime_root);state=str((observed.get('process_operation') or {}).get('process_state') or '')
  if state in TERMINAL:break
  time.sleep(.03)
 proc=observed.get('process_operation') or {}
 if str(proc.get('process_state') or '') not in TERMINAL:
  stop_candidate_process(op,active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix);proc=(monitor_candidate_process(op,runtime_root=runtime_root).get('process_operation') or {})
 candidate=Path(str(ws.get('candidate_private_path') or ''));checks=[];artifacts_ok=True
 for spec in expected:
  p=candidate/spec['relative_path'];exists=p.is_file();actual=hashlib.sha256(p.read_bytes()).hexdigest() if exists else '';ok=(exists if spec['must_exist'] else not exists) and (not spec['sha256'] or actual==spec['sha256']);artifacts_ok=artifacts_ok and ok;checks.append({'relative_path_digest':spec['relative_path_digest'],'exists':exists,'digest_matches':bool(not spec['sha256'] or actual==spec['sha256']),'ok':ok})
 passed=proc.get('process_state')=='completed' and proc.get('return_code')==0 and not proc.get('timed_out') and not proc.get('log_limit_exceeded') and artifacts_ok
 rec={'contract_version':CONTRACT_VERSION,'integration_verification_id':iid,'workspace_id':workspace_id,'source_workspace_digest':ws.get('source_workspace_digest'),'process_operation_id':op,'process_state':proc.get('process_state'),'return_code':proc.get('return_code'),'timed_out':proc.get('timed_out') is True,'log_limit_exceeded':proc.get('log_limit_exceeded') is True,'artifact_checks':checks,'artifact_count':len(checks),'controlled_runtime_root':True,'real_process_boundary_exercised':True,'mock_only':False,'verification_passed':passed,'content_free':True,'action_executed':True,**DENIED};rec['record_digest']=digest(rec);_atomic_json(_path(iid,runtime_root),rec);return {'ok':passed,'status':'integration_verification_passed' if passed else 'integration_verification_failed','integration_verification':_public(rec),'action_executed':True,**DENIED}
def _public(r):return {k:r.get(k) for k in ('contract_version','integration_verification_id','workspace_id','source_workspace_digest','process_operation_id','process_state','return_code','timed_out','log_limit_exceeded','artifact_checks','artifact_count','controlled_runtime_root','real_process_boundary_exercised','mock_only','verification_passed','content_free','record_digest','action_executed')}|DENIED
def load_integration_verification(i:str,*,runtime_root=None):
 try:r=_read_json(_path(i,runtime_root))
 except Exception:return {}
 if not r or r.get('record_digest')!=digest({k:v for k,v in r.items() if k!='record_digest'}):return {}
 return _public(r)
def process_integration_verification_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show integration verification','inspect integration verification','show integration tests'}:return {'active':False}
 i=str((project_state or {}).get('integration_verification_id') or '');r=load_integration_verification(i,runtime_root=runtime_root) if i else {};return {'active':True,'ok':bool(r),'status':'integration_verification_found' if r else 'integration_verification_missing','integration_verification':r,'action_executed':False,**DENIED}
