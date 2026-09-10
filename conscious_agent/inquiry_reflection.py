from __future__ import annotations
"""One-step resource-bounded inquiry reflection storing conclusions, never hidden reasoning."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
    from inquiry_evidence_quality import InquiryEvidenceQuality
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
    from inquiry_evidence_quality import InquiryEvidenceQuality
CONTRACT_VERSION='v1105.7'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,limit=700): return ' '.join(str(v or '').split())[:limit]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,2000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'reflections':[],'processed_events':[],'revision':0,'updated_at':'','resource_limits':{'max_reflections_per_inquiry':16,'provider_requests_per_reflection':0},'authority_boundary':{'can_authorize_action':False,'can_execute_action':False,'can_browse_externally':False}}
class InquiryReflection:
    def __init__(self,runtime_root=None,*,workspace=None,quality=None,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'inquiry_reflections.json';self.workspace=workspace or InquiryWorkspace(self.runtime_root);self.quality=quality or InquiryEvidenceQuality(self.runtime_root,workspace=self.workspace);self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items():s.setdefault(k,deepcopy(v))
        return s
    def reflect(self,event_id,*,inquiry_id:str):
        event_id=_clean(event_id,160); inquiry_id=_clean(inquiry_id,120)
        if not event_id or not inquiry_id: raise ValueError('event_id and inquiry_id are required')
        inquiry=next((r for r in self.workspace.snapshot()['inquiries'] if r.get('inquiry_id')==inquiry_id),None)
        if not inquiry: raise KeyError('inquiry not found')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load();prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
            existing=[r for r in s['reflections'] if r.get('inquiry_id')==inquiry_id]
            if len(existing)>=int(s['resource_limits']['max_reflections_per_inquiry']): result={'status':'reflection_budget_reached','inquiry_id':inquiry_id,'communication_decision':'silence'}
            else:
                assessment=next((r for r in reversed(self.quality.snapshot()['assessments']) if r.get('inquiry_id')==inquiry_id),None)
                progress=list(inquiry.get('progress') or [])
                if not progress and not assessment: result={'status':'deliberate_silence','inquiry_id':inquiry_id,'communication_decision':'silence','reason':'No meaningful progress or evidence assessment exists.'}
                else:
                    uncertainty=float((assessment or {}).get('updated_uncertainty',inquiry.get('uncertainty') or .5)); conflict=bool((assessment or {}).get('contradiction_present'))
                    if conflict: conclusion='The inquiry remains contested because active evidence points in more than one direction.'
                    elif uncertainty<=.25: conclusion='The inquiry has a comparatively well-supported provisional conclusion, while remaining open to correction.'
                    else: conclusion='The inquiry made bounded progress, but important uncertainty remains unresolved.'
                    now=self.clock(); rid='reflection-'+_digest(event_id)[:20];row={'reflection_id':rid,'inquiry_id':inquiry_id,'authored_conclusion':conclusion,'uncertainty':round(uncertainty,4),'supporting_reference_digests':[_digest((progress[-1] if progress else {}).get('step_id',''),(assessment or {}).get('assessment_id',''))],'occurred_at':now,'provider_contacted':False,'hidden_reasoning_stored':False,'external_browsing_performed':False,'action_authorized':False};s['reflections'].append(row);result={'status':'inquiry_reflection_recorded','inquiry_id':inquiry_id,'reflection_id':rid,'authored_conclusion':conclusion,'uncertainty':round(uncertainty,4),'communication_decision':'consider' if uncertainty<=.65 else 'silence'}
            now=self.clock();s['revision']+=1;s['updated_at']=now;s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'result':deepcopy(result),'occurred_at':now}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def inspection_summary(self):
        s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'reflection_count':len(s['reflections']),'recent_reflections':deepcopy(s['reflections'][-8:]),'resource_limits':deepcopy(s['resource_limits']),'provider_contacted':False,'hidden_reasoning_exposed':False,'action_authority_changed':False}
def build_inquiry_reflection_inspection(runtime_root=None):return InquiryReflection(runtime_root).inspection_summary()
