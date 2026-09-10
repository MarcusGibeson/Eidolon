from __future__ import annotations

"""Accountable reuse of operator-supplied evidence across related inquiries."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os, uuid
from pathlib import Path
from typing import Any, Callable

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
    from inquiry_evidence_assimilation import InquiryEvidenceLedger

CONTRACT_VERSION='v1106.1'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,limit=700): return ' '.join(str(v or '').split())[:limit]
def _digest(*parts): return hashlib.sha256('\x1f'.join(_clean(p,2000) for p in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'links':[],'processed_events':[],'revision':0,'updated_at':'','resource_limits':{'max_targets_per_evidence':8},'authority_boundary':{'can_browse':False,'can_authorize_action':False,'can_execute_action':False,'operator_authority_unchanged':True}}

class CrossInquiryEvidenceLineage:
    def __init__(self,runtime_root=None,*,workspace=None,ledger=None,clock:Callable[[],str]|None=None):
        self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'cross_inquiry_evidence_lineage.json'; self.workspace=workspace or InquiryWorkspace(self.runtime_root); self.ledger=ledger or InquiryEvidenceLedger(self.runtime_root,workspace=self.workspace); self.clock=clock or _now
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
            now=self.clock(); result=fn(s,now);s['revision']+=1;s['updated_at']=now;s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result)}])[-512:];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
    def link(self,event_id,*,evidence_id:str,target_inquiry_id:str,stance:str='supports',relevance:float=.5):
        evidence_id=_clean(evidence_id,120);target_inquiry_id=_clean(target_inquiry_id,120);stance=_clean(stance,40).lower()
        if stance not in {'supports','contradicts','context'}: raise ValueError('unsupported stance')
        evidence=next((r for r in self.ledger.snapshot()['evidence'] if r.get('evidence_id')==evidence_id),None)
        if not evidence: raise KeyError('evidence not found')
        if not evidence.get('active'): raise ValueError('retracted evidence cannot be newly linked')
        if not any(r.get('inquiry_id')==target_inquiry_id for r in self.workspace.snapshot()['inquiries']): raise KeyError('target inquiry not found')
        semantic=_digest(evidence_id,target_inquiry_id,stance)
        def apply(s,now):
            duplicate=next((r for r in s['links'] if r.get('semantic_key')==semantic and r.get('active')),None)
            if duplicate:return {'status':'duplicate_evidence_link_ignored','link_id':duplicate['link_id'],'created':False}
            if sum(1 for r in s['links'] if r.get('evidence_id')==evidence_id and r.get('active'))>=int(s['resource_limits']['max_targets_per_evidence']): raise ValueError('evidence target budget reached')
            row={'link_id':f'evidence-link-{uuid.uuid4().hex}','semantic_key':semantic,'evidence_id':evidence_id,'source_inquiry_id':evidence.get('inquiry_id'),'target_inquiry_id':target_inquiry_id,'stance':stance,'relevance':round(max(0,min(1,float(relevance))),4),'active':True,'created_at':now,'source_identity':{'source_label':evidence.get('source_label'),'evidence_kind':evidence.get('evidence_kind'),'operator_supplied':True},'provenance_digest':_digest(evidence_id,evidence.get('summary'),evidence.get('source_label'))};s['links'].append(row);return {'status':'cross_inquiry_evidence_linked','link_id':row['link_id'],'created':True}
        return self._mutate(event_id,apply)
    def retract(self,event_id,*,link_id:str,reason_code:str):
        def apply(s,now):
            row=next((r for r in s['links'] if r.get('link_id')==_clean(link_id,120)),None)
            if not row: raise KeyError('evidence link not found')
            row['active']=False;row['retracted_at']=now;row['retraction_reason']=_clean(reason_code,180);return {'status':'cross_inquiry_evidence_link_retracted','link_id':row['link_id']}
        return self._mutate(event_id,apply)
    def inspection_summary(self):
        s=self._load(); evidence={r.get('evidence_id'):r for r in self.ledger.snapshot()['evidence']}; active=[]
        for row in s['links']:
            copy=deepcopy(row); source=evidence.get(row.get('evidence_id')) or {}; copy['source_evidence_active']=source.get('active') is True; copy['effective']=row.get('active') is True and copy['source_evidence_active']; active.append(copy)
        return {'ok':True,'contract_version':CONTRACT_VERSION,'active_link_count':sum(r['effective'] for r in active),'historical_link_count':sum(not r['effective'] for r in active),'recent_links':active[-12:],'resource_limits':deepcopy(s['resource_limits']),'authority_boundary':deepcopy(s['authority_boundary']),'provider_contacted':False,'external_browsing_performed':False,'action_authority_changed':False,'hidden_reasoning_exposed':False}

def build_cross_inquiry_evidence_lineage_inspection(runtime_root=None): return CrossInquiryEvidenceLineage(runtime_root).inspection_summary()
