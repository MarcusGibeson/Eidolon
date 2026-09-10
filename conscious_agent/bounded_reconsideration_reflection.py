from __future__ import annotations
"""Consume one due reconsideration and store one concise authored conclusion or silence."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
    from belief_revision import BeliefRevisionStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
    from belief_revision import BeliefRevisionStore
CONTRACT_VERSION='v1106.6'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,l=500): return ' '.join(str(v or '').split())[:l]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'reflections':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'paused':False,'max_reflections_per_cycle':1,'max_total':256},'authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'can_modify_files':False,'can_browse_externally':False}}
class BoundedReconsiderationReflection:
    def __init__(self,runtime_root=None,*,scheduler=None,beliefs=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'bounded_reconsideration_reflection.json'; self.scheduler=scheduler or KnowledgeReconsiderationScheduler(self.runtime_root); self.beliefs=beliefs or BeliefRevisionStore(self.runtime_root)
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items(): s.setdefault(k,deepcopy(v))
        return s
    def reflect(self,event_id,*,schedule_id:str='',conclusion:str='',select_silence:bool=False):
        event_id=_clean(event_id,160); conclusion=_clean(conclusion,420)
        if not event_id: raise ValueError('event_id is required')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load(); prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_reflection_ignored','result':deepcopy(prior['result']),'idempotent':True}
            if s['controls'].get('paused'): result={'status':'reflection_paused','silence':True,'action_authorized':False}
            else:
                schedule=None
                if schedule_id: schedule=next((r for r in self.scheduler.snapshot().get('schedules') or [] if r.get('schedule_id')==schedule_id),None)
                else:
                    due=self.scheduler.due(limit=1); schedule=due[0] if due else None
                if not schedule: result={'status':'deliberate_silence','silence':True,'reason':'no_due_reconsideration','action_authorized':False}
                else:
                    subject_id=str(schedule.get('subject_id') or ''); subject_type=str(schedule.get('subject_type') or '')
                    if select_silence or not conclusion:
                        result={'status':'deliberate_silence','silence':True,'schedule_id':schedule.get('schedule_id'),'reason':'bounded_reflection_selected_silence','action_authorized':False}
                    else:
                        uncertainty=None
                        if subject_type=='belief':
                            belief=next((r for r in self.beliefs.snapshot().get('beliefs') or [] if r.get('belief_id')==subject_id),None); uncertainty=(belief or {}).get('uncertainty')
                        row={'reflection_id':'reconsideration-reflection-'+_digest(event_id,schedule.get('schedule_id'))[:24],'schedule_id':schedule.get('schedule_id'),'subject_type':subject_type,'subject_id':subject_id,'authored_conclusion':conclusion,'uncertainty':uncertainty,'supporting_reference_digests':[_digest(schedule.get('schedule_id'),subject_id)],'occurred_at':_now(),'raw_chain_of_thought_stored':False,'provider_contacted':False,'action_authorized':False}
                        s['reflections']=(s['reflections']+[row])[-int(s['controls'].get('max_total') or 256):]
                        result={'status':'reconsideration_reflected','silence':False,**row}
            stamp=_now(); s['revision']+=1; s['updated_at']=stamp; s['processed_events']=(s['processed_events']+[{'event_id':event_id,'result':deepcopy(result),'occurred_at':stamp}])[-512:]; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def inspection_summary(self):
        s=self._load(); return {'ok':True,'contract_version':CONTRACT_VERSION,'reflection_count':len(s['reflections']),'recent_reflections':deepcopy(s['reflections'][-8:]),'controls':deepcopy(s['controls']),'provider_contacted':False,'raw_chain_of_thought_stored':False,'authority_boundary':deepcopy(s['authority_boundary'])}
def build_bounded_reconsideration_reflection_inspection(runtime_root=None): return BoundedReconsiderationReflection(runtime_root).inspection_summary()
