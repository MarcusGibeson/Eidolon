from __future__ import annotations
"""Bounded scheduling for knowledge and inquiry reconsideration."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib, os
from pathlib import Path
from typing import Any, Callable
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from knowledge_confidence_checkpoint import build_knowledge_confidence_checkpoint
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from knowledge_confidence_checkpoint import build_knowledge_confidence_checkpoint
CONTRACT_VERSION='v1106.3'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,limit=300): return ' '.join(str(v or '').split())[:limit]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(x,2000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _parse(v):
    try:return datetime.fromisoformat(str(v or '').replace('Z','+00:00'))
    except ValueError:return None
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'schedules':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'paused':False,'max_due_per_cycle':3,'max_schedules':256},'authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'can_modify_files':False,'can_browse_externally':False}}
class KnowledgeReconsiderationScheduler:
    def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'knowledge_reconsideration_scheduling.json';self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items():s.setdefault(k,deepcopy(v))
        return s
    def snapshot(self): return deepcopy(self._load())
    def schedule_from_checkpoint(self,event_id,*,now:str|None=None,max_items:int=8):
        event_id=_clean(event_id,160); clock=_parse(now or self.clock()) or datetime.now(timezone.utc)
        if not event_id: raise ValueError('event_id is required')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load();prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_schedule_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
            if s['controls'].get('paused'): result={'status':'scheduling_paused','created_count':0,'action_authorized':False}
            else:
                checkpoint=build_knowledge_confidence_checkpoint(self.runtime_root,now=clock.isoformat())
                candidates=[]
                for row in checkpoint.get('reconsideration_candidates') or []: candidates.append(('belief',row.get('belief_id'),float(row.get('reconsideration_pressure') or 0),row.get('reason_codes') or []))
                for row in checkpoint.get('inquiry_review_candidates') or []: candidates.append(('inquiry',row.get('inquiry_id'),max(float(row.get('uncertainty') or 0),min(1,float(row.get('age_days') or 0)/90)),['aging_or_uncertainty']))
                candidates.sort(key=lambda x:(-x[2],x[0],str(x[1])))
                created=[]
                for kind,item_id,pressure,reasons in candidates[:max(1,int(max_items))]:
                    if not item_id: continue
                    semantic=_digest(kind,item_id)
                    existing=next((r for r in s['schedules'] if r.get('semantic_key')==semantic and r.get('status') in {'scheduled','due','claimed'}),None)
                    if existing: continue
                    delay_days=1 if pressure>=.8 else 7 if pressure>=.6 else 30
                    due=(clock+timedelta(days=delay_days)).isoformat().replace('+00:00','Z')
                    row={'schedule_id':'reconsider-'+_digest(event_id,kind,item_id)[:28],'semantic_key':semantic,'subject_type':kind,'subject_id':item_id,'pressure':round(pressure,4),'reason_codes':list(reasons),'status':'scheduled','scheduled_at':clock.isoformat().replace('+00:00','Z'),'due_at':due,'claimed_at':'','completed_at':'','history':[]}
                    s['schedules'].append(row);created.append(row['schedule_id'])
                s['schedules']=s['schedules'][-int(s['controls'].get('max_schedules') or 256):]
                result={'status':'reconsideration_scheduled','created_count':len(created),'schedule_ids':created,'action_authorized':False,'action_executed':False}
            stamp=self.clock();s['revision']+=1;s['updated_at']=stamp;s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'result':deepcopy(result),'occurred_at':stamp}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def due(self,*,now:str|None=None,limit:int|None=None):
        s=self._load();clock=_parse(now or self.clock()) or datetime.now(timezone.utc);cap=max(1,int(limit or s['controls'].get('max_due_per_cycle') or 3));rows=[]
        for row in s['schedules']:
            due=_parse(row.get('due_at'))
            if row.get('status')=='scheduled' and due and due<=clock: rows.append(deepcopy(row))
        rows.sort(key=lambda r:(-float(r.get('pressure') or 0),str(r.get('due_at') or '')));return rows[:cap]
    def complete(self,event_id,*,schedule_id:str,outcome:str):
        event_id=_clean(event_id,160);schedule_id=_clean(schedule_id,120);outcome=_clean(outcome,240)
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load();prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_completion_ignored','result':deepcopy(prior['result']),'idempotent':True}
            row=next((r for r in s['schedules'] if r.get('schedule_id')==schedule_id),None)
            if not row:raise KeyError('schedule not found')
            now=self.clock();row['status']='completed';row['completed_at']=now;row['history']=(row.get('history') or [])+[{'event':'completed','occurred_at':now,'outcome_digest':_digest(outcome)}];result={'status':'reconsideration_completed','schedule_id':schedule_id,'action_authorized':False,'action_executed':False};s['revision']+=1;s['updated_at']=now;s['processed_events']=(s['processed_events']+[{'event_id':event_id,'result':deepcopy(result),'occurred_at':now}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def set_paused(self,event_id,*,paused:bool):
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load();s['controls']['paused']=bool(paused);s['revision']+=1;s['updated_at']=self.clock();write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':'reconsideration_paused' if paused else 'reconsideration_resumed','paused':bool(paused)}
    def inspection_summary(self):
        s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'scheduled_count':sum(1 for r in s['schedules'] if r.get('status')=='scheduled'),'completed_count':sum(1 for r in s['schedules'] if r.get('status')=='completed'),'due_count':len(self.due()),'recent_schedules':deepcopy(s['schedules'][-8:]),'controls':deepcopy(s['controls']),'provider_contacted':False,'external_browsing_performed':False,'authority_boundary':deepcopy(s['authority_boundary'])}
def build_reconsideration_scheduling_inspection(runtime_root=None): return KnowledgeReconsiderationScheduler(runtime_root).inspection_summary()
