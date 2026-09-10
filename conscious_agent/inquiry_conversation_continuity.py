from __future__ import annotations

"""Bridge durable inquiry progress into existing proactive communication safeguards."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os, time
from pathlib import Path
from typing import Any, Callable
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
    from proactive_communication import ProactiveCommunicationStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
    from proactive_communication import ProactiveCommunicationStore

CONTRACT_VERSION='v1105.5'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,limit=700): return ' '.join(str(v or '').split())[:limit]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,2000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'decisions':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'can_modify_files':False,'can_bypass_communication_preferences':False}}

class InquiryConversationBridge:
    def __init__(self,runtime_root=None,*,workspace=None,communication=None,clock:Callable[[],str]|None=None,epoch_clock:Callable[[],float]|None=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'inquiry_conversation_continuity.json';self.workspace=workspace or InquiryWorkspace(self.runtime_root);self.communication=communication or ProactiveCommunicationStore(self.runtime_root);self.clock=clock or _now;self.epoch_clock=epoch_clock or time.time
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items():s.setdefault(k,deepcopy(v))
        return s
    def consider(self,event_id,*,inquiry_id:str,tone:str='thoughtful',continuation_of:str=''):
        event_id=_clean(event_id,160);inquiry_id=_clean(inquiry_id,120)
        if not event_id or not inquiry_id: raise ValueError('event_id and inquiry_id are required')
        inquiry=next((r for r in self.workspace.snapshot()['inquiries'] if r.get('inquiry_id')==inquiry_id),None)
        if not inquiry: raise KeyError('inquiry not found')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load();prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_bridge_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
            progress=list(inquiry.get('progress') or []);latest=progress[-1] if progress else {}
            conclusion=_clean(latest.get('conclusion') or f"The inquiry remains open with uncertainty {float(inquiry.get('uncertainty') or 0):.2f}.",420)
            salience=max(float(inquiry.get('priority') or 0),float(inquiry.get('uncertainty') or 0))
            receipt={'cycle_id':f"inquiry-cycle-{_digest(event_id,inquiry_id)[:24]}",'trigger_type':'unresolved_conversation','selected_motivation_id':inquiry.get('motivation_id',''),'reflection_conclusion':conclusion,'salience':round(salience,4),'communication_decision':'consider_communication','communication_reason':'A durable inquiry produced relevant progress that may be worth sharing.','occurred_at':self.clock()}
            outcome=self.communication.consider_cycle(receipt,tone=tone,continuation_of=continuation_of,now_epoch=float(self.epoch_clock()))
            result={'status':'inquiry_communication_considered','inquiry_id':inquiry_id,'decision':outcome.get('decision','silence'),'reason':outcome.get('reason') or (outcome.get('message') or {}).get('reason',''),'message_id':(outcome.get('message') or {}).get('message_id',''),'communication_status':outcome.get('status'),'action_authorized':False,'action_executed':False}
            now=self.clock();s['revision']+=1;s['updated_at']=now;s['decisions']=(s['decisions']+[dict(result,occurred_at=now)])[-256:];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'result':deepcopy(result),'occurred_at':now}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def inspection_summary(self):
        s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'decision_count':len(s['decisions']),'recent_decisions':deepcopy(s['decisions'][-8:]),'communication':self.communication.inspection_summary(),'action_authority_changed':False,'authority_boundary':deepcopy(s['authority_boundary'])}

def build_inquiry_conversation_inspection(runtime_root=None):return InquiryConversationBridge(runtime_root).inspection_summary()
