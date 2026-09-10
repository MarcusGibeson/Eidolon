from __future__ import annotations
"""v1141.6 durable repair execution continuity and restart reconciliation."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from sandbox_repair_materialization import SandboxRepairMaterializationStore
from sandbox_repair_execution import SandboxRepairExecutionStore

CONTRACT_VERSION='v1141.6'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,4000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'reconciliations':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_execute':False,'can_modify_source':False,'can_modify_installation':False,'can_approve':False,'can_authorize':False,'can_install':False,'can_promote':False,'can_certify':False}}
class RepairExecutionContinuityStore:
 def __init__(self,runtime_root=None):
  self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'repair_execution_continuity.json'; self.materializations=SandboxRepairMaterializationStore(self.runtime_root); self.executions=SandboxRepairExecutionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def reconcile(self,event_id:str,*,worker_id:str='reconciler',stale_materialization_ids:list[str]|None=None,interrupted_execution_ids:list[str]|None=None):
  now=_now(); stale=set(_clean(x) for x in (stale_materialization_ids or [])); interrupted=set(_clean(x) for x in (interrupted_execution_ids or []))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==_clean(event_id,180)),None)
   if prior: return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   mats=self.materializations.snapshot().get('materializations',[]); exs=self.executions.snapshot().get('executions',[]); rows=[]
   by_mat={x.get('materialization_id'):x for x in exs}
   for m in mats:
    mid=m.get('materialization_id',''); ex=by_mat.get(mid); state='completed' if ex and ex.get('status')=='completed' else 'failed' if ex and ex.get('status') in {'failed','timed_out'} else 'cancelled' if ex and ex.get('status')=='cancelled' else 'stale_claim_released' if mid in stale else 'interrupted' if ex and ex.get('execution_id') in interrupted else 'awaiting_execution' if m.get('state')=='materialized' else 'reconciled'
    row={'continuity_id':f'repair-continuity-{_digest(mid,event_id)[:24]}','materialization_id':mid,'execution_id':(ex or {}).get('execution_id',''),'work_order_id':m.get('work_order_id',''),'workspace_id':m.get('workspace_id',''),'reviewed_artifact_set_digest':m.get('reviewed_artifact_set_digest',''),'approval_id':m.get('approval_id',''),'authorization_id':m.get('authorization_id',''),'worker_id_digest':_digest(worker_id),'state':state,'restart_safe':True,'stale_worker_suppressed':mid in stale,'duplicate_suppressed':True,'source_modified':False,'installation_modified':False,'created_at':now}
    row['structural_digest']=_digest(*[row[k] for k in ('continuity_id','materialization_id','execution_id','state','reviewed_artifact_set_digest')]); rows.append(row)
   rid=f'repair-reconciliation-{_digest(event_id,*[r["structural_digest"] for r in rows])[:24]}'; rec={'reconciliation_id':rid,'record_count':len(rows),'records':rows,'created_at':now,'structural_digest':_digest(rid,*[r['structural_digest'] for r in rows])}
   s['reconciliations'].append(rec); result={'status':'reconciled','reconciliation_id':rid,'record_count':len(rows)}; s['processed_events'].append({'event_id':_clean(event_id,180),'result':deepcopy(result),'occurred_at':now}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); recent=s['reconciliations'][-12:]; return {'ok':True,'contract_version':CONTRACT_VERSION,'reconciliation_count':len(s['reconciliations']),'recent_reconciliations':deepcopy(recent),'restart_safe':True,'stale_worker_suppression':True,'duplicate_suppression':True,'raw_source_exposed':False,'patch_text_exposed':False,'commands_exposed':False,'logs_exposed':False,'hidden_reasoning_exposed':False,'source_modified':False,'installation_modified':False,'approval_created':False,'authorization_created':False,'promotion_created':False,'certification_created':False,'authority_boundary':deepcopy(s['authority_boundary'])}
def build_repair_execution_continuity_inspection(runtime_root=None): return RepairExecutionContinuityStore(runtime_root).inspection_summary()
