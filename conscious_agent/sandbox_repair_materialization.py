from __future__ import annotations
"""v1141.3 explicit operator-confirmed work-order claim and isolated workspace materialization."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os, shutil
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from sandbox_repair_work_orders import SandboxRepairWorkOrderStore

CONTRACT_VERSION='v1141.3'; SCHEMA_VERSION='1'
EXACT_CONFIRMATION='I confirm materialization of this exact authorized repair work order.'

def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v, n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,4000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/ 'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'materializations':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_modify_source':False,'can_modify_installation':False,'can_approve':False,'can_authorize':False,'can_install':False,'can_promote':False,'can_certify':False}}

class SandboxRepairMaterializationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):
  self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'sandbox_repair_materializations.json'; self.clock=clock or _now; self.work_orders=SandboxRepairWorkOrderStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def materialize(self,event_id:str,*,work_order_id:str,confirmation:str,operator_id:str,worker_id:str,source_root:str|Path,copy_paths:list[str]|None=None):
  if _clean(confirmation,200)!=EXACT_CONFIRMATION: return {'ok':False,'status':'confirmation_required','reason':'exact_operator_confirmation_mismatch'}
  wo=next((r for r in self.work_orders.snapshot().get('work_orders',[]) if r.get('work_order_id')==_clean(work_order_id)),None)
  if not wo: return {'ok':False,'status':'blocked','reason':'exact_work_order_missing'}
  if wo.get('state')!='ready_for_operator_confirmed_materialization': return {'ok':False,'status':'blocked','reason':'work_order_not_ready'}
  if not wo.get('authorized_bounds_match') or not wo.get('approval_id') or not wo.get('authorization_id'): return {'ok':False,'status':'blocked','reason':'authority_binding_invalid'}
  now=self.clock(); semantic=_digest(work_order_id,wo.get('reviewed_artifact_set_digest'),operator_id,worker_id)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==_clean(event_id,180)),None)
   if prior: return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   active=next((x for x in s['materializations'] if x.get('work_order_id')==work_order_id and x.get('state') in {'materialized','claimed'}),None)
   if active: result={'status':'materialization_reused','materialization_id':active['materialization_id'],'workspace_id':active['workspace_id'],'state':active['state']}
   else:
    mid=f'repair-materialization-{semantic[:24]}'; wid=f'repair-workspace-{_digest(mid)[:24]}'; workspace=(self.runtime_root/'repair_sandboxes'/wid).resolve(); source=Path(source_root).resolve()
    workspace.mkdir(parents=True,exist_ok=False)
    copied=[]
    for rel in sorted(set(copy_paths or [])):
     rp=Path(rel)
     if rp.is_absolute() or '..' in rp.parts: raise ValueError('workspace-relative copy path required')
     src=(source/rp).resolve()
     try: src.relative_to(source)
     except ValueError: raise ValueError('copy path escapes source root')
     if not src.exists() or not src.is_file(): raise ValueError('copy source missing')
     dst=workspace/rp; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst); copied.append({'path_digest':_digest(rp.as_posix()),'content_digest':hashlib.sha256(dst.read_bytes()).hexdigest()})
    row={'materialization_id':mid,'work_order_id':work_order_id,'eligibility_id':wo.get('eligibility_id',''),'reviewed_artifact_set_digest':wo.get('reviewed_artifact_set_digest',''),'approval_id':wo.get('approval_id',''),'authorization_id':wo.get('authorization_id',''),'workspace_id':wid,'workspace_path_digest':_digest(str(workspace)),'workspace_manifest_digest':_digest(*[x['content_digest'] for x in copied]),'copied_file_count':len(copied),'copied_files':copied,'operator_id_digest':_digest(operator_id),'worker_id_digest':_digest(worker_id),'claim_id':f'repair-claim-{_digest(mid,worker_id)[:24]}','execution_token_id':wo.get('execution_token_id',''),'execution_token_consumed':False,'state':'materialized','created_at':now,'updated_at':now,'source_modified':False,'installation_modified':False,'approval_created':False,'authorization_created':False}
    row['structural_digest']=_digest(mid,wid,row['workspace_manifest_digest'],row['claim_id']); s['materializations'].append(row); result={'status':'materialized','materialization_id':mid,'workspace_id':wid,'state':'materialized'}
   s['processed_events'].append({'event_id':_clean(event_id,180),'result':deepcopy(result),'occurred_at':now}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); return {'ok':True,'contract_version':CONTRACT_VERSION,'materialization_count':len(s['materializations']),'recent_materializations':deepcopy(s['materializations'][-24:]),'raw_source_exposed':False,'patch_text_exposed':False,'commands_exposed':False,'logs_exposed':False,'source_modified':False,'installation_modified':False,'approval_created':False,'authorization_created':False,'promotion_created':False,'certification_created':False,'authority_boundary':deepcopy(s['authority_boundary'])}

def build_sandbox_repair_materialization_inspection(runtime_root=None): return SandboxRepairMaterializationStore(runtime_root).inspection_summary()
