from __future__ import annotations
"""v1141.4 bounded sandbox candidate-change, command, and test execution."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, os, subprocess
from pathlib import Path
from typing import Any
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from sandbox_repair_materialization import SandboxRepairMaterializationStore

CONTRACT_VERSION='v1141.4'; SCHEMA_VERSION='1'; EXACT_CONFIRMATION='I confirm execution inside this exact isolated repair workspace.'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,4000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/ 'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'executions':[],'processed_events':[],'revision':0,'updated_at':''}
class SandboxRepairExecutionStore:
 def __init__(self,runtime_root=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'sandbox_repair_executions.json'; self.materializations=SandboxRepairMaterializationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def execute(self,event_id:str,*,materialization_id:str,confirmation:str,changes:list[dict[str,Any]],commands:list[list[str]],test_commands:list[list[str]],timeout_seconds:int=60,max_output_bytes:int=65536,cancelled:bool=False):
  if _clean(confirmation,200)!=EXACT_CONFIRMATION: return {'ok':False,'status':'confirmation_required'}
  mat=next((r for r in self.materializations.snapshot().get('materializations',[]) if r.get('materialization_id')==_clean(materialization_id)),None)
  if not mat or mat.get('state')!='materialized' or mat.get('execution_token_consumed'): return {'ok':False,'status':'blocked','reason':'materialization_not_executable'}
  workspace=(self.runtime_root/'repair_sandboxes'/mat['workspace_id']).resolve(); timeout_seconds=max(1,min(int(timeout_seconds),3600)); max_output_bytes=max(1024,min(int(max_output_bytes),1048576)); now=_now()
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==_clean(event_id,180)),None)
   if prior: return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   eid=f'repair-execution-{_digest(materialization_id,event_id)[:24]}'; applied=[]; results=[]; status='cancelled' if cancelled else 'completed'
   if not cancelled:
    for change in changes:
     rel=Path(str(change.get('path') or ''))
     if rel.is_absolute() or '..' in rel.parts: raise ValueError('workspace-relative change path required')
     target=(workspace/rel).resolve(); target.relative_to(workspace); before_bytes=target.read_bytes() if target.exists() else None; before=hashlib.sha256(before_bytes).hexdigest() if before_bytes is not None else ''
     backup=(workspace/'.repair_rollback'/eid/rel); backup.parent.mkdir(parents=True,exist_ok=True)
     if before_bytes is not None: backup.write_bytes(before_bytes)
     content=str(change.get('content') or ''); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(content,encoding='utf-8'); after=hashlib.sha256(target.read_bytes()).hexdigest(); applied.append({'path_digest':_digest(rel.as_posix()),'relative_path':rel.as_posix(),'before_digest':before,'after_digest':after,'previously_existed':before_bytes is not None})
    for category, rows in [('command',commands),('test',test_commands)]:
     for argv in rows:
      if not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x for x in argv): raise ValueError('argv list required')
      try:
       cp=subprocess.run(argv,cwd=workspace,text=True,capture_output=True,timeout=timeout_seconds,env={'PATH':os.environ.get('PATH',''),'PYTHONDONTWRITEBYTECODE':'1'})
       out=(cp.stdout+cp.stderr).encode()[:max_output_bytes]; results.append({'category':category,'argv_digest':_digest(*argv),'returncode':cp.returncode,'output_digest':hashlib.sha256(out).hexdigest(),'output_bytes':len(out),'timed_out':False})
       if cp.returncode!=0: status='failed'
      except subprocess.TimeoutExpired as exc:
       data=((exc.stdout or '')+(exc.stderr or '')).encode()[:max_output_bytes] if isinstance(exc.stdout,str) else b''; results.append({'category':category,'argv_digest':_digest(*argv),'returncode':None,'output_digest':hashlib.sha256(data).hexdigest(),'output_bytes':len(data),'timed_out':True}); status='timed_out'
   row={'execution_id':eid,'materialization_id':materialization_id,'workspace_id':mat['workspace_id'],'candidate_change_id':f'candidate-change-{_digest(eid,*[x["after_digest"] for x in applied])[:24]}','applied_changes':applied,'result_records':results,'command_count':len(commands),'test_count':len(test_commands),'status':status,'cancelled':cancelled,'timeout_seconds':timeout_seconds,'max_output_bytes':max_output_bytes,'created_at':now,'source_modified':False,'installation_modified':False,'approval_created':False,'authorization_created':False,'promotion_created':False,'certification_created':False}
   row['structural_digest']=_digest(eid,status,*[x['output_digest'] for x in results]); s['executions'].append(row); result={'status':status,'execution_id':eid,'candidate_change_id':row['candidate_change_id'],'result_count':len(results)}; s['processed_events'].append({'event_id':_clean(event_id,180),'result':deepcopy(result),'occurred_at':now}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   ms=self.materializations._load(); mr=next(x for x in ms['materializations'] if x['materialization_id']==materialization_id); mr['execution_token_consumed']=True; mr['state']='executed'; mr['updated_at']=now; write_json_atomic(self.materializations.path,ms,expected_type=dict,sort_keys=True)
   return {'ok':True,**result,'idempotent':False}
 def rollback(self,event_id:str,*,execution_id:str,confirmation:str):
  if _clean(confirmation,200)!=EXACT_CONFIRMATION: return {'ok':False,'status':'confirmation_required'}
  ex=next((r for r in self.snapshot().get('executions',[]) if r.get('execution_id')==execution_id),None)
  if not ex: return {'ok':False,'status':'blocked'}
  workspace=(self.runtime_root/'repair_sandboxes'/ex['workspace_id']).resolve()
  for item in ex.get('applied_changes',[]):
   rel=Path(item['relative_path']); target=(workspace/rel).resolve(); target.relative_to(workspace); backup=workspace/'.repair_rollback'/execution_id/rel
   if item.get('previously_existed'): target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(backup.read_bytes())
   elif target.exists(): target.unlink()
  return {'ok':True,'status':'rollback_completed','rollback_id':f'repair-rollback-{_digest(execution_id,event_id)[:24]}','source_modified':False,'installation_modified':False}
 def inspection_summary(self):
  s=self._load(); return {'ok':True,'contract_version':CONTRACT_VERSION,'execution_count':len(s['executions']),'recent_executions':deepcopy(s['executions'][-24:]),'patch_text_exposed':False,'commands_exposed':False,'logs_exposed':False,'source_modified':False,'installation_modified':False,'approval_created':False,'authorization_created':False,'promotion_created':False,'certification_created':False}
def build_sandbox_repair_execution_inspection(runtime_root=None): return SandboxRepairExecutionStore(runtime_root).inspection_summary()
