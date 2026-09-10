from __future__ import annotations
"""Accountable inquiry resolution into beliefs, residual questions, and historical provenance."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
    from inquiry_reflection import InquiryReflection
    from belief_revision import BeliefRevisionStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
    from inquiry_reflection import InquiryReflection
    from belief_revision import BeliefRevisionStore
CONTRACT_VERSION='v1105.8';SCHEMA_VERSION='1'
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,limit=700):return ' '.join(str(v or '').split())[:limit]
def _digest(*parts):return hashlib.sha256('\x1f'.join(_clean(p,2000) for p in parts).encode()).hexdigest()
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'resolutions':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'operator_authority_unchanged':True}}
class InquiryResolution:
    def __init__(self,runtime_root=None,*,workspace=None,reflection=None,beliefs=None,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'inquiry_resolutions.json';self.workspace=workspace or InquiryWorkspace(self.runtime_root);self.reflection=reflection or InquiryReflection(self.runtime_root,workspace=self.workspace);self.beliefs=beliefs or BeliefRevisionStore(self.runtime_root);self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items():s.setdefault(k,deepcopy(v))
        return s
    def resolve(self,event_id,*,inquiry_id:str,proposition:str,residual_question:str=''):
        event_id=_clean(event_id,160);inquiry_id=_clean(inquiry_id,120);proposition=_clean(proposition,600);residual_question=_clean(residual_question,500)
        if not event_id or not inquiry_id or not proposition:raise ValueError('event_id, inquiry_id, and proposition are required')
        inquiry=next((r for r in self.workspace.snapshot()['inquiries'] if r.get('inquiry_id')==inquiry_id),None)
        if not inquiry:raise KeyError('inquiry not found')
        reflection=next((r for r in reversed(self.reflection._load()['reflections']) if r.get('inquiry_id')==inquiry_id),None)
        if not reflection:raise ValueError('inquiry requires a recorded reflection before resolution')
        uncertainty=float(reflection.get('uncertainty') or 1)
        if uncertainty>.4:raise ValueError('inquiry uncertainty is too high for consolidation')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load();prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
            belief=self.beliefs.record_belief(event_id+'-belief',proposition=proposition,confidence=max(.5,1-uncertainty),origin_type='inquiry_resolution',origin_ref=inquiry_id,scope_project_id=inquiry.get('project_id',''))
            belief_id=(belief.get('result') or {}).get('belief_id','');self.workspace.set_status(event_id+'-complete',inquiry_id=inquiry_id,status='completed',reason_code='supported_resolution')
            now=self.clock();row={'resolution_id':'resolution-'+_digest(event_id)[:20],'inquiry_id':inquiry_id,'belief_id':belief_id,'proposition':proposition,'residual_question':residual_question,'uncertainty_retained':round(uncertainty,4),'supporting_reference_digests':[_digest(reflection.get('reflection_id',''),inquiry_id)],'occurred_at':now,'provider_contacted':False,'hidden_reasoning_stored':False,'action_authorized':False,'action_executed':False};s['resolutions'].append(row);result={'status':'inquiry_resolved','inquiry_id':inquiry_id,'belief_id':belief_id,'residual_question_preserved':bool(residual_question),'uncertainty_retained':round(uncertainty,4),'action_authorized':False}
            s['revision']+=1;s['updated_at']=now;s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'result':deepcopy(result),'occurred_at':now}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def inspection_summary(self):
        s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'resolution_count':len(s['resolutions']),'recent_resolutions':deepcopy(s['resolutions'][-8:]),'provider_contacted':False,'hidden_reasoning_exposed':False,'action_authority_changed':False,'authority_boundary':deepcopy(s['authority_boundary'])}
def build_inquiry_resolution_inspection(runtime_root=None):return InquiryResolution(runtime_root).inspection_summary()
