from __future__ import annotations
"""Bridge meaningful reconsideration outcomes into existing proactive communication policy."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os, time
from pathlib import Path
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
    from persistent_motivation import MotivationStore
    from proactive_communication import ProactiveCommunicationStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
    from persistent_motivation import MotivationStore
    from proactive_communication import ProactiveCommunicationStore
CONTRACT_VERSION='v1106.5';SCHEMA_VERSION='1'
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,l=500):return ' '.join(str(v or '').split())[:l]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'decisions':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'can_bypass_quiet':False,'can_modify_files':False}}
class ReconsiderationConversationBridge:
    def __init__(self,runtime_root=None,*,scheduler=None,motivations=None,communication=None,epoch_clock=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'reconsideration_conversation_continuity.json';self.scheduler=scheduler or KnowledgeReconsiderationScheduler(self.runtime_root);self.motivations=motivations or MotivationStore(self.runtime_root);self.communication=communication or ProactiveCommunicationStore(self.runtime_root);self.epoch_clock=epoch_clock or time.time
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items():s.setdefault(k,deepcopy(v))
        return s
    def consider(self,event_id,*,schedule_id:str,conclusion:str,changed_belief:bool=False,tone:str='thoughtful',continuation_of:str=''):
        event_id=_clean(event_id,160);schedule_id=_clean(schedule_id,120);conclusion=_clean(conclusion,420)
        if not event_id or not schedule_id or not conclusion:raise ValueError('event_id, schedule_id, and conclusion are required')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load();prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_reconsideration_communication_ignored','result':deepcopy(prior['result']),'idempotent':True}
            schedule=next((r for r in self.scheduler.snapshot().get('schedules') or [] if r.get('schedule_id')==schedule_id),None)
            if not schedule:raise KeyError('schedule not found')
            subject=f"Reconsider {schedule.get('subject_type')} {schedule.get('subject_id')}"
            motivation=self.motivations.record_motivation(f'{event_id}:motivation',kind='unresolved_subject',summary=subject,cognitive_state='thought',urgency=max(.6,float(schedule.get('pressure') or 0)),confidence=.7,origin_type='knowledge_reconsideration',origin_ref=schedule_id)
            mid=motivation['result']['motivation_id']
            receipt={'cycle_id':'reconsideration-cycle-'+_digest(event_id,schedule_id)[:24],'trigger_type':'changed_belief' if changed_belief else 'unresolved_conversation','selected_motivation_id':mid,'reflection_conclusion':conclusion,'salience':max(.6,float(schedule.get('pressure') or 0)),'communication_decision':'consider_communication','communication_reason':'A scheduled reconsideration produced a meaningful change or renewed uncertainty.','occurred_at':_now()}
            outcome=self.communication.consider_cycle(receipt,tone=tone,continuation_of=continuation_of,now_epoch=float(self.epoch_clock()))
            result={'status':'reconsideration_communication_considered','schedule_id':schedule_id,'decision':outcome.get('decision','silence'),'reason':outcome.get('reason') or (outcome.get('message') or {}).get('reason',''),'message_id':(outcome.get('message') or {}).get('message_id',''),'action_authorized':False,'action_executed':False}
            now=_now();s['decisions']=(s['decisions']+[dict(result,occurred_at=now)])[-256:];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'result':deepcopy(result),'occurred_at':now}])[-512:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def inspection_summary(self):
        s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'decision_count':len(s['decisions']),'recent_decisions':deepcopy(s['decisions'][-8:]),'communication':self.communication.inspection_summary(),'provider_contacted':False,'external_browsing_performed':False,'authority_boundary':deepcopy(s['authority_boundary'])}
def build_reconsideration_conversation_inspection(runtime_root=None):return ReconsiderationConversationBridge(runtime_root).inspection_summary()
