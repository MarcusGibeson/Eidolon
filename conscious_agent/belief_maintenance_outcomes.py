from __future__ import annotations
"""Accountable retain, revise, suspend, reopen, or unresolved outcomes."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from belief_revision import BeliefRevisionStore
    from knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
    from bounded_reconsideration_reflection import BoundedReconsiderationReflection
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from belief_revision import BeliefRevisionStore
    from knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
    from bounded_reconsideration_reflection import BoundedReconsiderationReflection
CONTRACT_VERSION='v1106.7'; SCHEMA_VERSION='1'; OUTCOMES={'retain','revise','suspend','reopen','unresolved'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,l=500): return ' '.join(str(v or '').split())[:l]
def _digest(*p): return hashlib.sha256('\x1f'.join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'can_modify_files':False}}
class BeliefMaintenanceOutcomes:
    def __init__(self,runtime_root=None,*,beliefs=None,scheduler=None,reflections=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'belief_maintenance_outcomes.json'; self.beliefs=beliefs or BeliefRevisionStore(self.runtime_root); self.scheduler=scheduler or KnowledgeReconsiderationScheduler(self.runtime_root); self.reflections=reflections or BoundedReconsiderationReflection(self.runtime_root)
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items(): s.setdefault(k,deepcopy(v))
        return s
    def apply(self,event_id,*,schedule_id:str,outcome:str,conclusion:str,new_confidence:float|None=None):
        event_id=_clean(event_id,160); schedule_id=_clean(schedule_id,120); outcome=_clean(outcome,40).lower(); conclusion=_clean(conclusion,420)
        if not all((event_id,schedule_id,conclusion)) or outcome not in OUTCOMES: raise ValueError('event_id, schedule_id, conclusion, and supported outcome are required')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load(); prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_outcome_ignored','result':deepcopy(prior['result']),'idempotent':True}
            schedule=next((r for r in self.scheduler.snapshot().get('schedules') or [] if r.get('schedule_id')==schedule_id),None)
            if not schedule: raise KeyError('schedule not found')
            reflection=next((r for r in reversed(self.reflections._load().get('reflections') or []) if r.get('schedule_id')==schedule_id),None)
            if not reflection: raise ValueError('a bounded reflection is required before an outcome')
            subject_type=schedule.get('subject_type'); subject_id=schedule.get('subject_id'); before={}; after={}
            if subject_type=='belief':
                with metadata_mutation_lock(self.beliefs.path,timeout_seconds=5.0):
                    bs=self.beliefs._load(); belief=next((r for r in bs['beliefs'] if r.get('belief_id')==subject_id),None)
                    if not belief: raise KeyError('belief not found')
                    before={'confidence':belief.get('confidence'),'uncertainty':belief.get('uncertainty'),'lifecycle_state':belief.get('lifecycle_state')}
                    if outcome=='revise' and new_confidence is not None:
                        belief['prior_confidence']=max(0,min(1,float(new_confidence))); self.beliefs._recompute(belief)
                    elif outcome=='suspend': belief['lifecycle_state']='contested'
                    elif outcome=='reopen': belief['lifecycle_state']='contested'; belief['uncertainty']=max(float(belief.get('uncertainty') or 0),.65)
                    elif outcome=='retain': pass
                    elif outcome=='unresolved': belief['uncertainty']=max(float(belief.get('uncertainty') or 0),.55)
                    belief['updated_at']=_now(); belief['update_history']=(belief.get('update_history') or [])+[{'event':'maintenance_outcome','outcome':outcome,'occurred_at':belief['updated_at'],'authored_conclusion':conclusion,'supporting_ref_digest':_digest(reflection.get('reflection_id'))}]
                    bs['revision']=int(bs.get('revision') or 0)+1;bs['updated_at']=belief['updated_at'];write_json_atomic(self.beliefs.path,bs,expected_type=dict,sort_keys=True)
                    after={'confidence':belief.get('confidence'),'uncertainty':belief.get('uncertainty'),'lifecycle_state':belief.get('lifecycle_state')}
            row={'outcome_id':'maintenance-outcome-'+_digest(event_id,schedule_id)[:24],'schedule_id':schedule_id,'subject_type':subject_type,'subject_id':subject_id,'outcome':outcome,'authored_conclusion':conclusion,'before':before,'after':after,'reflection_id':reflection.get('reflection_id'),'occurred_at':_now(),'action_authorized':False,'action_executed':False}
            s['outcomes']=(s['outcomes']+[row])[-256:]; stamp=_now();s['revision']+=1;s['updated_at']=stamp;s['processed_events']=(s['processed_events']+[{'event_id':event_id,'result':deepcopy(row),'occurred_at':stamp}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':'belief_maintenance_outcome_recorded','result':row,'idempotent':False}
    def inspection_summary(self):
        s=self._load(); return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'recent_outcomes':deepcopy(s['outcomes'][-8:]),'authority_boundary':deepcopy(s['authority_boundary']),'provider_contacted':False,'external_browsing_performed':False}
def build_belief_maintenance_outcomes_inspection(runtime_root=None): return BeliefMaintenanceOutcomes(runtime_root).inspection_summary()
