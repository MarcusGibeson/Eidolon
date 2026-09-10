from __future__ import annotations

"""Operator-supplied evidence assimilation with a hard external-research proposal boundary."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os, uuid
from pathlib import Path
from typing import Any, Callable, Iterable
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace

CONTRACT_VERSION='v1105.4'; SCHEMA_VERSION='1'

def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,limit=700): return ' '.join(str(v or '').split())[:limit]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,2000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'evidence':[],'research_proposals':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'operator_supplied_evidence_only':True,'can_browse_externally':False,'can_submit_research':False,'can_authorize_action':False,'can_execute_action':False}}

class InquiryEvidenceLedger:
    def __init__(self,runtime_root=None,*,workspace=None,clock:Callable[[],str]|None=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'inquiry_evidence_ledger.json'; self.workspace=workspace or InquiryWorkspace(self.runtime_root); self.clock=clock or _now
    def _load(self):
        s=load_json_file(self.path,_default(),expected_type=dict)
        for k,v in _default().items(): s.setdefault(k,deepcopy(v))
        return s
    def snapshot(self): return deepcopy(self._load())
    def _mutate(self,event_id,fn):
        event_id=_clean(event_id,160)
        if not event_id: raise ValueError('event_id is required')
        with metadata_mutation_lock(self.path,timeout_seconds=5.0):
            s=self._load(); prior=next((r for r in s['processed_events'] if r.get('event_id')==event_id),None)
            if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
            now=self.clock(); result=fn(s,now); s['revision']+=1;s['updated_at']=now;s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result)}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def assimilate(self,event_id,*,inquiry_id:str,summary:str,source_label:str,evidence_kind:str='operator_note',reliability:float=.5,supports:str=''):
        inquiry_id=_clean(inquiry_id,120);summary=_clean(summary);source_label=_clean(source_label,180)
        if not inquiry_id or not summary or not source_label: raise ValueError('inquiry_id, summary, and source_label are required')
        if not any(r.get('inquiry_id')==inquiry_id for r in self.workspace.snapshot()['inquiries']): raise KeyError('inquiry not found')
        reliability=max(0,min(1,float(reliability)))
        def apply(s,now):
            eid=f'evidence-{uuid.uuid4().hex}'; row={'evidence_id':eid,'inquiry_id':inquiry_id,'summary':summary,'source_label':source_label,'evidence_kind':_clean(evidence_kind,60),'reliability':round(reliability,4),'supports':_clean(supports,180),'received_at':now,'operator_supplied':True,'externally_retrieved_by_eidolon':False,'provider_contacted':False,'raw_private_payload_stored':False,'active':True}
            s['evidence'].append(row); return {'status':'evidence_assimilated','evidence_id':eid,'inquiry_id':inquiry_id}
        return self._mutate(event_id,apply)
    def propose_research(self,event_id,*,inquiry_id:str,question:str,justification:str,requested_sources:Iterable[str]=()):
        inquiry_id=_clean(inquiry_id,120);question=_clean(question);justification=_clean(justification)
        if not inquiry_id or not question or not justification: raise ValueError('inquiry_id, question, and justification are required')
        if not any(r.get('inquiry_id')==inquiry_id for r in self.workspace.snapshot()['inquiries']): raise KeyError('inquiry not found')
        sources=sorted({_clean(x,180) for x in requested_sources if _clean(x,180)})[:12]
        def apply(s,now):
            pid=f'research-proposal-{uuid.uuid4().hex}';row={'proposal_id':pid,'inquiry_id':inquiry_id,'question':question,'justification':justification,'requested_sources':sources,'status':'proposed','created_at':now,'operator_approval_required':True,'authorized':False,'executed':False,'external_request_made':False};s['research_proposals'].append(row);return {'status':'research_proposal_created','proposal_id':pid,'authorized':False,'executed':False}
        return self._mutate(event_id,apply)
    def retract_evidence(self,event_id,*,evidence_id:str,reason_code:str):
        def apply(s,now):
            row=next((r for r in s['evidence'] if r.get('evidence_id')==evidence_id),None)
            if not row: raise KeyError('evidence not found')
            row['active']=False;row['retracted_at']=now;row['retraction_reason']=_clean(reason_code,180);return {'status':'evidence_retracted','evidence_id':evidence_id}
        return self._mutate(event_id,apply)
    def inspection_summary(self):
        s=self._load(); active=[r for r in s['evidence'] if r.get('active')]
        return {'ok':True,'contract_version':CONTRACT_VERSION,'active_evidence_count':len(active),'historical_evidence_count':len(s['evidence'])-len(active),'research_proposal_count':len(s['research_proposals']),'recent_evidence':deepcopy(s['evidence'][-8:]),'recent_research_proposals':deepcopy(s['research_proposals'][-8:]),'external_browsing_performed':False,'provider_contacted':False,'action_authority_changed':False,'authority_boundary':deepcopy(s['authority_boundary'])}

def build_inquiry_evidence_inspection(runtime_root=None): return InquiryEvidenceLedger(runtime_root).inspection_summary()
